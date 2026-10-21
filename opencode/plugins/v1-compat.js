// v1-compat.js — lapisan kompatibilitas V1 → V2 untuk plugin OpenCode.
//
// Kenapa perlu: beberapa plugin di pool (opencode-goal-plugin, workaholic,
// notify, autotitle, token-tracker) masih API V1 (export default fungsi yang
// mengembalikan map hook). OpenCode v2 hanya memuat plugin yang default-nya
// objek { id, setup(ctx) } → plugin V1 gagal load ("Missing key at [default]").
//
// Yang dilakukan plugin ini:
//   1. Resolve paket dari cache npm OpenCode (~/.cache/opencode/npm/<pkg>@latest/...).
//   2. Kalau paket punya dukungan V2 native (default = { id, setup }) → panggil setup(ctx).
//   3. Kalau paket V1 (default = fungsi) → panggil factory-nya dengan konteks
//      V1-compatible, lalu PETAKAN hook V1 ke hook V2 (tool/chat/event/shell).
//
// Prinsip: TIDAK PERNAH melempar error ke luar (plugin lain/agent loop tidak boleh
// tumbang karena plugin|中国 kompatibilitas). Semua kegagalan dicatat, plugin
// yang gagal dilewati.

import fs from "node:fs"
import path from "node:path"
import os from "node:os"
import { pathToFileURL } from "node:url"

const NPM_CACHE = process.env.OPENCODE_NPM_CACHE || path.join(os.homedir(), ".cache", "opencode", "npm")

function log(...args) {
  console.log("[v1-compat]", ...args)
}

function readJSON(file) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"))
  } catch {
    return null
  }
}

/** Cari entry file ESM dari sebuah paket di cache npm OpenCode. */
function resolvePackageEntry(pkgName) {
  const base = path.join(NPM_CACHE, pkgName + "@latest")
  if (!fs.existsSync(base)) return null
  const versions = fs
    .readdirSync(base)
    .map((d) => path.join(base, d))
    .filter((d) => fs.existsSync(d))
  for (const v of versions.sort().reverse()) {
    const pkgDir = path.join(v, "node_modules", pkgName)
    const pkgJson = path.join(pkgDir, "package.json")
    if (!fs.existsSync(pkgJson)) continue
    const meta = readJSON(pkgJson)
    if (!meta) continue
    const exp = meta.exports?.["."]
    let rel = null
    if (typeof exp === "string") rel = exp
    else if (exp && typeof exp === "object") rel = exp.import || exp.default || exp.require
    if (!rel) rel = meta.module || meta.main
    if (!rel) continue
    const abs = path.resolve(pkgDir, rel)
    if (fs.existsSync(abs)) return { abs, pkgDir, meta }
  }
  return null
}

/** Cari file "v2-bridge" milik paket (beberapa paket sudah menyediakan adapter). */
function resolveV2Bridge(pkgDir) {
  const candidates = []
  for (const sub of ["src", "dist", "lib", "."]) {
    const dir = path.join(pkgDir, sub)
    if (!fs.existsSync(dir)) continue
    for (const f of fs.readdirSync(dir)) {
      if (/v2[-_.]?bridge/i.test(f) && f.endsWith(".js")) candidates.push(path.join(dir, f))
    }
  }
  return candidates[0] || null
}

// ---------------------------------------------------------------------------
// Facade client V1 -> V2
// ---------------------------------------------------------------------------

function makeV1Client(ctx) {
  const wrap = (ns) =>
    new Proxy(
      {},
      {
        get(_t, method) {
          return async (...args) => {
            const domain = ctx[ns]
            const fn = domain && typeof domain[method] === "function" ? domain[method] : null
            if (!fn) {
              log(`client.${ns}.${String(method)} tidak tersedia di V2 — dilewati`)
              return undefined
            }
            try {
              const out = await fn.apply(domain, args)
              return out
            } catch (e) {
              log(`client.${ns}.${String(method)} gagal: ${String(e?.message || e)}`)
              return undefined
            }
          }
        },
      },
    )
  return new Proxy(
    {},
    {
      get(_t, ns) {
        if (typeof ns !== "string") return undefined
        return wrap(ns)
      },
    },
  )
}

function v1Context(ctx) {
  return {
    directory: ctx.location?.directory,
    project: ctx.location?.project,
    worktree: ctx.location?.project?.canonical || ctx.location?.directory,
    client: makeV1Client(ctx),
    $: undefined,
    agent: ctx.agent,
  }
}

// ---------------------------------------------------------------------------
// Pemetaan hook V1 -> V2
// ---------------------------------------------------------------------------

function systemToV1(system) {
  if (!Array.isArray(system)) return []
  return system.map((s) => (typeof s === "string" ? s : (s?.text ?? "")))
}

function systemToV2(system) {
  if (!Array.isArray(system)) return []
  return system.map((s) => (typeof s === "string" ? { type: "text", text: s } : s))
}

