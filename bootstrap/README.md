# Kali Lab Bootstrap — restore lingkungan ini di OS fresh

Paket ini dibuat **21 Okt 2026** agar mesin Kali bisa **dibangun ulang (reinstall OS)**
dan hasilnya **sama persis** dengan kondisi sekarang: toolchain, plugin, track OpenCode,
memori, tuning kernel, git, dan mesh.

```
kali-lab-bootstrap/
├── bootstrap.sh        # master: 11 fase idempotent (restore)
├── verify.sh           # cek paritas: state sekarang vs expected.json
├── snapshot.sh         # ambil state mesin → JSON
├── expected.json       # state "benar" (reference paritas)
├── tuning/             # file tuning M2 (sysctl + modules-load) untuk disalin
├── opencode.json       # template config OpenCode v2
└── README.md           # dokumen ini
```

## Cara pakai (fresh install Kali)

```sh
# 1. pastikan drive D: ter-mount (isi drive = source of truth offline)
ls /run/media/*/*/CyberSecurity*        # harus ada

# 2. clone paket ini (kalau drive tidak ada: dari GitHub)
git clone git@github.com:bryanleeanito/kernel-specialist.git /root/kernel-lab/kernel-specialist
cp -r /root/kernel-lab/kernel-specialist/bootstrap /root/kernel-lab/bootstrap

# 3. jalankan restore
sudo bash /root/kernel-lab/bootstrap/bootstrap.sh

# 4. cek hasilnya identik
bash /root/kernel-lab/bootstrap/verify.sh
```

Output `verify.sh`:
```
  [SAMA]  plugins          [...]
  [SAMA]  agents           [...]
  [SAMA]  tuning           {...}
  [BEDA]  packages         <-- yang kurang
RESULT: PARITAS OK — mesin sama persis dengan expected.json
```

## Fase bootstrap

| # | Fase | Yang dilakukan | Idempotent |
|---|---|---|---|
| 0 | preflight | cek root, OS, kernel, drive, kit | ya |
| 1 | base-pkg | apt: toolchain kernel (gcc/bison/dwarves/lld/rustc/bindgen/rust-src/headers) + node/jq/cpio/zstd | ya |
| 2 | offensive-tools | jalankan `09-MIGRASI/kali-tools.sh` (tool offensive + node/uv) | ya |
| 3 | skills | skills eksternal → `~/.agents/skills`; skill track kernel → `~/.config/opencode/skills` | ya |
| 4 | plugins | `kernel-lab` `kali-ops` `v1-compat` `dev-journal` `shell-env-dev` → `~/.config/opencode/plugins` (+ instance #1) | ya |
| 5 | track-config | `install.sh` kit → agent `kernel`/`kernel-reviewer`/`oops-analyst`/`driver-dev`, command `/kbuild` `/kconfig` `/koops` `/kmodule` `/kperf` `/kstatus`, skill `kernel-lab`, `KERNEL-AGENTS.md` | ya |
| 6 | memory | restore `MEMORY.md` `TRACKER.md` `AGENTS.md` (offensive) + `MEMORY-KERNEL.md` `TRACKER-KERNEL.md` `KERNEL-AGENTS.md` (kernel) + `opencode.json` v2 | ya |
| 7 | tuning | `/etc/sysctl.d/99-kernel-lab.conf` + `/etc/modules-load.d/kernel-lab.conf` → BBR+FQ, buffer 16 MB, swappiness 10, cache pressure 50 | ya |
| 8 | git | identitas `kzldx`, credential helper (baca env var, **tanpa** file kredensial), SSH key (cetak public key), remote SSH, token MCP github | ya |
| 9 | mesh | daftar `kali-kernel` (role kernel) + presence (IP DHCP aman) | ya |
| 10 | verify | paritas vs `expected.json` | ya |

Opsi: `--only=4,5` · `--skip=7` · `--list`

## Kenapa begini (keputusan desain)

1. **Drive D: = source of truth offline.** GitHub butuh SSH key/token; drive selalu ada di laptop.
2. **Idempoten** — bisa dijalankan berulang; fase yang sudah beres dilewati (aman kalau dipanggil ulang).
3. **Privat key TIDAK disimpan di drive** (drive = NTFS, permission longgar). Bootstrap
   **membuat key baru** & mencetak public key → cukup 1 tempelan di GitHub.
4. **Credential = env var saja** (sesuai aturan platform): git credential helper membaca
   `$GITHUB_TOKEN`; tidak ada `~/.git-credentials`.
5. **Paritas diukur, bukan diklaim** — `expected.json` + `verify.sh` jadi bukti "sama persis".
6. **Memori per-OS** (`MEMORY.md`/`TRACKER.md` platform) tidak ditimpa sembarangan: fase 6
   selalu backup dulu (`*.bak-<timestamp>`).

## Isi state yang di-restore (ringkas)

| Area | Isi |
|---|---|
| Toolchain | gcc/clang, bison, flex, dwarves(pahole), lld, ccache, rustc 1.95 + rust-src + bindgen, kernel-headers, node, jq |
| Plugin (5) | `kernel-lab` (tool kernel + guardrail), `kali-ops` (co-pilot sistem), `v1-compat` (adapter plugin V1), `dev-journal`, `shell-env-dev` |
| Agent/Command/Skill | `kernel` `kernel-reviewer` `oops-analyst` `driver-dev` · `/kbuild /kconfig /koops /kmodule /kperf /kstatus` · skill `kernel-lab` |
| Tool native | namespace `kernel` (6) + `kali` (8) |
| Memori | `MEMORY.md` `TRACKER.md` `AGENTS.md` + varian `-KERNEL` (dari drive bersama `07-SISTEM/kernel-lab/`) |
| Tuning M2 | BBR + FQ, buffer 16 MB, swappiness 10, vfs_cache_pressure 50 (persist reboot) |
| Git | identitas, credential helper (env), SSH remote untuk 3 repo |
| Mesh | `kali-kernel` terdaftar + presence |
| Repo | `kernel-specialist` · `kali-ops` · `opencode-mesh-v2` (GitHub, via SSH) |

## Kalau OS-nya Windows (untuk OpenCode #1)

Repo yang sama: `git clone git@github.com:bryanleeanito/kernel-specialist.git` →
`install.sh` (PowerShell/WSL) → agent `kernel` + tool `kernel`/`kali` aktif.
Memori track kernel ada di `docs/machine-local/` (salinan) — salin manual ke
`%USERPROFILE%\.config\opencode\`.

## Changelog

- **2026-10-21** — paket dibuat: 11 fase bootstrap + verifier paritas + expected.json.
