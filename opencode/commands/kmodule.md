---
description: Operasi modul kernel — build, inspeksi, pasang, dan troubleshoot .ko
agent: driver-dev
subagent: true
---

Kerjakan operasi modul kernel ini: $ARGUMENTS

Alur wajib:
1. `uname -r` → kernel target. Modul **wajib** built terhadap tree versi yang sama.
2. Build: `make -C /lib/modules/$(uname -r)/build M=$PWD modules`
   (kalau symlink `build` tidak ada → pakai `/root/kernel-lab/src/linux-7.1.5` dan set `KDIR`).
3. Inspeksi SEBELUM pasang:
   `python3 /root/kernel-lab/kernel-specialist/tools/kernel/module_inspect/module_inspect.py --module <file.ko>`
   → cek `vermagic` == `uname -r`, `signer`, symbol undefined vs `Module.symvers`.
   Vermagic beda = modul tidak akan bisa dimuat → rebuild, jangan dipaksa.
4. Pasang hanya atas izin: `insmod <file.ko>` (atau `depmod -a` + `modprobe <nama>`),
   lalu verifikasi `dmesg | tail -20`, `lsmod`, `/sys/module/<nama>/`.
5. Unload: `rmmod <nama>` (hanya kalau tidak sedang dipakai).
6. Output: nama modul, kernel target, hasil modinfo (vermagic/signer), status build,
   dan bukti terpasang/tidak (`lsmod`/`dmesg`). Kalau gagal → tampilkan error pertama.
