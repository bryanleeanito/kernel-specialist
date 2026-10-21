# Kernel Specialist

Kit + track OpenCode untuk **pengembangan kernel kustom/semi-kustom** di mesin Kali.
Ini adalah counterpart dari `windev-specialist` (OpenCode #1 di mesin Windows):
yang Windows berada di `07-SISTEM/windev-specialist`, yang ini
di `07-SISTEM/kernel-specialist`.

Dibuat 2026-10-21 · untuk mesin Kali (OpenCode #2, root).

## Peran

| | windev-specialist | kernel-specialist |
|---|---|---|
| Mesin | Windows 10/11 (OpenCode #1) | Kali Linux (OpenCode #2) |
| Fokus | dev, devops, build, deploy, otomasi | **kernel kustom/semi-kustom, driver, tuning, boot debug** |
| Platform | Windows-first | Linux-first (Kali) |
| Kit | `tools/{sysadmin,dev,security}/` | `tools/kernel/{env_report,config_check,module_inspect,kbuild}/` |

## Struktur

```
opencode/            ← track OpenCode (agent, command, skill, instruksi)
  KERNEL-AGENTS.md     instruksi track kernel (diload sebagai instructions)
  agents/              kernel · kernel-reviewer · oops-analyst · driver-dev
  commands/            /kbuild /kconfig /koops /kmodule /kperf /kstatus
  skills/kernel-lab/   SOP: source tree, config baseline, build, install, jebakan dual-boot
  plugins/             kernel-lab.js · v1-compat.js · dev-journal.js · shell-env-dev.js
tools/kernel/        ← kit executable (dipakai mesh + skill)
  env_report/          snapshot environment kernel dev (read-only)
  config_check/        validasi .config/fragment terhadap tree
  module_inspect/      inspeksi .ko: vermagic, signature, symbol
  kbuild/              wrapper build aman (staging, nunca sentuh /boot tanpa flag)
tests/run_all.py     ← gate: semua tes harus lulus (exit 0)
tests/test_guardrail.mjs ← unit test guardrail plugin (deny/ask)
FRAMEWORK.md         ← framework L0–L8 + 3 lapis proteksi
install.sh           ← pasang track ke ~/.config/opencode (backup otomatis)
HANDOFF.md           ← status antar mesin (mesh)
```

## Plugin (OpenCode v2)

| plugin | fungsi |
|---|---|
| `kernel-lab.js` | 6 tool kernel native (`kernel_status`, `kernel_preflight`, `kernel_config_check`, `kernel_build`, `kernel_module_inspect`, `kernel_crashlog`) + **guardrail** (permission hook deny/ask) + injeksi context kernel + pengingat pre-flight di prompt |
| `v1-compat.js` | memuat plugin OpenCode **v1** (goal/workaholic/notify/autotitle/token-tracker) lewat adapter → default export v2 `{id, setup}` |
| `dev-journal.js` | mencatat tiap perintah shell + hasilnya ke `~/.config/opencode/journal/commands.log` |
| `shell-env-dev.js` | env shell: UTF-8, no bytecode, path journal |

Aman: semua error ditangkap (tidak menjatuhkan agent loop), I/O tanpa shell
interpolation, dan guardrail punya **unit test** (32 assertion).

## Area kerja di mesin Kali (bukan di repo)

```
/root/kernel-lab/
  src/linux-7.1.5/         source tree (apt-get source linux — patch Kali)
  build/linux-7.1.5/       build out-of-tree (O=)
  config/fragments/        fragment .conf (satu opsi per baris)
  logs/                    log build
  kernel-specialist/       salinan tool kit (hasil install.sh)
```

## Pakai tool

```sh
python3 tools/kernel/env_report/env_report.py            # report manusia
python3 tools/kernel/env_report/env_report.py --json     # untuk agent/script

python3 tools/kernel/config_check/config_check.py \
    --tree /root/kernel-lab/src/linux-7.1.5 \
    --fragment /root/kernel-lab/config/fragments/perf.conf --strict

python3 tools/kernel/module_inspect/module_inspect.py --module x.ko

python3 tools/kernel/kbuild/kbuild.py \
    --tree /root/kernel-lab/src/linux-7.1.5 \
    --out  /root/kernel-lab/build/linux-7.1.5 \
    --base-config /boot/config-$(uname -r) \
    --target bzImage --jobs 12 --ccache
```

## Test

```sh
python3 tests/run_all.py     # gate — harus exit 0
```

## Integrasi mesh

Tool ini diekspos ke mesh sebagai kit berawalan `kernel-`:
`kernel-env-report`, `kernel-config-check`, `kernel-module-inspect`, `kernel-kbuild`.
Mesin Windows (role `development`) bisa mendelegasikan tugas kernel ke mesin ini
(role `kernel`) lewat `mesh_integrator.py --kit kernel-*`.

### Cara OpenCode #1 (Windows) memakai mesin ini

Mesin ini terdaftar di mesh sebagai **`kali-kernel`** (role `kernel`,
IP `192.168.14.99`, capability `kernel,kbuild,driver,perf,debug`).

1. **Jalankan kit langsung dari mesin Windows** (butuh repo kit di sisi Windows):
   ```sh
   python3 scripts/mesh_integrator.py run-kit --kit kernel-env-report --command ""
   python3 scripts/mesh_integrator.py run-kit --kit kernel-config-check \
       --command "--tree C:\\path\\linux-7.1.5 --fragment kernel.conf"
   ```
2. **Delegasi task** (task masuk antrean state mesh, diambil mesin ini):
   ```sh
   python3 scripts/mesh_integrator.py delegate-kit --to kali-kernel \
       --kit kernel-kbuild --command "--tree ... --target bzImage"
   ```
3. **Install kit di sisi Windows** (kalau repo belum ada):
   ```sh
   git clone <repo-kernel-specialist> ; cd kernel-specialist ; sh install.sh
   ```
   lalu set env var agar mesh menemukan kit:
   `KERNEL_SPECIALIST_PATH=/path/ke/kernel-specialist`
4. **Batas**: dual-boot → mesin Kali harus hidup agar delegasi bisa diproses.
   Kalau Kali mati, kerjakan langsung di sisi Windows (repo kit sama persis).

## Aturan repo

1. **Credentials = env var only.** Never hardcode.
2. **Output kerja jangan di-commit** — artefak build, bukan source.
3. **Read-only pada target data** sampai operator konfirmasi perubahan.
4. **Redact kredensial real** di output (`<REDACTED>`).
5. **Test wajib jalan** — perubahan tool harus lolos `tests/run_all.py`.
6. **Jangan sentuh `/boot`** dari tool tanpa flag eksplisit (`kbuild --install`).

## Changelog

- **2026-10-21** — repo dibuat: 4 tool (env_report, config_check, module_inspect,
  kbuild) + track OpenCode (4 agent, 6 command, 1 skill) + gate tes 34/34 lulus.
