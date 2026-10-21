# MEMORY-KERNEL (KALI) — Track Kernel Ops & Dev (OpenCode #2)

**Track:** kernel di mesin Kali. **Baca awal sesi; update akhir sesi.**
> **Mode default: M1–M3 (TANPA build kernel penuh).** Build kernel custom penuh
> dibatalkan user (21 Okt 2026): ±1,5–2 jam + 5,6 GB + 4.020 modul → overkill.
> Source tree (1,9 GB) + build dir (5,6 GB) + ccache (1,4 GB) **sudah dihapus** →
> `/root/kernel-lab` sekarang **1,3 MB**, disk bebas 64 GB.
> Track = (M1) baca & debug kernel running · (M2) tuning runtime tanpa rebuild ·
> (M3) driver/modul out-of-tree · (M4) build kernel penuh = opsional, atas izin.

Aturan disiplin (lihat `AGENTS.md` §Disiplin mutlak): hasil nyata & terverifikasi
(dilarang false positive), **efisien tapi tepat**, **tidak gengsi minta ke user kalau
butuh tool/akses/token**, **wajib update `MEMORY-KERNEL.md` + `TRACKER-KERNEL.md`**
setiap selesai eksekusi, **bersihkan sisa eksperimen**, dan saat stuck → baca lagi
file ini + log → ubah pola → ulangi sampai ada hasil.

---

## 0. Ringkasan status (21 Okt 2026)

| Item | Status |
|---|---|
| Toolchain kernel | ✅ terpasang (rustc 1.95.0, lld 21.1.8, pahole 1.32, bison 3.8.2, bindgen 0.72.1, rust-src) |
| Source tree | ❌ **dihapus** (hemat 1,9 GB) — obtain ulang: `deb-src` Kali + `apt-get source linux` |
| Build dir / ccache | ❌ dihapus (hemat 7 GB) |
| Kit 4 tool + tes | ✅ 66/66 assertion |
| Track OpenCode (agent/command/skill) | ✅ terpasang |
| 4 plugin V2 | ✅ active (kernel-lab, v1-compat, dev-journal, shell-env-dev) |
| Framework L0–L8 + mode M1–M4 | ✅ `FRAMEWORK.md` |
| Integrasi mesh | ✅ `kali-kernel` terdaftar, 4 kit `kernel-*` |
| Tuning runtime (M2) | ⏳ belum ada tuning yang dicatat → section 8 |

## 1. Facts mesin (verified 2026-10-21)

| item | nilai |
|---|---|
| distro | Kali GNU/Linux Rolling 2026.3 (x86_64), hostname `kali`, sesi ini root |
| kernel running | `7.1.5+kali-amd64` (build 2026-07-29) |
| kernel sebelumnya | `6.19.14+kali-amd64` (masih ada di /lib/modules) |
| CPU / RAM | 12 core / 14 GiB (swap 5.7G) |
| root fs | 102G, sisa ~67G |
| `/boot` | **bukan partisi terpisah** — ikut `/` (nvme0n1p6, 102G, ~62G free). EFI partisi sendiri `/dev/nvme0n1p5` (976M) di `/boot/efi` (975M free) |
| IP LAN | **DHCP — berubah antara sekolah & rumah.** Terakhir: `15.15.0.201/22` (wlan0, gateway 15.15.0.1, DNS 15.15.0.1 + 203.142.82.222). Sumber IP live untuk mesh = `state/presence/kali-kernel.json` |
| **Secure Boot** | **NONAKTIF** (efivars `SecureBoot=0`, `SetupMode=1`) → kernel custom **boleh boot tanpa MOK**. `mokutil` tidak ada di repo Kali → deteksi via `/sys/firmware/efi/efivars/` (efivarfs tidak seekable → baca full, byte ke-5) |
| OpenCode | v2.1.1, background service di 127.0.0.1:49375 (Basic auth) |

## 2. Toolchain kernel (sudah terpasang 2026-10-21)

