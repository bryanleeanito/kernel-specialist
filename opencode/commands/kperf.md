---
description: Analisis performa & tuning kernel — scheduler, preempt, HZ, BBR, mitigasi, I/O
agent: kernel
---

Analisis opsi tuning kernel untuk mesin ini. Permintaan: $ARGUMENTS

Data yang wajib dikumpulkan dulu (fakta, bukan asumsi):
1. Profil workload saat ini:
   - `nproc`, `lscpu | egrep 'Model name|CPU\(s\)|MHz'`, `free -h`
   - `uname -r`, `cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor` (kalau ada)
   - Beban I/O: `iostat -x 1 3` / `vmstat 1 3` (kalau ada paketnya)
   - Scheduler aktif: `sysctl kernel.sched_*`, `cat /sys/block/*/queue/scheduler`
   - TCP: `sysctl net.ipv4.tcp_congestion_control`, `net.core.default_qdisc`
   - preempt/HZ aktual: `/proc/config.gz` (kalau ada) atau config build
2. Opsi kandidat (hanya yang relevan & benar untuk versi tree ini):
   - Scheduler: `CONFIG_SCHED_*` (EEVDF vs BFS/MuQSS — BFS/MuQSS **tidak** upstream),
     `CONFIG_PREEMPT*`, `CONFIG_HZ_*` + `CONFIG_NO_HZ_IDLE`/`_FULL`,
     `CONFIG_HIGH_RES_TIMERS`.
   - Networking: `CONFIG_TCP_CONG_BBR` + `CONFIG_TCP_CONG_ADVANCED`, `CONFIG_NET_SCH_FQ`,
     `CONFIG_HZ` terkait, `CONFIG_RPS`/`CONFIG_RFS_ACCEL`, `CONFIG_XDP_SOCKETS`.
   - I/O/memory: `CONFIG_ZSWAP`, `CONFIG_ZRAM`, `CONFIG_TRANSPARENT_HUGEPAGE`,
     `CONFIG_COMPACTION`, `CONFIG_MTHP`.
   - Filesystem: `CONFIG_BTRFS_FS` + compression (`CONFIG_BTRFS_ZSTD`),
     `CONFIG_XFS_FS` + `CONFIG_XFS_RT` (realtime group scheduling).
   - Mitigasi Spectre/Meltdown: `CONFIG_RETPOLINE`, `CONFIG_CPU_IBPB_ENTRY`/
     `CONFIG_CPU_IBPB` — **biaya performa nyata**, tradeoff harus disebut.
   - Build flags: `CONFIG_LTO_*`, `CONFIG_CC_OPTIMIZE_FOR_PERFORMANCE`,
     `CONFIG_GCC_PLUGINS` (KASAN, UBSAN), `CONFIG_DEBUG_INFO_BTF` (overhead build).
   - Hardware: `CONFIG_AMD_PMC`, `CONFIG_AMD_IOMMU`, `CONFIG_X86_PREDICTION` (retpoline),
     `CONFIG_PAGE_TABLE_ISOLATION` (overhead ~2-5%).
3. Untuk tiap kandidat: **manfaat**, **biaya/risk**, **cara ukur sebelum & sesudah**
   (perintah + metrik), **rollback**.
4. Rekomendasi harus **bertahap** (satu variabel per build) supaya bisa diukur —
   jangan throw semua opsi sekaligus.
5. Jangan mengubah `/boot`/config sistem tanpa izin; usulkan fragment dan lokasi build dulu.
   Selalu sediakan cara rollback (fragment lama / config stock).

Ringkas dalam tabel: opsi | nilai sekarang | nilai usulan | alasan | cara ukur | risiko.
