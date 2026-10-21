---
description: Analisis oops/panic kernel dari log — culprit, root cause, fix, dan cara verifikasi
agent: oops-analyst
subagent: true
---

Analisis crash kernel dari log di mesin ini. Permintaan: $ARGUMENTS

Langkah:
1. Kumpulkan bukti REAL dari sistem (jangan mengarang log):
   - `dmesg -T | tail -200`
   - `journalctl -k -b --no-pager | tail -200`
   - `journalctl -k -b -1 --no-pager | tail -100` (boot sebelumnya, kalau ada)
   - `/var/log/kern.log` (grep BUG/oops/panic/Call Trace)
2. Kalau tidak ada oops di boot ini, cari di boot sebelumnya / kern.log dan sebutkan sumbernya.
3. Klasifikasi crash (NULL deref / OOB / UAF / race / atomic-sleep / lockup / rcustall),
   decode `RIP` + `Code:`, baca `Modules linked in:`.
4. Output: ringkasan → bukti (kutip log) → root cause (hipotesis utama + alternatif + confidence)
   → fix konkret (file/fungsi) → langkah verifikasi.
5. Kalau datanya belum cukup, tulis persis data yang dibutuhkan (bukan mengarang).

Jangan mengklaim "selesai" tanpa kutip log sebagai bukti.
