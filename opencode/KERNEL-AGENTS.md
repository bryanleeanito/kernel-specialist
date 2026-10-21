# KERNEL-AGENTS.md (KALI) — Track Kernel Ops & Dev (OpenCode #2)

**Track paralel di mesin ini.** Mesin Kali menjalankan **dua jalur** OpenCode:

| Track | Fokus | Agent/command |
|---|---|---|
| `kali-offensive` | offensive, CTF, pentest (lihat `AGENTS.md`) | skill `kali-offensive`, `ctf-prep` |
| **`kali-kernel`** | **kernel: analisis, debugging crash, tuning runtime, driver/modul OOT** | agent `kernel`, command `/kbuild` `/kconfig` `/koops` `/kmodule` `/kperf` `/kstatus` |

> **Mode default: M1–M3 (tanpa build kernel penuh).** Build kernel custom penuh
> **DIBATALKAN** (21 Okt 2026): butuh 1,5–2 jam + 5,6 GB + 4.020 modul → overkill
> untuk laptop 6C/12T. Source tree pun dihapus (hemat 1,9 GB). Jadi track ini
> fokus ke: (M1) baca & debug kernel running, (M2) tuning runtime tanpa rebuild
> (`sysctl`/scheduler/BBR/governor), (M3) driver/modul out-of-tree (build detik).
> (M4) build kernel penuh hanya kalau user **spesifik minta** + menyetujui
> waktu/storage-nya → wajib `localmodconfig` + `install-kernel.sh` (dry-run dulu).

**Awal sesi track kernel WAJIB:** baca `MEMORY-KERNEL.md` + `TRACKER-KERNEL.md`
(sibling file di folder config ini) — status, versi kernel, jejak tuning,
jejebakan yang sudah ketemu.

## Fokus & batas

1. **Kernel dulu.** Kalau task bukan kernel (mis. CTF), pakai track `kali-offensive`
   (skill-nya), bukan agent `kernel`. Jangan campur.
2. **Sumber kebenaran = kernel yang jalan di mesin ini**: `7.1.5+kali-amd64`
   (`uname -r`). **Source tree TIDAK ada** (dihapus 21 Okt 2026, hemat 1,9 GB) —
   jangan-build kernel kecuali user minta (M4).
3. **Tuning default = runtime, bukan rebuild** (M2): `sysctl` (`/etc/sysctl.d/99-kernel-lab.conf`),
   scheduler I/O, governor CPU, BBR/FQ, page cache. 1 variabel per iterasi + ukur before/after.
4. **Tidak boleh merusak dual-boot Windows.** Layout disk: p3=Windows(ntfs), p5=EFI(976M), p6=Kali ext4(102G, `/boot` ikut sini), p7=swap, p4=D:\ drive(ntfs). Before touch `/boot`, `/lib/modules`,
   `/etc/default/grub`: cek `df -h /boot`, `ls /boot/vmlinuz-*` (kernel stock harus
   ada), Secure Boot (efivars `SecureBoot-` — `mokutil` tidak ada di Kali). Tanya user sebelum install.
5. **Modul OOT = jalur "ngoprek kernel" yang murah** (M3): 1 file C + Makefile,
   `KDIR=/lib/modules/$(uname -r)/build` → build detik, `vermagic` wajib cocok.
6. **Tool kit = sumber kebenaran operasional**: `tools/kernel/*/` (env_report,
   config_check, module_inspect, kbuild). Jangan rewrite logika yang sudah ada —
   perbaiki di tool, lalu jalankan `python3 tests/run_all.py` (gate, harus exit 0).
7. **Aturan disiplin platform tetap berlaku** (lihat `AGENTS.md` §Disiplin mutlak):
   hasil nyata + terverifikasi, **dilarang false positive**, update `MEMORY.md` +
   `TRACKER.md` track kernel, bersihkan sisa eksperimen.

## Prasyarat (cek sebelum compile)

| Kebutuhan | Status di mesin ini |
|---|---|
| gcc/clang/make/bc/bison/flex | terpasang |
| libelf-dev, libssl-dev | terpasang |
| pahole (dwarves) | terpasang 1.32 — wajib karena `CONFIG_DEBUG_INFO_BTF=y` |
| rustc | terpasang **1.95.0** — cocok `CONFIG_RUSTC_VERSION_TEXT` (`CONFIG_RUST=y`) |
| lld | terpasang 21.1.8 — cocok `CONFIG_RUSTC_LLVM_VERSION=210108` |
| ccache | terpasang (pakai `--ccache` di tool kbuild) |
| bindgen + rust-src | terpasang (wajib kalau `CONFIG_RUST=y`) |
| `linux-headers-$(uname -r)` | **cek** — untuk modul OOT (M3) saja |

## Loop kerja standar

**M1 — baca & debug:**
1. `kernel_status` (tool) atau `python3 tools/kernel/env_report/env_report.py`.
2. Untuk crash: `kernel_crashlog` → subagent `oops-analyst` (klasifikasi + root cause + fix).
3. Untuk modul: `kernel_module_inspect` / `lsmod` / `/sys/module`.
4. Tulis hasil ke `MEMORY-KERNEL.md` + geser status di `TRACKER-KERNEL.md`.

**M2 — tuning runtime:**
1. Ukur baseline dulu (iostat/vmstat/curl timing).
2. Ubah **1** variabel via `sysctl` (catat nilai awal buat rollback).
3. Ukur ulang → putuskan lanjut/revert. Catat di `MEMORY-KERNEL.md`.

**M3 — modul OOT:**
1. Lihat `MEMORY-KERNEL.md` §M3 (resep Makefile + C minimal).
2. `make` → `modinfo` (vermagic wajib = `uname -r`) → `insmod` → `dmesg` → `rmmod`.
3. Kalau butuh simbol kernel yang tidak diekspor → cek `Module.symvers`/ksym.

**M4 — build kernel penuh (hanya kalau diminta):**
1. Fragment via `/root/kernel-lab/config/fragments/*.conf` (perf.conf / debug.conf
   sudah tervalidasi `config_check` → PASS 0 temuan).
2. Validasi: `tools/kernel/config_check/config_check.py --strict` (butuh source tree).
3. Build: `tools/kernel/kbuild/kbuild.py ... --target all --jobs 12 --ccache`
   → **wajib `localmodconfig`** (bukan config penuh) + `LOCALVERSION` berbeda.
4. Verifikasi artefak → staging install → `install-kernel.sh` (dry-run dulu) →
   `update-initramfs` + `update-grub` (dengan izin user).

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
