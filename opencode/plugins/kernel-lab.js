// kernel-lab.js — plugin OpenCode V2 untuk track kernel development (mesin Kali).
//
// Empat tanggung jawab:
//   1. TOOL  : tool kernel sebagai tool native (agent tidak perlu shell mentah).
//   2. GUARD : permission hook -> tolak perintah yang bisa merusak boot/dual-boot.
//   3. CONTEXT: sisipkan fakta state kernel ke system prompt tiap request.
//   4. PROMPT : ingatkan pre-flight safety kalau prompt menyentuh install/boot.
//
// Semua operasi I/O lewat execFile (tanpa shell interpolation), semua error
// ditangkap — plugin ini tidak boleh menjatuhkan agent loop.

import { execFile } from "node:child_process"
import { promisify } from "node:util"
import fs from "node:fs"
import path from "node:path"
import os from "node:os"

const exec = promisify(execFile)

const DEFAULTS = {
  kitPath: "/root/kernel-lab/kernel-specialist",
  labPath: "/root/kernel-lab",
  tree: "/root/kernel-lab/src/linux-7.1.5",
  build: "/root/kernel-lab/build/linux-7.1.5",
  baseConfig: "/boot/config-" + os.release(),
}

function kitTool(ctx, name) {
  const base = ctx?.options?.kitPath || DEFAULTS.kitPath
  return path.join(base, "tools", "kernel", name, `${name}.py`)
}

function lab(ctx, key) {
  return ctx?.options?.[key] || DEFAULTS[key]
}

async function runTool(ctx, toolName, args = []) {
  const file = kitTool(ctx, toolName)
  if (!fs.existsSync(file)) {
    return { ok: false, error: `tool kit tidak ditemukan: ${file}` }
  }
  try {
    const { stdout, stderr } = await exec("python3", [file, ...args], {
      maxBuffer: 32 * 1024 * 1024,
      timeout: 900_000,
    })
    return { ok: true, stdout, stderr }
  } catch (e) {
    return {
      ok: false,
      error: String(e?.message || e),
      stdout: e?.stdout || "",
      stderr: e?.stderr || "",
    }
  }
}

