---
description: Tuning performa kernel TANPA rebuild (sysctl/scheduler/governor/BBR) + opsi config-level bila diminta
agent: kernel
---

Optimalkan performa kernel di mesin ini. Permintaan: $ARGUMENTS

**Aturan utama: utamakan tuning RUNTIME (M2) — tanpa rebuild.**
Kernel stock Kali sudah punya BBR, FQ, ZSWAP, XFS_RT, KFENCE, `HZ_250`,
`PREEMPT_DYNAMIC` → yang perlu cuma menyalakan & menyetel.

Langkah wajib:
1. **Ukur baseline dulu** (tidak boleh klaim tanpa angka):
   - I/O: `iostat -x 1 3` (antrian + throughput)
   - Load/RAM: `vmstat 1 3`, `free -h`
   - Latensi app (kalau ada target): `curl -o /dev/null -s -w "%{time_total}\n" <url>` (5x)
   - Scheduler I/O: `cat /sys/block/*/queue/scheduler`
   - Governor CPU: `cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor`
   - TCP: `sysctl net.ipv4.tcp_congestion_control net.core.default_qdisc`
2. **Usulkan 1–3 perubahan** dengan tabel: parameter | nilai sekarang | nilai usulan |
   alasan | cara ukur | cara rollback (nilai awal).
3. **Terapkan 1 per iterasi** (`sysctl -w` dulu, uji, baru permanen di
   `/etc/sysctl.d/99-kernel-lab.conf`), ukur ulang, bandingkan dengan baseline.
4. **Kalau yang diminta butuh level config (rebuild)**: JANGAN langsung build —
   laporkan dulu biayanya (±1,5–2 jam, ±5,6 GB, 4.020 modul) dan tawarkan alternatif
   runtime. Build hanya atas izin eksplisit + wajib `localmodconfig`.
5. Update `MEMORY-KERNEL.md` (nilai akhir + cara rollback) dan `TRACKER-KERNEL.md`.

Jangan mengarang angka performa — bandingkan hasil ukur before/after.