`build-essential bc bison flex libssl-dev libelf-dev dwarves ccache lld rustc
libncurses-dev python3-dev xz-utils zstd rsync kmod cpio git jq`

| tool | versi | wajib karena |
|---|---|---|
| gcc | 13/14 (Debian) | build |
| bison | 3.8.2 | parser Kconfig |
| pahole (dwarves) | 1.32 | `CONFIG_DEBUG_INFO_BTF=y` |
| rustc | **1.95.0** | `CONFIG_RUST=y` — cocok `CONFIG_RUSTC_VERSION_TEXT` |
| lld | 21.1.8 | cocok `CONFIG_RUSTC_LLVM_VERSION=210108` |
| ccache | terpasang | iterasi build cepat |

> Kalau Kali update kernel → `CONFIG_RUSTC_VERSION_TEXT` ikut berubah.
> **Cek ulang tiap build** (`grep CONFIG_RUSTC_VERSION /boot/config-$(uname -r)`).

## 3. Layout (sumber kebenaran)

| Kebutuhan | Path |
|---|---|
| source tree | **TIDAK ADA** (dihapus 21 Okt 2026, hemat 1,9 GB) — obtain ulang: `deb-src` Kali + `apt-get source linux` |
| build out-of-tree | **TIDAK ADA** (dihapus, hemat 5,6 GB) — dibuat ulang oleh `kbuild.py` |
| header modul OOT (M3) | `/lib/modules/$(uname -r)/build` (ringan) |
| base config kernel running | `/boot/config-$(uname -r)` |
| fragment | `/root/kernel-lab/config/fragments/*.conf` |
| log build | `/root/kernel-lab/logs/kbuild-*.log` |
| kit + track OpenCode | `/root/kernel-lab/kernel-specialist/` |
| config OpenCode aktif | `/root/.config/opencode/` |
| repo kit (workspace) | `07-SISTEM/kernel-specialist/` |

## 4. Track OpenCode + PLUGIN (terpasang 2026-10-21)

- Agent: `kernel` (primary, **default_agent**), `kernel-reviewer`, `oops-analyst`, `driver-dev`.
- Command: `/kbuild` `/kconfig` `/koops` `/kmodule` `/kperf` `/kstatus`.
- Skill: `kernel-lab` (SOP: source tree, config baseline, build, install aman, jebakan dual-boot).
- Instruksi: `KERNEL-AGENTS.md` (global), `MEMORY-KERNEL.md` + `TRACKER-KERNEL.md`.
- **Plugin lokal (V2) di `~/.config/opencode/plugins/`**:
  | plugin | fungsi | status |
  |---|---|---|
  | `kernel-lab.js` | 6 tool kernel native + **guardrail deny/ask** + context injection + prompt safety | active |
  | `v1-compat.js` | muat plugin V1 lewat adapter (goal/workaholic/notify/autotitle/token-tracker) | active |
  | `dev-journal.js` | journal tiap perintah shell (port V1→V2) | active — **terbukti jalan** (journal terisi) |
  | `shell-env-dev.js` | env shell UTF-8 + path journal (port V1→V2) | active |
| **`kali-ops.js`** | **co-pilot sistem**: 8 tool native namespace `kali` (status mesin, cek tool, jaringan, service, firewall, disk, paket apt, ubah paket dgn gate) + guardrail sistem deny/ask + context injection sistem | active — **52/52 assertion** |
- Permission root: `rm -rf /boot*`, `mkfs*`, `wipefs*`, `dd *of=/dev/*` = **deny**;
  `make install`, `modules_install`, `update-initramfs`, `update-grub`, `insmod`,
  `modprobe`, `rmmod`, `depmod`, `apt-get install`, `git push` = **ask**.