async function adaptHooks(ctx, hooks, name) {
  const supported = []
  const unsupported = []

  const call = async (fn, input, output) => {
    try {
      return await fn(input, output)
    } catch (e) {
      log(`hook ${name} error: ${String(e?.message || e)}`)
      return undefined
    }
  }

  for (const [key, fn] of Object.entries(hooks || {})) {
    if (typeof fn !== "function") continue
    switch (key) {
      case "tool.execute.before":
        await ctx.tool.hook("execute.before", async (event) => {
          await call(fn, { tool: event.tool }, event.input || {})
        })
        supported.push(key)
        break
      case "tool.execute.after":
        await ctx.tool.hook("execute.after", async (event) => {
          await call(
            fn,
            { tool: event.tool },
            {
              title: event.tool,
              output: event.result ?? event.output,
              metadata: event.metadata,
            },
          )
        })
        supported.push(key)
        break
      case "chat.params":
        await ctx.session.hook("context", async (event) => {
          const out = {
            system: systemToV1(event.system),
            tools: event.tools,
            agent: event.agent,
            model: event.model,
            temperature: event.options?.temperature,
            top_p: event.options?.topP,
          }
          await call(fn, {}, out)
          if (Array.isArray(out.system)) event.system = systemToV2(out.system)
          if (out.temperature !== undefined) event.options.temperature = out.temperature
        })
        supported.push(key)
        break
      case "chat.message":
        await ctx.session.hook("prompt", async (event) => {
          const text = event.prompt?.text || ""
          await call(fn, {}, { message: { role: "user", parts: [{ type: "text", text }] } })
        })
        supported.push(key)
        break
      case "event": {
        const controller = new AbortController()
        void (async () => {
          try {
            for await (const ev of ctx.event.subscribe({ signal: controller.signal })) {
              await call(fn, { event: ev }, {})
            }
          } catch (e) {
            log(`event stream error: ${String(e?.message || e)}`)
          }
        })()
        supported.push(key)
        break
      }
      case "shell.env":
        await ctx.shell.hook("create.before", async (event) => {
          const out = { env: event.env }
          await call(fn, {}, out)
          if (out.env && typeof out.env === "object") event.env = { ...event.env, ...out.env }
        })
        supported.push(key)
        break
      case "dispose":
      case "config":
      case "auth":
      case "provider":
      case "tool":
      case "command.execute.before":
      case "permission.ask":
      case "experimental.chat.system.transform":
      case "experimental.chat.messages.transform":
      default:
        unsupported.push(key)
        break
    }
  }
  if (supported.length) log(`${name}: hook dipetakan → ${supported.join(", ")}`)
  if (unsupported.length) log(`${name}: hook TIDAK dipetakan (diabaikan) → ${unsupported.join(", ")}`)
}

// ---------------------------------------------------------------------------
// Plugin
// ---------------------------------------------------------------------------

export default {
  id: "v1-compat",
  async setup(ctx) {
    const names = Array.isArray(ctx?.options?.packages)
      ? ctx.options.packages
      : [
          "opencode-goal-plugin",
          "opencode-workaholic",
          "opencode-notify",
          "opencode-autotitle",
          "opencode-token-tracker",
        ]
    if (!names.length) {
      log("tidak ada package yang dimuat (set options.packages)")
      return
    }

    for (const name of names) {
      try {
        const found = resolvePackageEntry(name)
        if (!found) {
          log(`${name}: tidak ditemukan di ${NPM_CACHE} — dilewati`)
          continue
        }
        const mod = await import(pathToFileURL(found.abs).href)
        const def = mod.default

        // (a) dukungan V2 native: default = { id, setup }
        if (def && typeof def === "object" && typeof def.setup === "function") {
          await def.setup(ctx)
          log(`${name}: dimuat lewat setup() V2 native (${def.id || name})`)
          continue
        }

        // (b) adapter v2-bridge milik paket
        const bridge = resolveV2Bridge(found.pkgDir)
        if (bridge) {
          const bmod = await import(pathToFileURL(bridge).href)
          if (typeof bmod.createV2Setup === "function" && typeof mod.GoalPlugin === "function") {
            await bmod.createV2Setup(mod.GoalPlugin)(ctx)
            log(`${name}: dimuat lewat v2-bridge paket`)
            continue
          }
        }

        // (c) plugin V1 murni → adapter generik
        const factory =
          typeof def === "function" ? def : typeof mod.server === "function" ? mod.server : null
        if (!factory) {
          log(`${name}: tidak punya entrypoint yang dikenali — dilewati`)
          continue
        }
        const hooks = await factory(v1Context(ctx), ctx.options?.[name] || {})
        await adaptHooks(ctx, hooks, name)
        log(`${name}: dimuat lewat adapter V1 generik`)
      } catch (e) {
        log(`${name}: GAGAL dimuat — ${String(e?.message || e)}`)
      }
    }
  },
}
