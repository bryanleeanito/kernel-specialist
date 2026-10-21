---
name: Kernel Lab
description: Alur kerja kernel di mesin Kali — tuning runtime tanpa rebuild, analisis crash/oops, driver-modul out-of-tree, dan (opsional) build kernel custom. Gunakan saat mengerjakan tuning kernel, debugging boot, atau membuat modul .ko.
metadata:
  opencode/autoinvoke: true
---

# Kernel Lab — SOP mesin Kali (OpenCode #2)

Skill ini berisi **prosedur kerja** track kernel. Load saat mulai mengerjakan
tuning kernel, debugging crash, atau membuat modul/driver di mesin ini.

> **Mode default sejak 21 Okt 2026: M1–M3 (TANPA build kernel penuh).**
> Build kernel custom penuh **dibatalkan** (1,5–2 jam + 5,6 GB + 4.020 modul →
> overkill) dan source tree **sudah dihapus** (hemat 1,9 GB).
> Pilih mode sesuai task:
> - **M1 Read & Debug** — pahami kernel running, analisis crash/oops, peta modul.
> - **M2 Tuning runtime** — optimasi **tanpa rebuild** (sysctl/scheduler/governor/BBR).
> - **M3 Driver/modul OOT** — bikin modul `.ko` sendiri (build **detik**).
> - **M4 Build kernel penuh** — **hanya atas permintaan eksplisit** + izin
>   (biaya ±1,5–2 jam & ±5,6 GB; wajib `localmodconfig`).
> Detail: `references/framework.md` (layer L0–L8 + playbook per mode).

## Peta path (fakta)

| Kebutuhan | Path |
|---|---|
| Source tree | **TIDAK ADA** (dihapus 21 Okt 2026) — tool butuh tree akan bilang tidak ada |
| Header modul OOT | `/lib/modules/$(uname -r)/build` (ringan, untuk M3) |
| Base config kernel | `/boot/config-$(uname -r)` |
| Fragment config | `/root/kernel-lab/config/fragments/*.conf` (`perf.conf`, `debug.conf`, `localversion.conf` — tervalidasi) |
| Tool kit | `/root/kernel-lab/kernel-specialist/tools/kernel/*/` |
| Repo kit + config | `/root/kernel-lab/kernel-specialist/` |
| Sysctl tuning | `/etc/sysctl.d/99-kernel-lab.conf` (buat saat M2) |

## M2 — Tuning runtime (paling sering dipakai, 0 build)

```sh
# Basis: kernel stock Kali sudah punya BBR, FQ, ZSWAP, XFS_RT, KFENCE → tinggal aktifkan
sysctl -w net.ipv4.tcp_congestion_control=bbr
sysctl -w net.core.default_qdisc=fq
sysctl -w net.core.rmem_max=16777216
sysctl -w net.core.wmem_max=16777216
sysctl -w fs.file-max=2097152
sysctl -w vm.vfs_cache_pressure=50
sysctl -w vm.swappiness=1
# CPU governor (laptop): powersave (hemat) / performance (responsif)
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
# I/O scheduler per device
cat /sys/block/nvme0n1/queue/scheduler
```

**Aturan**: ukur baseline dulu (iostat/vmstat/timing), ubah **1** variabel,
ukur ulang, catat nilai awal untuk rollback, tulis hasilnya ke `MEMORY-KERNEL.md`.
Simpan permanen di `/etc/sysctl.d/99-kernel-lab.conf` (efektif setelah reboot).

## M3 — Modul out-of-tree (build detik)

```sh
mkdir -p ~/kernel-lab/modul && cd ~/kernel-lab/modul
cat > Makefile <<'EOF'
obj-m := namamod.o
KDIR ?= /lib/modules/$(shell uname -r)/build
all: ; $(MAKE) -C $(KDIR) M=$(PWD) modules
clean: ; $(MAKE) -C $(KDIR) M=$(PWD) clean
EOF
# namamod.c: MODULE_LICENSE/AUTHOR/DESCRIPTION/VERSION + module_init/exit
make && modinfo namamod.ko   # vermagic HARUS == uname -r
insmod namamod.ko && dmesg | tail -20 && rmmod namamod
```

