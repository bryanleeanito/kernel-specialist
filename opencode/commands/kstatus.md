---
description: Status lab kernel (source tree, build, config, modul, kernel running)
agent: kernel
---

Laporkan status environment kernel development mesin ini. Gunakan tool kit
`/root/kernel-lab/kernel-specialist/tools/kernel/env_report/env_report.py` (mode text) sebagai data utama,
lalu ringkas jadi tabel ringkas:

| item | nilai |
|---|---|
| kernel running | `uname -r` |
| source tree | path + versi + status git |
| build dir | artefak (bzImage/vmlinux/Module.symvers/.ko) + waktu build terakhir |
| config | sumber base config + fragment aktif |
| toolchain | gcc/clang/rustc/pahole/ccache/bison — yang hilang sebutkan |
| secure boot | state (penting untuk dual-boot) |
| /boot free | ruang (wajib cukup untuk 2 kernel) |

Tambahkan 3 baris **rekomendasi langkah berikutnya** yang paling logis.
Jangan mengarang nilai — kalau tool gagal, tulis apa yang gagal.