- **Guardrail plugin (lapis kedua, di atas permission config)**:
  DENY: `rm -rf /boot*`, `rm -rf /lib/modules*`, `mkfs*`, `wipefs*`, `sgdisk --zap-all`,
  `dd … of=/dev/*`, `> /dev/sd*`, `chmod -R 777 /`, `chown -R … /`.
  ASK: `make install`, `modules_install`, `update-initramfs`, `mkinitramfs`, `update-grub`,
  `depmod`, `insmod/modprobe/rmmod`, `git push`, `apt-get install`, `curl … | sh`.
  **Teruji**: `node tests/test_guardrail.mjs` → 32/32 assertion lulus.
- Goal-plugin (V1) hidup lagi lewat `v1-compat` → command `/goal`, agent `goal` + `goal-verify` terdaftar.

## 5. Tool kit (4 tool, gate tes 66/66 lulus)

| tool | fungsi |
|---|---|
| `tools/kernel/env_report/env_report.py` | snapshot env (kernel, toolchain, SB, source, build) |
| `tools/kernel/config_check/config_check.py` | validasi config/fragment vs tree + baseline + risiko |
| `tools/kernel/module_inspect/module_inspect.py` | `.ko`: vermagic, signature, symbol, dependensi |
| `tools/kernel/kbuild/kbuild.py` | wrapper build (fragment→olddefconfig→make→verifikasi), staging-only |

Gate: `python3 /root/kernel-lab/kernel-specialist/tests/run_all.py` → exit 0
(5 berkas tes: 4 tool + guardrail plugin, 66/66 assertion).

**Framework** (lapisan L0–L8 + 3 lapis proteksi) → `FRAMEWORK.md` di repo kit.

## 5b. Integrasi mesh (2026-10-21)

- Mesin ini terdaftar di mesh sebagai `kali-kernel` (role `kernel`, IP 192.168.14.99,
  capability `kernel,kbuild,driver,perf,debug`).
- Kategori kit baru di `mesh_integrator.py`: `kernel-env-report`, `kernel-config-check`,
  `kernel-module-inspect`, `kernel-kbuild` (total kit mesh 30).
- **Terbukti**: `mesh_integrator.py run-kit --kit kernel-env-report` → report normal.
- Repo kit di workspace: `07-SISTEM/kernel-specialist/` (git init, commit lokal — belum push).
- Mesh repo: conflict marker ter-commit sudah diperbaiki + tes suite 18/18 lulus.

## 6. Jebakan (sudah ketemu — jangan ulangi)

1. **Merge conflict di mesh**: `07-SISTEM/opencode-mesh-v2/README.md` dan
   `scripts/mesh_integrator.py` punya marker `<<<<<<<` yang **ter-commit** →
   `mesh_integrator.py` rusak (SyntaxError). Penyebab: 2 mesin push tanpa
   pull-before-push. Perbaikan: `scripts/fix_state_conflict.py` (khusus JSON state).
2. **`apt-get source` butuh `deb-src`** → file `/etc/apt/sources.list.d/kali-src.sources`.
3. **`CONFIG_RUST=y`** → rustc harus versi persis (1.95.0 sekarang).
4. **`CONFIG_MODULE_SIG=y`** → modul custom perlu signed / `MODULE_SIG_FORCE=n`.
5. **Secure Boot** → custom kernel butuh MOK enrolled; `mokutil --sb-state` (paket `mok-util`).
6. **`make install` bisa menimpa `/boot`** → dual boot bisa rusak. Staging dulu.
7. **`update-grub` + os-prober** → entri Windows bisa hilang dari GRUB.

## 7. Riwayat eksekusi

- **2026-10-21** — Setup track kernel:
  - Toolchain kernel terpasang (verifikasi versi di §2).
  - `deb-src` Kali aktif → `apt-get source linux` (source tree 7.1.5).
  - 4 tool kit dibuat + tes 34/34 lulus (gate `tests/run_all.py`).
  - Track OpenCode terpasang di `~/.config/opencode` (4 agent, 6 command, 1 skill).
  - Track KALI (offensive) ikut terpasang: AGENTS/MEMORY/TRACKER + 3 skill + 32 skill eksternal + 2 plugin lokal.
  - `09-MIGRASI/kali/opencode.json` **berformat V1** (`permission`/`bash`/`task`/`mcp`) —
    TIDAK disalin mentah; sudah dikonversi ke V2 (`permissions`/`shell`/`subagent`/`mcp.servers`/`plugins`).
