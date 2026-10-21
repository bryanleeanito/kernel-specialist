# FRAMEWORK — Kernel Development Framework (mesin Kali, OpenCode #2)

Framework kerja kernel untuk **AI Agent / OpenCode** di Kali. Tujuannya:
agent bisa bekerja **leluasa** (bisa build, patch, tuning, driver) tapi **tidak bisa
merusak** dual-boot Windows + kernel stock.

Prinsip: **agent boleh optimist, guardrail boleh skeptis.**

## MODE RINGAN (default sejak 21 Okt 2026)

Keputusan user: **build kernel penuh di-drop** (1,5–2 jam + 5,6 GB + 4.020 modul →
overkill untuk laptop 6C/12T). Yang tetap: framework, plugin, tool, agent, skill,
mesh, dan guardrail.

Artinya framework dipakai dalam **3 mode**, urut dari yang paling murah:

| Mode | Yang dikerjakan | Biaya | Layer aktif |
|---|---|---|---|
| **M1 — Read & Debug** (default) | pahami kernel running: config, modul, crash/oops, log, bottleneck | **0 build**, detik | L0, L1, L7 |
| **M2 — Tuning runtime** | optimasi **tanpa rebuild**: `sysctl`, scheduler, BBR/FQ, governor CPU, I/O scheduler, page cache, cgroup | **0 build**, menit | L0, L1, L7, L8 (versi runtime) |
| **M3 — Driver / modul OOT** | tulis modul `.ko` sendiri (1 file C + Makefile) → build **detik**, pasang, uji | ~menit, <50 MB | L0–L4, L7 (tanpa L5/L6) |
| **M4 — Build kernel penuh** *(opsional, perlu persetujuan)* | kernel custom sungguhan | 1,5–2 jam · 5,6 GB · 4.020 modul | semua L0–L8 |

> **M3 (modul OOT) adalah "kernel development" yang murah** — ini jalur yang
> realistis kalau mau ngoprek kernel tanpa build 2 jam. Contoh: modul eBPF/char
> untuk tracing syscall, modul untuk skip flag (rootkit-style, hanya di lab),
> driver untuk perangkat yang belum didukung.
> Kalau M4 nanti dijalankan: **wajib `localmodconfig`** (hanya modul hardware
> aktif) → turun ke ~15–20 mnt & ±1–2 GB, dan kunci daftar modul wajib
> (wifi/GPU/NVMe/BT/audio/touchpad).

```
L0 CONTEXT ──► L1 INTENT ──► L2 PLAN ──► L3 BUILD ──► L4 VERIFY
                                                      │
                              ┌───────────────────────┘
                              ▼
                   L5 STAGE ──► L6 BOOT ──► L7 OBSERVE ──► L8 TUNE
                              (izin)                    (1 var/iterasi)
```

| Layer | M1 | M2 | M3 | M4 |
|---|:-:|:-:|:-:|:-:|
| L0 CONTEXT | ✅ | ✅ | ✅ | ✅ |
| L1 INTENT | ✅ | ✅ | ✅ | ✅ |
| L2 PLAN (fragment) | ➖ | ➖ | ➖ | ✅ |
| L3 BUILD | ➖ | ➖ | ✅ (modul) | ✅ |
| L4 VERIFY | ➖ | ➖ | ✅ | ✅ |
| L5 STAGE | ➖ | ➖ | ➖ | ✅ |
| L6 BOOT | ➖ | ➖ | ➖ | ✅ |
| L7 OBSERVE | ✅ | ✅ | ✅ | ✅ |
| L8 TUNE | runtime | runtime | ➖ | ✅ |
| Guardrail | ✅ | ✅ | ✅ | ✅ |

---

## Playbook per mode (siap pakai)

### M1 — Read & Debug (default, tanpa build)

