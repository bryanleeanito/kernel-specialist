---
description: Build kernel (kustom/semi-kustom) dengan aman — config → compile → verifikasi artefak
agent: kernel
---

Build kernel di mesin ini. Target permintaan: $ARGUMENTS

Ketentuan:
1. Kalau argumen kosong → build default: source tree `/root/kernel-lab/src/linux-7.1.5`,
   out `/root/kernel-lab/build/linux-7.1.5`, base config `/boot/config-$(uname -r)`
   (semi-custom: pertahankan semua driver laptop), target `bzImage` + `modules`, `-j12`, ccache.
2. **Cek prasyarat dulu** (rustc/pahole/bison/flex/bc/libelf/openssl) vs opsi di config.
   Kalau ada yang tidak cocok → laporkan sebelum build, jangan.build paksa.
3. Build via tool kit:
   `python3 /root/kernel-lab/kernel-specialist/tools/kernel/kbuild/kbuild.py --tree ... --out ... --base-config ... --fragment ... --target bzImage --jobs 12 --ccache`
4. **Jangan** `make install` / `modules_install` ke `/` tanpa izin user. Default staging saja.
5. Setelah selesai: laporkan rc make, waktu build, artefak (path + ukuran),
   jumlah `.ko`, dan error pertama kalau gagal (cuplik log, bukan ringkasan kabur).
6. Kalau `$ARGUMENTS` menyebut fragment, pakai fragment itu; kalau nama fragment tidak ada → buat
   di `/root/kernel-lab/config/fragments/<nama>.conf` dan jelaskan isinya.

Output: ringkas + terstruktur, bukti nyata (angka dari output make).