- **Next** (lihat `TRACKER-KERNEL.md`): tuning runtime M2 (ukur baseline → 1 variabel → ukur ulang),
  modul OOT M3, dan (opsional) M4 build kernel penuh dengan `localmodconfig` + izin user.

## 7b. M3 — Modul out-of-tree (SUDAH BERJALAN, 21 Okt 2026)

**Resep working (modul `kernel_lab`):** `/root/kernel-lab/modul/` (salinan di repo kit:
`examples/kernel_lab/`). Build → `make` (pakai `KDIR=/lib/modules/$(uname -r)/build`).

| Tahap | Hasil terverifikasi |
|---|---|
| `apt install linux-headers-$(uname -r)` | ✅ `linux-headers-7.1.5+kali-amd64` + symlink `build` OK |
| `make` | ✅ `kernel_lab.ko` 350.456 byte — **hitungan detik** |
| `modinfo` | vermagic `7.1.5+kali-amd64 SMP preempt mod_unload` = cocok `uname -r` |
| `insmod` | ✅ loaded, `/proc/kernel_lab` terbentuk |
| baca | `release 7.1.5+kali-amd64` · `version #1 SMP PREEMPT_DYNAMIC Kali 7.1.5-1kali1` · `nodename kali` · `uptime 22218` · `cpus_online 12` |
| module param | `echo 42 > /sys/module/kernel_lab/parameters/lab_counter` → terbaca 42 ✅ |
| `rmmod` | ✅ unloaded, `/proc/kernel_lab` hilang, tidak ada sisa |

**Cara baca API kernel 7.1 (beda dari versi lama — jangan nebak, baca header):**
| Butuh | Header 7.1.5 |
|---|---|
| release/version kernel | `struct new_utsname` + `utsname()` (bukan `struct utsname`/`uname()`) |
| uptime | `ktime_get_boottime_seconds()` (linux/timekeeping.h) |
| jumlah CPU | `num_online_cpus()` |
| proc single-buffer | `single_open(file, show, NULL)` (bukan `seq_open` + `seq_operations`) |
| daftar modul loaded | **tidak bisa** dari modul (list `modules` tidak diekspor) → hitung dari userspace (`/proc/modules`) |
| `__DATE__`/`__TIME__` | dilarang (`-Werror=date-time`) → pakai `KBUILD_BUILD_TIMESTAMP` |
| `struct module` | field list = `list` (bukan `m_list`) |

**Taint (wajar, bukan error):** `module verification failed: signature ... missing - tainting kernel`
→ modul OOT tidak signed; `CONFIG_MODULE_SIG=y` tapi `MODULE_SIG_FORCE` tidak aktif → **tetap bisa dimuat**,
hanya kernel ditandai tainted. Kalau mau signed: pakai signing key Debian.

**Tool kit (`module_inspect`) menemukan bug saat dipakai nyata & sudah diperbaiki:**
`modinfo -F vermagic /lib/modules/<rel>` → salah (modinfo butuh file .ko) → kini bandingkan
field pertama vermagic vs `uname -r`; label symbol undefined → "normal untuk modul" (error
hanya kalau symbol tidak ada di `Module.symvers`).

## 7c. M1 — Analisis crash kernel (SUDAH BERJALAN, 21 Okt 2026)

**Kasus nyata**: modul `kernel_lab` (versi buggy) memicu **Oops sungguhan** saat
menulis ke `/proc/kernel_lab`. Log lengkap: `dmesg` (blok ~51 baris).

### Ringkasan temuan (output agent `oops-analyst`, diverifikasi ulang)

