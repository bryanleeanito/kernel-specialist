---
name: Kernel Lab
description: Alur kerja kernel development di mesin Kali — source tree Kali, config baseline, build out-of-tree, fragment config, modul, install aman, dan jebakan dual-boot. Gunakan saat mengerjakan build/config/modul kernel.
metadata:
  opencode/autoinvoke: true
---

# Kernel Lab — SOP mesin Kali (OpenCode #2)

Skill ini berisi **prosedur kerja** track kernel. Load saat mulai mengerjakan
build/config/modul kernel di mesin ini.

## Peta path (fakta)

| Kebutuhan | Path |
|---|---|
| Source tree (patch Kali) | `/root/kernel-lab/src/linux-7.1.5` |
| Build dir (O=) | `/root/kernel-lab/build/linux-7.1.5` |
| Base config (semi-custom) | `/boot/config-$(uname -r)` |
| Fragment config | `/root/kernel-lab/config/fragments/*.conf` |
| Log build | `/root/kernel-lab/logs/kbuild-*.log` |
| Tool kit | `/root/kernel-lab/kernel-specialist/tools/kernel/*/` |
| Repo kit + config | `/root/kernel-lab/kernel-specialist/` |

## Sumber kernel (kalau tree belum ada)

```sh
# 1) aktifkan deb-src Kali
cat > /etc/apt/sources.list.d/kali-src.sources <<'EOF'
Types: deb-src
URIs: http://http.kali.org/kali/
Suites: kali-rolling
Components: main contrib non-free non-free-firmware
Signed-By: /usr/share/keyrings/kali-archive-keyring.gpg
EOF
apt-get update
# 2) ambil source kernel yang PERSIS versi yang jalan
cd /root/kernel-lab/src && apt-get source linux
```

Hasil: `linux-<versi>` (mis. `linux-7.1.5`) berisi tree + patch Debian/Kali.
`apt-get source` butuh paket build: `dpkg-dev`, `debhelper`, `fakeroot` (untuk `make bindeb-pkg`).

## Prasyarat build (verifikasi, jangan diasumsikan)

| Kebutuhan | Pemeriksaan | Kenapa |
|---|---|---|
| gcc/clang/make/bc/bison/flex | `command -v gcc bison flex bc` | build basic |
| libelf + openssl dev | `dpkg -l libelf-dev libssl-dev` | signing/BTF |
| pahole (dwarves) | `command -v pahole` | `CONFIG_DEBUG_INFO_BTF=y` |
| rustc (+clang) | `rustc --version` vs `CONFIG_RUSTC_VERSION_TEXT` | `CONFIG_RUST=y` (Kali: rustc 1.95.0) |
| ccache | `command -v ccache` | iterasi cepat |
| lld (LLVM) | `ld.lld --version` | opsional `LLVM=1` |

Kalau `CONFIG_RUST=y` tapi versi rustc tidak sama dengan `CONFIG_RUSTC_VERSION_TEXT`
→ build akan gagal dengan pesan versi; jangan dipaksa, samakan dulu.

## SOP: build semi-custom (aman)

```sh
# base = config kernel yang sedang jalan (semua driver laptop ikut)
cp /boot/config-$(uname -r) /root/kernel-lab/build/linux-7.1.5/.config

# pakai tool kit (merge fragment + olddefconfig + build + verifikasi artefak)
python3 /root/kernel-lab/kernel-specialist/tools/kernel/kbuild/kbuild.py \
  --tree /root/kernel-lab/src/linux-7.1.5 \
  --out  /root/kernel-lab/build/linux-7.1.5 \
  --base-config /boot/config-$(uname -r) \
  --fragment /root/kernel-lab/config/fragments/<nama>.conf \
  --target bzImage --jobs 12 --ccache
```