| Task | Tool | Output |
|---|---|---|
| Pahami state kernel | `kernel_status` | kernel running, toolchain, SB, config kritikal |
| "Kenapa kernel crash?" | `kernel_crashlog` → `oops-analyst` | klasifikasi + root cause + fix + verifikasi |
| Modul mana yang dipakai? | `lsmod`, `/sys/module`, `kernel_module_inspect` | peta modul aktif |
| Opsi apa yang aktif? | `grep CONFIG_ /boot/config-$(uname -r)` | konfigurasi efektif |
| Bottleneck I/O? | `iostat -x 1 3`, `vmstat 1 3`, `iostat` | antrian + throughput |
| Syscall lambat? | `strace -c`, `bpftrace` (kalau ada), `/proc/schedstat` | hot path |
| Interrupt/Timer? | `/proc/interrupts`, `/proc/timer_list` |-IRQ-No | sumber interrupt |
| Memori? | `/proc/meminfo`, `slabtop -s`, `smaps_rollup` | anon/file/slab |
| Thermal/throttling? | `sensors`, `/sys/class/thermal`, `turbostat` | throttleReason |

### M2 — Tuning runtime (tanpa rebuild)

Semua di `/etc/sysctl.d/99-kernel-lab.conf` (efektif setelah reboot) atau
`sysctl -w` (langsung, hilang setelah reboot):

```sh
# I/O + jaringan (stock Kali sudah punya BBR & FQ sebagai modul → aktifkan)
sysctl -w net.ipv4.tcp_congestion_control=bbr
sysctl -w net.core.default_qdisc=fq
sysctl -w net.core.rmem_max=16777216
sysctl -w net.core.wmem_max=16777216
sysctl -w fs.file-max=2097152

# scheduler CPU (hemat daya vs responsif — laptop)
sysctl -w kernel.sched_latency_ns=1000000      # preemption latency
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor   # powersave/performance

# I/O scheduler (NVMe → none, HDD → mq-deadline/bfq)
cat /sys/block/nvme0n1/queue/scheduler
# page cache
sysctl -w vm.vfs_cache_pressure=50
sysctl -w vm.swappiness=1
```
Aturan: **1 variabel per iterasi** → ukur before/after (`iostat`, `curl -w`, `hyperfine`).
Semua perubahan **reversible** (kembalikan nilai awal) — catat di `MEMORY-KERNEL.md`.

### M3 — Driver / modul out-of-tree (murah, realistis)

```sh
mkdir -p ~/kernel-lab/modul && cd ~/kernel-lab/modul
# Makefile
cat > Makefile <<'EOF'
obj-m := namamod.o
KDIR ?= /lib/modules/$(shell uname -r)/build
all: ; $(MAKE) -C $(KDIR) M=$(PWD) modules
clean: ; $(MAKE) -C $(KDIR) M=$(PWD) clean
EOF
# namamod.c — minimal: license, author, description, version, init/exit
make
modinfo namamod.ko            # vermicus harus == uname -r
insmod namamod.ko && dmesg | tail -20
rmmod namamod
```
- `KDIR` harus menunjuk tree versi **sama persis** → di mesin ini:
  `/lib/modules/$(uname -r)/build` (symlink headers) — **tanpa** perlu source tree penuh.
- Kalau headers tidak ada: `apt install linux-headers-$(uname -r)` (ringan, ~100 MB).
- Verifikasi wajib: `vermagic` cocok, tidak ada symbol undefined, `dmesg` bersih.

### M4 — Build kernel penuh (opsional, perlu persetujuan + waktu)

Syarat: (1) `localmodconfig` (bukan config penuh), (2) daftar modul wajib dikunci,
(3) `LOCALVERSION` berbeda, (4) pre-flight + staging install. Detail di
`install-kernel.sh` (default dry-run).

---



## L0 — CONTEXT (otomatis, tanpa biaya token besar)

**Sumber**: plugin `kernel-lab` → hook `ctx.session.hook("context")` menyisipkan
fakta state kernel ke system prompt tiap request (cache 60 detik).

Isi: kernel running · source tree (versi + git) · build artifacts · Secure Boot ·
opsi kritis config (RUST/BTF/MODULE_SIG) · aturan main.

**Output**: agent selalu tahu "dunia"-nya tanpa harus menebak.
**Gate**: tidak ada. **Failure mode**: data basi → agent pakai tool `kernel_status`
untuk refresh (tool membaca langsung dari sistem).