| Aspek | Nilai | Dasar |
|---|---|---|
| Jenis | **page fault, protection violation (SMAP)** | `#PF: error_code(0x0001)` → P=1 (protection), W=0 (read), U=0 (supervisor) |
| Bukan | NULL deref | `CR2 = 0x557c1f7bf880` (alamat **user**, bukan ~0) |
| Bukan | UAF / race | deterministik, single-thread, tanpa free/realloc |
| Fatalitas | Oops (bukan panic) — proses `zsh` mati, **kernel tetap hidup** | `Oops: Oops: 0001 [#1]` |
| Culprit | **`lab_write+0x16/0x40 [kernel_lab]`** → `movzbl (%rsi),%edx` | `Code: ... <0f> b6 16 ...` = `movzbl (%rsi),%edx`; `RSI = 0x557c1f7bf880` = `buf` (argumen `write(2)`) |
| Root cause | `v = buf[0];` — **deref pointer user-space langsung di mode kernel** | `nm -u` → tidak ada `_copy_from_user`; PTE `80000002b2083867` → bit0 present, bit2 user → **halaman user, ditolak SMAP** |

**Pelajaran Membaca Log (inti skill `oops-analyst`):**
1. Entri bertanda **`?`** di Call Trace = **suspects**, bukan culprit (`srso_return_thunk`,
   `__handle_mm_fault`, `do_user_addr_fault` = jalur unwind normal).
2. **`RIP`** → fungsi guilty; **`Code:`** → instruksi yang fault (`<0f>` = byte fault);
   **`CR2`** → alamat yang gagal diakses; **`RSI/RDX/RDI`** → argumen syscall
   (di sini: buf/count/file*); `PTE` → apakah halaman present/user.
3. `#PF: error_code(0x0001)` + PTE present&user + SMAP aktif ⇒ **user pointer
   yang di-deref tanpa `copy_from_user()`** (bukan page-not-present).
4. `Tainted: [O]=OOT_MODULE, [E]=UNSIGNED_MODULE` → modul OOT tanpa signature
   (wajar, bukan penyebab crash).

### Bug kedua yang tersembunyi (ditemukan agent)
`v` = `int` diisi dari `buf[0]` (rentang 0–255), sedangkan trigger `v == 0xDEAD`
(57005) → **tidak mungkin true** → **GCC menghapus** blok `pr_warn` + `WARN_ON`
(bukti: `strings kernel_lab.ko | grep "dipicu manual"` kosong; `nm -u` tanpa `__warn`).
Jadi trigger latihanku **tidak pernah terealisasi**; crash terjadi sebagai efek samping.
→ Pelajaran: **verifikasi bahwa branch yang kamu tulis memang reachable** (uji trigger
bukan cuma compile).

### Fix (terverifikasi jalan)
```c
static ssize_t lab_write(struct file *file, const char __user *buf, size_t count, loff_t *ppos)
{
	u16 v = 0;                      /* u16 supaya 0xDEAD bisa tercapai */
	if (count < sizeof(v)) return -EINVAL;
	if (copy_from_user(&v, buf, sizeof(v))) return -EFAULT;
	if (v == 0xDEAD) { pr_warn("kernel_lab: dipicu manual (0x%04x)\n", v); WARN_ON(true); }
	lab_counter = v;
	return count;
}
```
- `copy_from_user()` **boleh dipakai modul OOT** (static inline → `_copy_from_user` di-EXPORT).
- `WARN_ON(true)` di x86 berbasis trap `ud2` → **tidak butuh simbol `__warn`**.
- Little-endian: agar `v == 0xDEAD`, byte yang ditulis harus `AD DE` (bukan `DE AD`).
- Uji (hasil nyata, probe terpisah): tulis 2 byte biasa → counter update, **tanpa oops**;
  tulis 1 byte → `EINVAL`; tulis `\xAD\xDE` → **WARNING muncul, kernel tetap hidup**,
  tidak ada `BUG: unable to handle page fault` baru.

### Sisa yang perlu diketahui
- Modul versi buggy **nyangkut di state "Unloading"** (`/proc/modules`: `kernel_lab 12288 -1 - Unloading`)
  → referensi bocor dari proses yang **mati di tengah oops** (fd cleanup tak selesai).
  Fungsinya sudah selesai (`/proc/kernel_lab` hilang), cuma ngikat ~12 KB RAM.
  **Bersih total setelah reboot.** Modul dengan nama sama tidak bisa di-`insmod` lagi
  (EBUSY) → pakai nama berbeda atau reboot dulu.
