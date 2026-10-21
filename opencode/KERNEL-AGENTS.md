# KERNEL-AGENTS.md (KALI) — Track Kernel Development (OpenCode #2)

**Track paralel di mesin ini.** Mesin Kali menjalankan **dua jalur** OpenCode:

| Track | Fokus | Agent/command |
|---|---|---|
| `kali-offensive` | offensive, CTF, pentest (lihat `AGENTS.md`) | skill `kali-offensive`, `ctf-prep` |
| **`kali-kernel`** | **kernel kustom/semi-kustom, driver, tuning, debugging boot** | agent `kernel`, command `/kbuild` `/kconfig` `/koops` `/kmodule` `/kperf` `/kstatus` |

**Awal sesi track kernel WAJIB:** baca `MEMORY-KERNEL.md` + `TRACKER-KERNEL.md`
(sibling file di folder config ini) — status build, versi kernel, fragment aktif,
jejebakan yang sudah ketemu.

## Fokus & batas

1. **Kernel dulu.** Kalau task bukan kernel (mis. CTF), pakai track `kali-offensive`
   (skill-nya), bukan agent `kernel`. Jangan campur.
2. **Sumber kebenaran = kernel yang jalan di mesin ini**: `7.1.5+kali-amd64`
   (`uname -r`). Source tree: `/root/kernel-lab/src/linux-7.1.5` (patch Kali ikut).
3. **Semi-custom = base config kernel running** (`/boot/config-$(uname -r)`),
   lalu tambah fragment. Semua driver laptop harus tetap ikut.
4. **Tidak boleh merusak dual-boot Windows.** Layout disk: p3=Windows(ntfs), p5=EFI(976M), p6=Kali ext4(102G, `/boot` ikut sini), p7=swap, p4=D:\ drive(ntfs). Before touch `/boot`, `/lib/modules`,
   `/etc/default/grub`: cek `df -h /boot`, `ls /boot/vmlinuz-*` (kernel stock harus
   ada), `mokutil --sb-state` (Secure Boot). Tanya user sebelum install.
5. **Build out-of-tree** selalu: `make O=/root/kernel-lab/build/linux-7.1.5 ...`.
6. **Tool kit = sumber kebenaran operasional**: `tools/kernel/*/` (env_report,
   config_check, module_inspect, kbuild). Jangan rewrite logika yang sudah ada —
   perbaiki di tool, lalu jalankan `python3 tests/run_all.py` (gate, harus exit 0).
7. **Aturan disiplin platform tetap berlaku** (lihat `AGENTS.md` §Disiplin mutlak):
   hasil nyata + terverifikasi, **dilarang false positive**, update `MEMORY.md` +
   `TRACKER.md` track kernel, bersihkan sisa eksperimen.

## Prasyarat build (cek sebelum compile)

| Kebutuhan | Status di mesin ini |
|---|---|
| gcc/clang/make/bc/bison/flex | terpasang |
| libelf-dev, libssl-dev | terpasang |
| pahole (dwarves) | terpasang 1.32 — wajib karena `CONFIG_DEBUG_INFO_BTF=y` |
| rustc | terpasang **1.95.0** — cocok `CONFIG_RUSTC_VERSION_TEXT` (`CONFIG_RUST=y`) |
| lld | terpasang 21.1.8 — cocok `CONFIG_RUSTC_LLVM_VERSION=210108` |
| ccache | terpasang (pakai `--ccache` di tool kbuild) |

## Loop kerja standar

1. `python3 tools/kernel/env_report/env_report.py` → state mesin.
2. Ubah config **lewat fragment** di `/root/kernel-lab/config/fragments/*.conf`.
   (Tersedia: `perf.conf` 19 opsi, `debug.conf` 22 opsi — keduanya sudah
   divalidasi `config_check` → PASS 0 temuan, tapi **belum dipakai di build**.)
3. Validasi: `tools/kernel/config_check/config_check.py --strict`.
4. Build: `tools/kernel/kbuild/kbuild.py ... --target bzImage --jobs 12 --ccache`.
5. Verifikasi artefak (`bzImage`, `vmlinux`, `Module.symvers`, jumlah `.ko`).
6. Kalau user mau boot → install (dengan izin) + `update-initramfs` + `update-grub`.
7. Tulis hasil ke `MEMORY-KERNEL.md` + geser status di `TRACKER-KERNEL.md`.

**Tool native OpenCode** (lebih cepat & aman daripada shell mentah — lihat namespace
`kernel` di TUI): `kernel_status` · `kernel_preflight` · `kernel_config_check` ·
`kernel_build` · `kernel_module_inspect` · `kernel_crashlog`.
**Guardrail otomatis**: plugin `kernel-lab` menolak perintah berbahaya (deny) dan
meminta persetujuan untuk perintah berisiko (ask) + menyisipkan pengingat
pre-flight saat prompt menyentuh install/boot.

**Framework lengkap (L0–L8 + 3 lapis proteksi)**: `references/framework.md`
(skill `kernel-lab`) atau `FRAMEWORK.md` di repo kit.

## Jebakan yang sudah diketahui (jangan ulangi)

- Secure Boot → custom kernel butuh MOK enrolled; cek `mokutil --sb-state` (install `mok-util`).
- `make install` bisa menimpa `/boot` dan menghilangkan kernel stock → dual boot bisa rusak.
- `CONFIG_RUST=y` → versi rustc harus persis sama tiap Kali update kernel.
- `CONFIG_MODULE_SIG=y` → modul custom perlu signed atau `CONFIG_MODULE_SIG_FORCE=n`.
- `update-grub` + `os-prober` → entri Windows bisa hilang dari GRUB.
- `/boot` **ikut partisi `/`** (bukan partisi kecil) — aman untuk 2+ kernel. Yang kecil =
  partisi EFI 976M di `/boot/efi` (tempat boot loader + shim).
- `GRUB_CMDLINE_LINUX_DEFAULT="quiet"` → boot tidak kelihatan log; **hapus `quiet`**
  sementara saat debug kernel custom (lalu kembalikan).

Detail & SOP lengkap → skill `kernel-lab`.