function jsonOf(res) {
  if (!res?.stdout) return null
  try {
    return JSON.parse(res.stdout)
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// 1. TOOLS
// ---------------------------------------------------------------------------

const TOOLS = [
  {
    name: "status",
    description:
      "State kernel development mesin ini: kernel running, toolchain, Secure Boot, source tree, build artifacts, ruang /boot. Baca-saja.",
    input: { type: "object", properties: {}, additionalProperties: false },
    execute: async () => {
      const res = await runTool({ options: {} }, "env_report", ["--json"])
      const data = jsonOf(res)
      if (!data) return { content: res.stdout || res.error || "gagal membaca report" }
      const s = data.system || {}
      const tc = data.toolchain || {}
      const sb = data.secure_boot || {}
      const tree = data.source_tree || {}
      const bd = data.build_dir || {}
      const art = bd.artifacts || {}
      const lines = [
        `kernel running : ${s.kernel_running} (${s.arch})`,
        `distro         : ${(s.os_release || {}).PRETTY_NAME || "?"}`,
        `cpu / mem      : ${(s.cpu_model || "?").trim()} / ${s.mem_total}`,
        `/boot free     : ${s.boot_free || "n/a"}`,
        `secure boot    : ${sb.output || sb.note || "tidak diketahui"}`,
        `source tree    : ${tree.path} ${tree.exists ? "v" + (tree.version || "?") + "." + (tree.sublevel || "?") + (tree.git_describe ? " (" + tree.git_describe + ")" : "") : "(belum ada)"}`,
        `build artifacts: bzImage=${art.bzImage?.exists ? "ada" : "tidak"} vmlinux=${art.vmlinux?.exists ? "ada" : "tidak"} ko=${art.ko_count ?? 0}`,
        `toolchain      : gcc=${tc.gcc || "-"} clang=${tc.clang || "-"} rustc=${tc.rustc || "-"} pahole=${tc.pahole || "-"} ccache=${tc.ccache || "-"} bison=${tc.bison || "-"}`,
      ]
      return { content: lines.join("\n") }
    },
  },
  {
    name: "preflight",
    description:
      "Safety pre-flight sebelum install/boot custom kernel: Secure Boot, ruang /boot, kernel stock tersedia, initramfs, GRUB, rollback. Mengembalikan daftar blocker.",
    input: { type: "object", properties: {}, additionalProperties: false },
    execute: async () => {
      const blockers = []
      const warns = []
      const ok = []

      // Secure Boot
      try {
        const { stdout } = await exec("mokutil", ["--sb-state"], { timeout: 15_000 }).catch(
          (e) => ({ stdout: "", stderr: String(e?.message || e) }),
        )
        const txt = (stdout || "").trim()
        if (/enabled/i.test(txt)) {
          blockers.push(
            "Secure Boot ENABLED — kernel custom tidak akan boot tanpa MOK yang di-enroll (mokmanager) atau SB dimatikan.",
          )
        } else if (/disabled/i.test(txt)) {
          ok.push("Secure Boot disabled — kernel custom boleh boot tanpa signing (tetap patuhi config MODULE_SIG).")
        } else {
          warns.push("Status Secure Boot tidak terbaca (mokutil belum terpasang?) — pasang mok-util atau cek manual di BIOS.")
        }
      } catch {
        warns.push("Status Secure Boot tidak bisa dibaca — cek manual (mokutil --sb-state).")
      }

      // ruang /boot
      try {
        const { stdout } = await exec("df", ["-h", "/boot"], { timeout: 10_000 })
        const parts = stdout.trim().split("\n")
        const last = parts[parts.length - 1].trim().split(/\s+/)
        const availKB = Number(last[3])
        if (Number.isFinite(availKB) && availKB < 300 * 1024) {
          blockers.push(`/boot tinggal ${last[3]} — tidak cukup untuk kernel baru + initramfs (butuh ~300MB).`)
        } else {
          ok.push(`/boot bebas ${last[3]} — cukup untuk 1 kernel + initramfs.`)
        }
      } catch {
        warns.push("Tidak bisa cek ruang /boot.")
      }

      // kernel stock
      try {
        const vmlinuz = fs.readdirSync("/boot").filter((f) => f.startsWith("vmlinuz-"))
        if (vmlinuz.length === 0) {
          blockers.push("Tidak ada /boot/vmlinuz-* — tidak ada kernel fallback. Jangan install sebelum yakin.")
        } else {
          ok.push(`Kernel tersedia sebagai fallback: ${vmlinuz.join(", ")}`)
        }
      } catch {
        blockers.push("/boot tidak bisa dibaca — periksa partisi /boot (dual-boot berisiko).")
      }

      // grub + windows
      try {
        fs.accessSync("/etc/default/grub")
        const grub = fs.readFileSync("/etc/default/grub", "utf8")
        if (/GRUB_DISABLE_OS_PROBER\s*=\s*true/i.test(grub)) {
          warns.push("GRUB_DISABLE_OS_PROBER=true — entri Windows hilang dari GRUB tiap update-grub.")
        } else {
          ok.push("os-prober aktif — entri Windows di GRUB kemungkinan tetap ada (verifikasi setelah update-grub).")
        }
      } catch {
        warns.push("/etc/default/grub tidak terbaca — cek manual sebelum update-grub.")
      }

      // initramfs
      const cur = os.release()
      const initrd = `/boot/initrd.img-${cur}`
      if (fs.existsSync(initrd)) ok.push(`initramfs kernel running ada: ${initrd}`)
      else warns.push(`initramfs untuk ${cur} tidak ditemukan — cek update-initramfs.`)

      return {
        content: [
          `PRE-FLIGHT (kernel running: ${cur})`,
          "",
          "BLOCKER (hanya install setelah semua beres):",
          ...(blockers.length ? blockers.map((b) => "  [X] " + b) : ["  (tidak ada)"]),
          "",
          "WARN:",
          ...(warns.length ? warns.map((w) => "  [!] " + w) : ["  (tidak ada)"]),
          "",
          "OK:",
          ...(ok.length ? ok.map((o) => "  [OK] " + o) : ["  (tidak ada)"]),
          "",
          "Rollback wajib: booting kernel stock via GRUB > Advanced options, lalu hapus kernel custom.",
        ].join("\n"),
      }
    },
  },
  {
    name: "config_check",
    description:
      "Validasi fragment/.config kernel terhadap source tree: symbol dikenal, baseline boot, kombinasi berisiko (RUST/BTF/MODULE_SIG).",
    input: {
      type: "object",
      properties: {
        fragments: { type: "array", items: { type: "string" }, description: "path fragment .conf" },
        config: { type: "string", description: "path .config utuh (opsional)" },
        strict: { type: "boolean", description: "warning ikut menggagalkan (default true)" },
      },
      additionalProperties: false,
    },
    execute: async (input) => {
      const args = ["--tree", lab({ options: {} }, "tree"), "--json"]
      if (input?.config) args.push("--config", input.config)
      for (const f of input?.fragments || []) args.push("--fragment", f)
      if (input?.strict !== false) args.push("--strict")
      const res = await runTool({ options: {} }, "config_check", args)
      const data = jsonOf(res)
      if (!data) return { content: res.stdout || res.error || "gagal" }
      const out = [
        `RESULT: ${data.ok ? "PASS" : "FAIL"}`,
        ...(data.errors || []).map((e) => "  [X] " + e),
        ...(data.warnings || []).map((w) => "  [!] " + w),
      ]
      return { content: out.join("\n") }
    },
  },
  {
    name: "build",
    description:
      "Build kernel out-of-tree (bzImage/modules) via tool kit. Tidak pernah menyentuh /boot atau /lib/modules._default",
    input: {
      type: "object",
      properties: {
        target: { type: "string", description: "bzImage | modules | all (default bzImage)" },
        jobs: { type: "number", description: "jumlah paralel (default: jumlah CPU)" },
        fragments: { type: "array", items: { type: "string" } },
        baseConfig: { type: "string", description: "default /boot/config-$(uname -r)" },
        ccache: { type: "boolean", description: "aktifkan ccache (default true)" },
        dryRun: { type: "boolean", description: "tampilkan perintah saja" },
      },
      additionalProperties: false,
    },
    execute: async (input) => {
      const args = [
        "--tree",
        lab({ options: {} }, "tree"),
        "--out",
        lab({ options: {} }, "build"),
        "--base-config",
        input?.baseConfig || lab({ options: {} }, "baseConfig"),
        "--target",
        input?.target || "bzImage",
        "--jobs",
        String(input?.jobs || os.cpus().length),
      ]
      if (input?.ccache !== false) args.push("--ccache")
      for (const f of input?.fragments || []) args.push("--fragment", f)
      if (input?.dryRun) args.push("--dry-run")
      const res = await runTool({ options: {} }, "kbuild", args)
      const tail = (res.stdout || "").split("\n").slice(-40).join("\n")
      return {
        content: res.ok ? tail : `${tail}\n\nGAGAL: ${res.error || "rc != 0"}`,
      }
    },
  },
  {
    name: "module_inspect",
    description: "Inspeksi modul .ko: vermagic vs kernel running, signature, symbol undefined, dependensi.",
    input: {
      type: "object",
      properties: {
        module: { type: "string", description: "path file .ko" },
        dir: { type: "string", description: "direktori .ko" },
      },
      additionalProperties: false,
    },
    execute: async (input) => {
      const args = ["--json"]
      if (input?.module) args.push("--module", input.module)
      if (input?.dir) args.push("--dir", input.dir)
      if (!input?.module && !input?.dir) return { content: "wajib --module atau --dir" }
      const res = await runTool({ options: {} }, "module_inspect", args)
      const data = jsonOf(res)
      if (!data) return { content: res.stdout || res.error || "gagal" }
      return {
        content: data
          .map(
            (m) =>
              `${m.path}\n  vermagic : ${m.modinfo?.vermagic || "-"}\n  signer   : ${m.modinfo?.signer || "(unsigned)"}\n  errors   : ${(m.errors || []).join("; ") || "tidak ada"}\n  warnings : ${(m.warnings || []).join("; ") || "tidak ada"}`,
          )
          .join("\n\n"),
      }
    },
  },
  {
    name: "crashlog",
    description:
      "Kumpulkan bukti crash kernel nyata dari dmesg/journal (oops, BUG, panic, Call Trace) untuk dianalisis.",
    input: {
      type: "object",
      properties: {
        lines: { type: "number", description: "jumlah baris terakhir (default 200)" },
        previous: { type: "boolean", description: "ambil juga boot sebelumnya (default true)" },
      },
      additionalProperties: false,
    },
    execute: async (input) => {
      const n = Math.min(Number(input?.lines || 200), 2000)
      const chunks = []
      try {
        const { stdout } = await exec("dmesg", ["-T"], { timeout: 20_000 })
        chunks.push("== dmesg -T (tail " + n + ") ==\n" + stdout.split("\n").slice(-n).join("\n"))
      } catch (e) {
        chunks.push("== dmesg GAGAL: " + String(e?.message || e))
      }
      try {
        const { stdout } = await exec(
          "journalctl",
          ["-k", "-b", "--no-pager", "-n", String(n)],
          { timeout: 30_000 },
        )
        chunks.push("== journalctl -k -b (tail " + n + ") ==\n" + stdout)
      } catch (e) {
        chunks.push("== journalctl -k -b GAGAL: " + String(e?.message || e))
      }
      if (input?.previous !== false) {
        try {
          const { stdout } = await exec(
            "journalctl",
            ["-k", "-b", "-1", "--no-pager", "-n", String(n)],
            { timeout: 30_000 },
          )
          chunks.push("== journalctl -k -b -1 (boot sebelumnya) ==\n" + stdout)
        } catch (e) {
          chunks.push("== boot sebelumnya tidak tersedia: " + String(e?.message || e))
        }
      }
      const text = chunks.join("\n\n")
      const hit = /BUG:|Oops|Call Trace|general protection fault|panic|Kernel panic|soft lockup|rcu: INFO|stack segment/i.test(
        text,
      )
      return { content: (hit ? "[ADA INDIKASI CRASH]\n" : "[tidak ada indikasi crash di potongan ini]\n") + text }
    },
  },
]

// ---------------------------------------------------------------------------
// 2. GUARDRAIL (permission evaluate)
// ---------------------------------------------------------------------------

const DENY = [
  { re: /\brm\s+(-[a-zA-Z]*\s+)*-?[a-zA-Z]*r[a-zA-Z]*f?[a-zA-Z]*\s+\/boot\b/i, why: "menghapus /boot" },
  { re: /\brm\s+-rf\s+\/boot\/?\s*$/i, why: "menghapus /boot" },
  { re: /\brm\s+-rf\s+\/lib\/modules\b/i, why: "menghapus /lib/modules" },
  { re: /\bmkfs(\.[a-z0-9]+)?\b/i, why: "memformat filesystem" },
  { re: /\bwipefs\b/i, why: "menghapus signature disk" },
  { re: /\bsgdisk\s+.*--zap-all/i, why: "menghapus seluruh partisi disk" },
  { re: /\bdd\b[^|;]*\bof=\/dev\//i, why: "menulis langsung ke device disk" },
  { re: />\s*\/dev\/(sd|nvme|vd)[a-z]/i, why: "redirect output ke device disk" },
  { re: /\bchmod\s+-R\s+777\s+\/\s*$/i, why: "membuka permissions seluruh root" },
  { re: /\bchown\s+-R\s+\S+\s+\/\s*$/i, why: "mengubah ownership seluruh root" },
]

const ASK = [
  { re: /\bmake\s+(\S+\s+)?install\b/i, why: "install kernel ke /boot (dual-boot)" },
  { re: /\bmake\s+(\S+\s+)?modules_install\b/i, why: "install modul ke /lib/modules" },
  { re: /\bupdate-initramfs\b/i, why: "mengganti initramfs" },
  { re: /\bmkinitramfs\b/i, why: "membuat initramfs" },
  { re: /\bupdate-grub\b/i, why: "menulis konfigurasi bootloader" },
  { re: /\bdepmod\b/i, why: "mengganti database modul" },
  { re: /\binsmod\b/i, why: "memuat modul ke kernel running" },
  { re: /\brmmod\b/i, why: "melepas modul dari kernel running" },
  { re: /\bmodprobe\s+(-r\s+)?\S+/i, why: "memuat/melepas modul" },
  { re: /\bgit\s+push\b/i, why: "push ke remote" },
  { re: /\bapt(-get)?\s+install\b/i, why: "pasang paket" },
  { re: /\bcurl\b[^|;]*\|\s*(ba)?sh\b/i, why: "menjalankan script dari internet" },
]

function guardCheck(command) {
  const cmd = String(command || "")
  for (const d of DENY) {
    if (d.re.test(cmd)) return { effect: "deny", why: d.why }
  }
  for (const a of ASK) {
    if (a.re.test(cmd)) return { effect: "ask", why: a.why }
  }
  return null
}

// diekspor untuk unit test (tests/test_guardrail.mjs)
export const __guard = { check: guardCheck, DENY, ASK }

// ---------------------------------------------------------------------------
// 3. CONTEXT injection
// ---------------------------------------------------------------------------

let cachedContext = { at: 0, text: "" }

async function buildContext(ctx) {
  const now = Date.now()
  if (now - cachedContext.at < 60_000 && cachedContext.text) return cachedContext.text
  const res = await runTool({ options: ctx?.options || {} }, "env_report", ["--json"])
  const data = jsonOf(res)
  if (!data) return ""
  const s = data.system || {}
  const tree = data.source_tree || {}
  const bd = data.build_dir || {}
  const art = bd.artifacts || {}
  const sb = data.secure_boot || {}
  const cfg = data.running_kernel_config || {}
  const settings = cfg.settings || {}
  const text = [
    "<kernel-lab-context>",
    `Mesin: Kali, kernel running ${s.kernel_running} · ${os.cpus().length} core · /boot free ${(s.boot_free || "?").split(" ")[0] || "?"}`,
    `Source tree: ${tree.path} ${tree.exists ? "(v" + (tree.version || "?") + "." + (tree.sublevel || "?") + (tree.git_describe ? ", " + tree.git_describe : "") + ")" : "(belum ada)"}`,
    `Build dir: ${bd.path} · bzImage=${art.bzImage?.exists ? "ada" : "belum"} · ko=${art.ko_count ?? 0}`,
    `Secure Boot: ${(sb.output || sb.note || "tidak diketahui").split("\n")[0]}`,
    `Config running: ${settings.CONFIG_RUST || "CONFIG_RUST=?"} · ${settings.CONFIG_DEBUG_INFO_BTF || "CONFIG_DEBUG_INFO_BTF=?"} · ${settings.CONFIG_MODULE_SIG || "CONFIG_MODULE_SIG=?"}`,
    "Aturan: build out-of-tree, ubah config lewat fragment, JANGAN sentuh /boot tanpa izin + pre-flight, kernel stock harus tetap bootable.",
    "</kernel-lab-context>",
  ].join("\n")
  cachedContext = { at: now, text }
  return text
}

// ---------------------------------------------------------------------------
// 4. PROMPT hook (safety reminder)
// ---------------------------------------------------------------------------

const RISKY_INTENT =
  /\b(install|pasang|boot|reboot|dual.?boot|grub|initramfs|update-grub|modules_install|kernel baru|replace kernel)\b/i

// ---------------------------------------------------------------------------
// PLUGIN
// ---------------------------------------------------------------------------

export default {
  id: "kernel-lab",
  async setup(ctx) {
    const opts = ctx?.options || {}

    // --- tools -------------------------------------------------------------
    await ctx.tool.transform((editor) => {
      editor.namespace({
        name: "kernel",
        description:
          "Tool kernel development: status, pre-flight safety, validasi config, build, inspeksi modul, kumpulkan log crash. Gunakan tool ini untuk kerja kernel — bukan shell mentah.",
      })
      for (const t of TOOLS) {
        editor.add({
          name: t.name,
          description: t.description,
          input: t.input,
          options: { namespace: "kernel", codemode: true },
          execute: async (input, toolCtx) => {
            try {
              const out = await t.execute(input || {})
              const content = typeof out === "string" ? out : out?.content
              if (toolCtx?.progress) {
                try {
                  await toolCtx.progress({ status: t.name })
                } catch {}
              }
              return { content: String(content ?? "") }
            } catch (e) {
              return { content: `ERROR ${t.name}: ${String(e?.message || e)}` }
            }
          },
        })
      }
    })

    // --- guardrail ---------------------------------------------------------
    await ctx.permission.hook("evaluate", async (event) => {
      if (event.action !== "shell") return
      const resources = event.resources || []
      for (const r of resources) {
        const hit = guardCheck(r)
        if (!hit) continue
        if (hit.effect === "deny") {
          event.effect = "deny"
          event.message = `DITOLAK oleh guardrail kernel-lab: ${hit.why}. Perintah: "${String(r).slice(0, 160)}". Dual-boot Windows + kernel stock harus tetap aman — pakai tool kernel (kernel_build dengan staging) alih-alih menulis ke /boot.`
        } else {
          event.effect = "ask"
          event.message = `Guardrail kernel-lab: ${hit.why}. Pastikan pre-flight (tool kernel_preflight) sudah dicek dan user sudah menyetujui.`
        }
        return
      }
    })

    // --- context injection -------------------------------------------------
    await ctx.session.hook("context", async (event) => {
      try {
        const text = await buildContext(ctx)
        if (text) event.system.push({ type: "text", text })
      } catch {}
    })

    // --- prompt safety reminder -------------------------------------------
    await ctx.session.hook("prompt", async (event) => {
      try {
        const t = event?.prompt?.text || ""
        if (!RISKY_INTENT.test(t)) return
        event.prompt.text =
          t +
          "\n\n[guardrail kernel-lab] Task ini menyentuh area sensitif (install/boot/bootloader). " +
          "WAJIB: (1) jalankan tool kernel_preflight lebih dulu, " +
          "(2) pastikan kernel stock masih ada di /boot sebagai fallback, " +
          "(3) build di staging (tanpa --install) dan verifikasi artefak, " +
          "(4) minta izin user sebelum update-initramfs/update-grub/make install."
      } catch {}
    })

    if (opts.verbose) {
      console.log("[kernel-lab] aktif — tools: " + TOOLS.map((t) => "kernel_" + t.name).join(", "))
    }
  },
}