- Kalau `/lib/modules/$(uname -r)/build` tidak ada → `apt install linux-headers-$(uname -r)`.
- Cek symbol undefined: `nm -u namamod.ko` vs `Module.symvers` kernel running.
- Tool: `kernel_module_inspect` / `tools/kernel/module_inspect/module_inspect.py --module x.ko`.

## M1 — Read & Debug

```sh
uname -r
grep -E '^CONFIG_(PREEMPT|HZ_|MODULES|RUST|DEBUG_INFO_BTF|MODULE_SIG)' /boot/config-$(uname -r)
lsmod; ls /sys/module | head -40
cat /proc/cmdline; head -20 /proc/interrupts
iostat -x 1 3; vmstat 1 3
```

Crash → tool `kernel_crashlog` → subagent `oops-analyst` (klasifikasi → root cause → fix → verifikasi).

## M4 — Build kernel penuh (opsional; butuh izin + waktu)

Lihat `references/framework.md` §M4 dan `install-kernel.sh` (default dry-run).
WAJIB: `localmodconfig` (bukan config penuh) + `LOCALVERSION` berbeda
(`localversion.conf`) + pre-flight + staging install.
Kalau butuh source tree lagi: `deb-src` Kali + `apt-get source linux` (lihat §M4).

## Jebakan khas mesin ini

1. **Secure Boot NONAKTIF** (`SecureBoot=0`, `SetupMode=1`) → kernel custom boleh boot
   tanpa MOK. (`mokutil` tidak ada di repo Kali → baca `/sys/firmware/efi/efivars/SecureBoot-*`,
   byte ke-5; file efivarfs **tidak bisa di-seek** → baca utuh.)
2. **`/boot` bukan partisi terpisah** → ikut `/` (102G, ~62G free). Partisi EFI 976M
   di `/boot/efi` (tempat boot loader). Aman untuk 2+ kernel.
3. **`GRUB_CMDLINE_LINUX_DEFAULT="quiet"`** → log boot tidak kelihatan; **hapus `quiet`**
   sementara saat debug, lalu kembalikan.
4. **Build kernel penuh = mahal**: config stock = 4.020 modul → ~12.000 objek →
   1,5–2 jam & 5,6 GB. Ganti 1 opsi config = rebuild ~90% objek (ccache hit anjlok ~5%).
   → pakai `localmodconfig` kalau memang perlu.
5. **`HOSTCC="ccache gcc"`** bikin build gagal (`-Clinker=$(HOSTCC)` → rustc salah parse).
   Ccache hanya lewat `CC=ccache gcc`.
6. **`CONFIG_RUST=y`** butuh rustc versi persis (1.95.0) + `bindgen` + paket `rust-src`.
7. **Kernel 7.1.5 Kconfig berubah**: simbol `menuconfig` (HUGETLBFS, TCP_CONG_ADVANCED,
   KFENCE, TRANSPARENT_HUGEPAGE, GCC_PLUGINS), HZ maksimum `HZ_1000`, `SCHEDSTATS`
   (bukan SCHED_DEBUG), `DEBUG_VM_MAPLE_TREE`/`DEBUG_VM_RB` (bukan PMAP/PML),
   Btrfs tanpa `BTRFS_ZSTD`.

## Aftercare (wajib)

- Update `MEMORY-KERNEL.md` + `TRACKER-KERNEL.md` (aturan disiplin platform).
- Bersihkan artefak eksperimen yang tidak dipakai (out-of-tree dir lama, log > 7 hari).
- Kalau tuning M2: catat nilai awal (rollback) + hasil before/after.