---

## L1 — INTENT (routing)

**Sumber**: command `/kstatus` `/kbuild` `/kconfig` `/koops` `/kmodule` `/kperf`
+ agent `kernel` (primary, default) dan subagent `kernel-reviewer`,
`oops-analyst`, `driver-dev`.

**Gate**: task di luar ranah kernel → agent/kernel diarahkan ke track `kali-offensive`
(skill terpisah), bukan dipaksa Stay di kernel.
**Failure mode**: prompt ambigu → agent boleh bertanya, tapi <= 1 pertanyaan
(aturan "jangan banyak tanya" platform).

---

## L2 — PLAN (satu unit perubahan = satu fragment)

**Aturan**: perubahan config **tidak pernah** mengedit `.config` langsung.
Semua perubahan = file fragment di `/root/kernel-lab/config/fragments/<nama>.conf`
(satu opsi per baris). Ini yang membuat perubahan *reviewable*, *revertible*, dan
*bisa dibandingkan antar-build*.

**Tool**: `kernel_config_check` (validasi symbol vs tree + baseline + risiko).
**Gate (wajib sebelum build)**:
1. Semua symbol di fragment dikenal tree (tidak ada typo).
2. Baseline boot utuh: `CONFIG_64BIT`, `CONFIG_MODULES`, `CONFIG_BLK_DEV_INITRD`,
   `CONFIG_SYSFS`, `CONFIG_PROC_FS`, `CONFIG_FHANDLE`, `CONFIG_INOTIFY_USER`.
3. Prasyarat terpasang: `rustc` (kalau `CONFIG_RUST=y`), `pahole` (kalau BTF=y),
   `bison`, `bc`, `flex`, `libelf-dev`, `libssl-dev`.
4. Tidak ada kombinasi yang saling bertentangan (mis. `MODULE_SIG_FORCE=y` + modul unsigned).

**Failure mode**: fragment salah → `config_check` gagal → build **tidak** dijalankan.
**Tuning**: satu variabel per iterasi (L8).

---

## L3 — BUILD (out-of-tree, reproducible, ter-log)

**Perintah**:
```sh
make O=/root/kernel-lab/build/linux-7.1.5 -j12 CCACHE_ENABLE=1 bzImage modules
```
**Aturan**:
- **Selalu** `O=` (out-of-tree). Source tree tidak pernah jadi tempat output.
- `-j$(nproc)` (12 core, RAM 14G → aman; turunkan ke -j6 bila OOM).
- Log di `/root/kernel-lab/logs/kbuild-<timestamp>.log` (tool `kernel_build` sudah menulis log).
- Kalau toolchain bermasalah → **ganti pola**, jangan ulangi build yang sama
  (aturan platform "pola-kikir").

**Failure mode**: build gagal → tampilkan **error pertama** (bukan ringkasan),
dan diagnosis (toolchain vs config vs patch).

---

## L4 — VERIFY (bukti, bukan klaim)

**Wajib** sebelum menyatakan "berhasil":
| Artefak | Cek |
|---|---|
| `bzImage` | ada, ukuran wajar (~10–20 MB), timestamp terbaru |
| `vmlinux` | ada (symbol utuh) |
| `System.map` | ada |
| `Module.symvers` | ada (dipakai cek symbol modul) |
| `.ko` | jumlahnya > 0 bila target `modules` |
| config | diff base vs hasil (opsi yang benar-benar berubah) |

**Aturan platform**: **dilarang false positive** — "build sukses" tanpa output
`make` rc=0 + daftar artefak = bohong. Tool `kernel_build` sudah mengembalikan
summary berbasis file nyata.

---

## L5 — STAGE (install ke staging, bukan ke sistem)

```sh
make O=... modules_install INSTALL_MOD_PATH=/root/kernel-lab/stage
```
Semua modul + image dicopies ke staging. Tidak menyentuh `/boot`/`/lib/modules`.
**Gate**: L4 harus hijau.

---

## L6 — BOOT (berbahaya → 3 lapis proteksi)

Tiga lapis, semua harus dilewati:

