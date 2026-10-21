---
description: Build kernel custom (opsional & berat) — config → compile → verifikasi. Tawarkan alternatif tuning runtime lebih dulu.
agent: kernel
---

Build kernel custom di mesin ini. Permintaan: $ARGUMENTS

**Peringatan biaya (wajib disampaikan sebelum build):**
config stock Kali = **4.020 modul** → ~12.000 objek → **±1,5–2 jam** di laptop ini
(6C/12T) + **±5,6 GB** artefak + **±1,4 GB** ccache. Mengganti 1 opsi config =
rebuild ~90% objek (ccache hit anjlok ~5%).

Karena itu:
1. **Tawarkan alternatif lebih dulu** (santai, 0 build):
   - tuning runtime (`/kperf`) — BBR/FQ/sysctl/governor/I/O scheduler;
   - modul out-of-tree (`/kmodule`) — untuk driver/fitur kecil.
  Ingat: kalau permintaannya sebenarnya "agar kernel lebih cepat/fitur X", 90% kasus
   bisa beres tanpa build kernel.
2. **Build hanya kalau** user tetap minta DAN understands biayanya. Tetap wajib:
   - **source tree** harus ada (saat ini TIDAK ada → `deb-src` Kali + `apt-get source linux`);
   - **`localmodconfig`**, bukan config penuh (potong 4.020 modul → hanya yang dipakai);
   - `LOCALVERSION` berbeda (fragment `localversion.conf` → `7.1.5+kali-amd64-custom`)
     supaya **tidak menimpa** kernel stock;
   - `config_check --strict` dulu (symbol dikenal tree, baseline boot utuh).
3. Eksekusi via tool kit:
   `python3 /root/kernel-lab/kernel-specialist/tools/kernel/kbuild/kbuild.py --tree ... --out ... --base-config ... --fragment ... --target all --jobs 12 --ccache`
4. **Jangan** `make install` / `modules_install` ke `/` tanpa izin. Default staging saja.
   Install wajib lewat `install-kernel.sh` (dry-run dulu, pre-flight + rollback).
5. Laporkan: rc make, waktu build, artefak (path + ukuran), jumlah `.ko`, dan error
   pertama kalau gagal (cuplik log, bukan ringkasan kabur).