- Deteksi dini untuk bug similar: `CONFIG_DEBUG_VM=y`, `CONFIG_KASAN=y` (butuh kernel
  custom — **tidak menjangkau modul OOT**), `CONFIG_HARDENED_USERCOPY` (untuk
  `copy_struct_from_user`). Untuk OOT modul: satu-satunya bets = `copy_from_user()` + cek length.

## 8. Jejak tuning runtime (M2) — isi setiap pendekatan

Format: `tanggal | parameter | nilai lama → baru | cara ukur | before → after | rollback`

_(tabel ini yang jadi acuan "hasil nyata" track kernel — isi HANYA kalau ada angka ukur)_

| Tanggal | Parameter | Lama → Baru | Cara ukur | Before → After | Rollback |
|---|---|---|---|---|---|
| 2026-10-21 | `net.ipv4.tcp_congestion_control` | cubic → **bbr** | A/B bergantian 4×2 host (median connect) | debian 0,059→0,055 s · cloudflare 0,091→**0,055 s** (−40%) | `sysctl -w net.ipv4.tcp_congestion_control=cubic` |
| 2026-10-21 | `net.core.default_qdisc` | fq_codel → **fq** | ikut BBR (FQ = syarat BBR) | — (menyusul BBR) | `sysctl -w net.core.default_qdisc=fq_codel` |
| 2026-10-21 | `net.core.rmem_max` / `wmem_max` | 4 MB → **16 MB** | — (buffer, dampak nyata di link high-BDP) | perlu uji transfer file besar | `sysctl -w net.core.rmem_max=4194304` |
| 2026-10-21 | `net.ipv4.tcp_rmem` / `tcp_wmem` | max 32M/4M → **16M/16M** | — | — | `sysctl -w net.ipv4.tcp_rmem="4096 131072 33554432"` |
| 2026-10-21 | `vm.swappiness` | 60 → **10** | — | — | `sysctl -w vm.swappiness=60` |
| 2026-10-21 | `vm.vfs_cache_pressure` | 100 → **50** | — | — | `sysctl -w vm.vfs_cache_pressure=100` |

**Persistence:** `/etc/sysctl.d/99-kernel-lab.conf` (8 setelan) +
`/etc/modules-load.d/kernel-lab.conf` (`tcp_bbr`, `sch_fq`).
Rollback penuh: hapus 2 file itu + reboot (atau `sysctl -w` per baris di atas).

### Baseline mesin (21 Okt 2026, sebelum tuning)
- Disk: write 1,7 GB/s · read-cache 7,1 GB/s (NVMe sehat)
- I/O scheduler: `[none] mq-deadline` (NVMe → `none` sudah optimal)
- CPU governor: `schedutil` (hemat baterai — **jangan** diubah ke `performance` di laptop)
- `tcp_bbr.ko` & `sch_fq.ko` **ada** di `/lib/modules` tapi belum dimuat → BBR tidak aktif
  (cc default cubic). Fix: `modprobe tcp_bbr` + `modprobe sch_fq`.

### CATATAN jujur soal pengukuran
- Jaringan sekolah = **sumber noise utama** (variance TTFB 0,15–0,63 s antar request).
  Angka A/B di atas diambil dari **median 4 ronde bergantian** supaya tren terlihat.
- **TTFB tidak bisa diklaim membaik** (noise > efek). Yang konsisten: **connect time
  membaik** (— terutama cloudflare.com −40%).
- **Ulangi benchmark di rumah** (jaringan berbeda) untuk angka yang lebih valid —
  catat di tabel atas sebagai ronde baru.
- Disk/lokal & I/O scheduler **tidak diubah** (sudah optimal, dan governor
  `schedutil` dipakai demi baterai).

