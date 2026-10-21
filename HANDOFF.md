# HANDOFF — kernel-specialist

Status antar mesin (mesh). Isi ringkas: di mana, apa yang sudah jadi, apa yang next.

## Repo

| Item | Nilai |
|---|---|
| Path (Kali) | `/root/kernel-lab/kernel-specialist` |
| Path (workspace) | `07-SISTEM/kernel-specialist/` |
| Fork/source | `https://github.com/bryanleeanito/kernel-specialist.git` (belum di-push — perlu token) |
| Mesh kit prefix | `kernel-` |

## Status per mesin

| Mesin | Role mesh | Capability | Status |
|---|---|---|---|
| Kali (OpenCode #2) | `kali-kernel` | kernel, kbuild, driver, perf | track + tool siap (2026-10-21) |
| Windows (OpenCode #1) | `windows-dev` | dev, devops, build | butuh clone repo ini + set `KERNEL_SPECIALIST_PATH` |

## Yang sudah (2026-10-21)

- Toolchain kernel terpasang: gcc/clang, bison, flex, bc, libelf-dev, libssl-dev,
  dwarves (pahole 1.32), ccache, lld 21.1.8, rustc 1.95.0, **bindgen 0.72.1**, **rust-src**.
- Source kernel diambil: `apt-get source linux` → `/root/kernel-lab/src/linux-7.1.5`
  (kernel running: `7.1.5+kali-amd64`, patch Kali ikut, 1.8G).
- 4 tool kit + **66/66 assertion** tes lulus (`tests/run_all.py`, 5 berkas tes).
- Track OpenCode terpasang di `~/.config/opencode` (agent `kernel`, `kernel-reviewer`,
  `oops-analyst`, `driver-dev`; command `/kbuild` `/kconfig` `/koops` `/kmodule`
  `/kperf` `/kstatus`; skill `kernel-lab`).
- **Plugin V2**: `kernel-lab` (6 tool + guardrail deny/ask + context + prompt safety),
  `v1-compat` (5 plugin V1 hidup lagi → `/goal`), `dev-journal` (terbukti jalan),
  `shell-env-dev`.
- **Framework** L0–L8 + 3 lapis proteksi → `FRAMEWORK.md`.
- Mesh: mesin terdaftar `kali-kernel`; 4 kit `kernel-*` expose di `mesh_integrator.py`;
  conflict marker ter-commit di repo mesh diperbaiki (tes mesh 18/18 lulus).
- **Secure Boot NONAKTIF** (`SecureBoot=0`, `SetupMode=1`) → kernel custom boleh boot
  tanpa MOK. `/boot` ikut partisi `/` (62G free) — aman untuk 2+ kernel.
- Build baseline semi-custom (bzImage + modules) sedang berjalan dengan tool kit.

## Next

1. Build baseline (semi-custom) dari `/boot/config-$(uname -r)` → `bzImage` + `modules`,
   verify artefak (belum dilakukan — butuh izin, CPU lama).
2. Buat fragment pertama: `perf.conf` (PREEMPT/HZ/BBR) dan `debug.conf`
   (KASAN/PROVE_LOCKING/DEBUG_ATOMIC_SLEEP).
3. Cek Secure Boot (`mokutil --sb-state`) → tentukan strategi boot custom kernel
   (enroll MOK vs nonaktifkan SB) **sebelum** install.
4. Daftarkan mesin ini ke mesh sebagai `kali-kernel` (role `kernel`).
5. Push repo ke GitHub (butuh token — minta user).
6. Di mesin Windows: clone repo ini, set `KERNEL_SPECIALIST_PATH`, expose kit di
   `mesh_integrator.py` (kategori baru "kernel-specialist").

## Jebakan (tercatat, jangan diulang)

- `make install` bisa menimpa `/boot` → dual boot rusak. Selalu staging dulu.
- `CONFIG_RUST=y` → versi rustc harus persis `CONFIG_RUSTC_VERSION_TEXT` (1.95.0).
- `CONFIG_MODULE_SIG=y` → modul custom perlu signed (atau `MODULE_SIG_FORCE=n`).
- `update-grub` bisa menghapus entri Windows (os-prober).