Manual equivalent:
```sh
cd /root/kernel-lab/src/linux-7.1.5
make O=/root/kernel-lab/build/linux-7.1.5 olddefconfig
make O=/root/kernel-lab/build/linux-7.1.5 -j12 CCACHE_ENABLE=1 bzImage modules
```

## SOP: fragment config

- Satu baris satu opsi: `CONFIG_X=y` / `=m` / `=n` (atau `# CONFIG_X is not set`).
- Tanpa komentar di dalam file fragment (komentar disimpan di MEMORY/HANDOFF).
- Validasi sebelum build:
```sh
python3 /root/kernel-lab/kernel-specialist/tools/kernel/config_check/config_check.py \
  --tree /root/kernel-lab/src/linux-7.1.5 --fragment <frag> --strict
```

## SOP: install (BERBAHAYA — dual-boot)

Checklist sebelum install:
1. Kernel stock Kali masih ada & bootable (`ls /boot/vmlinuz-*`) — **jangan dihapus**.
2. Ruang `/boot` cukup untuk 2 kernel + initramfs (`df -h /boot`).
3. Secure Boot state dicek: `mokutil --sb-state` (butuh `mok-util`).
   - SB **aktif** → kernel custom tidak akan boot (tanda MOK belum di-enroll).
4. Partisi `/boot` EFI + Windows Boot Manager tetap utuh (dual-boot).

Langkah (hanya atas izin user):
```sh
make O=/root/kernel-lab/build/linux-7.1.5 modules_install
make O=/root/kernel-lab/build/linux-7.1.5 install
update-initramfs -c -k <versi-kernel>     # atau: mkinitramfs -o /boot/initrd.img-<versi> <versi>
update-grub                                  # cek /etc/default/grub (GRUB_TIMEOUT, os-prober)
```

Rollback: boot ke kernel stock (GRUB → Advanced options) lalu `apt remove linux-image-<versi-custom>`.

## Jebakan khas mesin ini (dual-boot Windows + Kali)

1. **Secure Boot**: custom kernel tidak boot tanpa MOK. Solusi: `mokmanager` (enroll MOK) atau
   nonaktifkan SB. Cek dulu sebelum build, jangan setelah boot gagal.
2. **`make install` menimpa `/boot`**: kernel stock bisa hilang → dual boot bisa rusak.
   Selalu `--install-to /boot/staging` dulu untuk uji.
3. **`update-initramfs`**: initramfs lama sering jadi penyebab boot gagal setelah kernel update.
4. **NVIDIA/AMD GPU proprietary**: `CONFIG_MAKEFILE_OUTPUT`/DKMS harus rebuilt — `dkms status`.
5. **ZFS/NFS**: modul besar, build lebih lama; `CONFIG_ZFS` perlu `CONFIG_CRYPTO` user API.
6. **Rust in kernel**: `CONFIG_RUST=y` butuh rustc versi persis; kalau Kali update kernel,
   `CONFIG_RUSTC_VERSION_TEXT` ikut berubah → cek ulang tiap build.
7. **`/boot` kecil di laptop**: 2 kernel + 2 initramfs bisa penuh → cek `df -h /boot` dulu.
8. **Windows boot manager**: `os-prober` Sometimes disabled → entri Windows hilang dari GRUB
   setelah `update-grub`. Cek `/etc/grub.d/`.

## Modul (.ko)

```sh
# build OOT
make -C /lib/modules/$(uname -r)/build M=$PWD modules
# verifikasi SEBELUM pasang
python3 /root/kernel-lab/kernel-specialist/tools/kernel/module_inspect/module_inspect.py --module x.ko
# pasang (vermagic harus == uname -r)
insmod x.ko && dmesg | tail -20
```

## Aftercare (wajib)

- Update `MEMORY.md` + `TRACKER.md` track kernel (aturan disiplin platform).
- Bersihkan artefak eksperimen yang tidak dipakai (out-of-tree dir lama, log > 7 hari).
- Kalau install sukses: catat versi, cara boot fallback, dan status `update-grub`.
