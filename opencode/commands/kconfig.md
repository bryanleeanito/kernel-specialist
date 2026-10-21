---
description: Kelola config kernel — tampilkan, ubah via fragment, validasi, dan ringkas diff
agent: kernel
---

Kerjakan permintaan config kernel ini: $ARGUMENTS

Alur wajib:
1. **Tampilkan kondisi sekarang** dulu: `grep -E '^CONFIG_' /root/kernel-lab/build/linux-7.1.5/.config`
   (atau `/boot/config-$(uname -r)` kalau build belum ada) untuk opsi yang relevan.
2. **Selalu lewat fragment**, jangan edit `.config` langsung (susah dilacak):
   fragment di `/root/kernel-lab/config/fragments/*.conf`.
   Buat fragment baru kalau perlu — isi hanya baris `CONFIG_X=y/m/n`, satu baris satu opsi,
   tanpa `#` penjelasan di dalam file.
3. **Validasi** sebelum build:
   `python3 /root/kernel-lab/kernel-specialist/tools/kernel/config_check/config_check.py --tree /root/kernel-lab/src/linux-7.1.5 --fragment <fragment> --strict`
   Tool ini mengecek: symbol dikenal tree, baseline boot wajib, dan kombinasi berisiko
   (MODULE_SIG_FORCE, RUST tanpa rustc cocok, BTF tanpa pahole, LOCK_DOWN).
4. Kalau ada error → jelaskan & perbaiki (jangan lanjut build dengan config rusak).
5. Ringkas diff config: opsi yang berubah + dampak yang diharapkan + opsi terkait
   yang sebaiknya ikut berubah (mis. ubah `CONFIG_HZ` → `CONFIG_HZ_*` + `CONFIG_NO_HZ_*`).

Kalau argumen kosong → tampilkan ringkasan config saat ini + daftar fragment yang ada.