1. **Permission config** (`~/.config/opencode/opencode.json`):
   `make install`, `modules_install`, `update-initramfs`, `mkinitramfs`,
   `update-grub`, `depmod`, `insmod`, `modprobe`, `rmmod` → effect **ask**.
2. **Hard guard plugin** (`kernel-lab` → `ctx.permission.hook("evaluate")`):
   `rm -rf /boot*`, `rm -rf /lib/modules*`, `mkfs*`, `wipefs*`, `sgdisk --zap-all`,
   `dd … of=/dev/*`, `> /dev/sd*`, `chmod -R 777 /`, `chown -R … /` → effect **deny**
   (ditolak + alasan, tidak bisa di-bypass agent).
   Plus `git push`, `apt-get install`, `curl … | sh` → **ask**.
3. **Pre-flight tool** (`kernel_preflight`) → checklist blocker:
   Secure Boot state · ruang `/boot` · kernel stock tersedia · initramfs · os-prober.

Plus **prompt hook**: kalau prompt user mengandung install/boot/grub/initramfs,
plugin menyisipkan pengingat pre-flight ke prompt.

**Rollback wajib**: booting kernel stock via GRUB → Advanced options, lalu
`apt remove linux-image-<versi-custom>`. Rencanakan sebelum install, bukan setelah boot gagal.

**Testing guardrail**: `node tests/test_guardrail.mjs` (32 assertion) — wajib hijau
setiap kali guardrail diubah.

---

## L7 — OBSERVE (dari sistem nyata)

- Crash: tool `kernel_crashlog` → kumpulkan `dmesg -T` + `journalctl -k -b` +
  `journalctl -k -b -1` → subagent `oops-analyst` (klasifikasi, `RIP`/`Code:`, root cause).
- Performa: `/proc/stat`, `iostat`, `vmstat`, `perf`, `sysctl` — **sebelum vs sesudah**.
- Regresi boot: `journalctl -k -b -1` + `dmesg` setelah reboot.

**Failure mode**: log tidak ada → jawab "data crash tidak tersedia di boot ini",
jangan mengarang Call Trace.

---

## L8 — TUNE (satu variabel per iterasi)

Proses: **ukur baseline** → ubah 1 opsi → build → **ukur ulang** → putuskan
(lanjut / revert). Revert = hapus fragment, build ulang (ccache mempercepat).

Kandidat umum (lihat `/kperf` untuk versi tree ini): scheduler/EEVDF · `PREEMPT_*` ·
`HZ_*` + `NO_HZ_IDLE` · `TCP_CONG_BBR` + `NET_SCH_FQ` · `ZSWAP`/`ZRAM` ·
`BTRFS_ZSTD` · `XFS_RT` · `LTO` · mitigasi Spectre (biaya nyata, harus disebut).

**Gate**: tidak ada tuning yang dipertahankan tanpa angka before/after.

---

## Lapisan keamanan (ringkas)

| Lapis | Mekanisme | Where |
|---|---|---|
| Konfigurasi | `permissions` rules | `~/.config/opencode/opencode.json` |
| Kode | permission hook (deny/ask) | `~/.config/opencode/plugins/kernel-lab.js` |
| Prosedur | pre-flight checklist | tool `kernel_preflight` |
| Persetujuan | prompt hook + izin user | plugin + aturan platform |
| Pengujian | unit test guardrail | `tests/test_guardrail.mjs` |
| Bukti | artefak & log | tool `kernel_build` + `tests/run_all.py` |

---

## Struktur repo

```
kernel-specialist/
├── opencode/          track OpenCode (agent, command, skill, instruksi)
│   └── plugins/       kernel-lab.js, v1-compat.js, dev-journal.js, shell-env-dev.js
├── tools/kernel/      4 tool kit (env_report, config_check, module_inspect, kbuild)
├── tests/             run_all.py (gate) + test_guardrail.mjs
├── FRAMEWORK.md       dokumen ini
└── install.sh         pasang track ke ~/.config/opencode (backup otomatis)
```

Area kerja runtime (bukan repo): `/root/kernel-lab/{src,build,logs,config,stage}`.
