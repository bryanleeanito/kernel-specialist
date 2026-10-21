# TRACKER-KERNEL (KALI) — Status Track Kernel Development (OpenCode #2)

**Aturan pakai:** baca di awal sesi, **update tiap ada perubahan status** (bukan cuma
akhir sesi). Status: `TODO` · `PROGRES` · `SELESAI` · `BLOKAD`.
Kolom hasil wajib berisi **bukti nyata** (output make, path artefak, angka).

**Terakhir diperbarui:** 2026-10-21

## Aktif

| # | Tugas | Status | Hasil / bukti | Diperbarui |
|---|---|---|---|---|
| 1 | Toolchain kernel (gcc/bison/flex/dwarves/ccache/lld/rustc/libelf/libssl) | SELESAI | rustc 1.95.0 + lld 21.1.8 + pahole 1.32 + bison 3.8.2 + bindgen 0.72.1 + rust-src terpasang; cocok `CONFIG_RUSTC_VERSION_TEXT` & `CONFIG_RUSTC_LLVM_VERSION=210108` | 2026-10-21 |
| 2 | `deb-src` Kali + source kernel running | SELESAI | `/root/kernel-lab/src/linux-7.1.5` (1.8G, patch Kali ikut, v7.1.5); unduhan 161.650.220 byte ✓ (percobaan 2x terpotong → unduh manual via curl) | 2026-10-21 |
| 3 | Tool kit kernel (4 tool + tes) | SELESAI | `tests/run_all.py` → 5/5 berkas, **66/66 assertion** lulus (4 tool + guardrail plugin) | 2026-10-21 |
| 4 | Track OpenCode kernel (agent/command/skill) | SELESAI | 4 agent + 6 command + skill `kernel-lab` terpasang di `~/.config/opencode`; `install.sh --check` semua OK | 2026-10-21 |
| 5 | Track KALI (offensive) + V1→V2 config | SELESAI | AGENTS/MEMORY/TRACKER + 3 skill + 32 skill eksternal + 2 plugin lokal terpasang; `opencode.json` (paket + mesin) dikonversi ke V2 | 2026-10-21 |
| 6 | **Plugin V2 + guardrail** | SELESAI | `kernel-lab.js` (6 tool + deny/ask hook + context + prompt safety), `v1-compat.js` (5 plugin V1 hidup lagi → `/goal` + agent `goal`), `dev-journal.js` (journal terbukti terisi), `shell-env-dev.js` | 2026-10-21 |
| 7 | **Framework kernel** (L0–L8 + 3 lapis proteksi) | SELESAI | `FRAMEWORK.md` di repo kit | 2026-10-21 |
| 8 | **Perbaikan repo mesh** | SELESAI | conflict marker ter-commit di README/MESH_INTEGRATION/test_all → dibersihkan; `mesh_integrator.py` rusak → diperbaiki + kategori kit kernel; tes mesh 18/18 lulus; commit lokal | 2026-10-21 |
| 9 | Integrasi mesh mesin ini | SELESAI | terdaftar `kali-kernel` (role kernel, IP DHCP — live: `state/presence/kali-kernel.json`, terakhir 15.15.0.201, cap kernel/kbuild/driver/perf/debug); `run-kit --kit kernel-env-report` → output normal | 2026-10-21 |
| 10 | **Build baseline semi-custom** | **DIBATALKAN (keputusan user 21 Okt)** | build dihentikan di ~6.400 objek: butuh ~1,5–2 jam + **5,6 GB** artefak + 1,4 GB ccache → terlalu berat. User: "gak usah bikin custom kernel dulu". Artefak + ccache **sudah dihapus** (bersih, free 62G) | 2026-10-21 |
| 10b | Source tree kernel | **DIBATALKAN (dihapus)** | `/root/kernel-lab/src/linux-7.1.5` (1,9 GB) **dihapus** 21 Okt 2026 → hemat 1,9 GB. Obtain ulang kalau M4 perlu: `deb-src` Kali + `apt-get source linux` (161 MB, sempat terpotong 2x → unduh manual `curl -L -C -` + verifikasi ukuran vs `.dsc`) | 2026-10-21 |
| 11a | **M2 tuning runtime** (tanpa rebuild) | **PROGRES (satu iterasi selesai)** | 21 Okt: BBR+FQ aktif (`modprobe tcp_bbr/sch_fq` + sysctl), socket buffer 4→16 MB, swappiness 60→10, vfs_cache_pressure 100→50. A/B median 4 ronde: connect time debian 0,059→0,055 s · cloudflare 0,091→0,055 s (−40%); TTFB noise (tidak diklaim). Persist: `/etc/sysctl.d/99-kernel-lab.conf` + `/etc/modules-load.d/kernel-lab.conf`. Jejak: `MEMORY-KERNEL.md` §8 | 2026-10-21 |
| 11b | **M3 modul out-of-tree** | **SELESAI** | modul `kernel_lab` (/proc/kernel_lab + module param): build **detik** → vermagic cocok → insmod → baca data nyata → param sysfs rw → rmmod bersih. `linux-headers-7.1.5+kali-amd64` terpasang. Catatan API kernel 7.1 + 2 bug tool `module_inspect` yang ditemukan & diperbaiki. Sumber: `examples/kernel_lab/` | 2026-10-21 |
| 11d | **M1 analisis crash kernel** | **SELESAI** | oops nyata dari modul buggy (SMAP violation, page fault di `lab_write+0x16`) → agent `oops-analyst` menganalisis log → root cause (deref user pointer tanpa `copy_from_user`) + bug tersembunyi (branch `0xDEAD` unreachable → GCC hapus WARN_ON) → fix terverifikasi (probe: 2 byte OK, 1 byte EINVAL, `\xAD\xDE` → WARNING tanpa oops). Sumber: `examples/kernel_lab/`. Catatan: modul buggy nyangkut 'Unloading' (referensi bocor dari proses mati saat oops) — bersih setelah reboot | 2026-10-21 |
| 11c | Fragment config `perf.conf` + `debug.conf` (untuk M4 nanti) | SELESAI | keduanya `config_check` → **PASS, 0 temuan** (19 + 22 opsi, disesuaikan API tree 7.1.5: HZ_1000 maks, SCHEDSTATS, DEBUG_VM_MAPLE_TREE, Btrfs tanpa BTRFS_ZSTD). **Belum dipakai di build** — masih butuh persetujuan user | 2026-10-21 |
| 19 | **M2 iterasi-2 (rumah)** | **SELESAI** | A/B 5 ronde di jaringan rumah: BBR connect −1…−4%, TTFB ±2%, throughput 25MB 3,8→3,9 MB/s (+2,6%). **Koreksi honesty**: angka −40% di sekolah itu noise (varians 0,15–0,63 s), bukan gain. 2 eksperimen negatif: CPU governor performance hanya +1,05% (jangan diubah, boros baterai) · tcp_slow_start_after_idle 0 → −1,4% (jangan diubah). Kesimpulan: sistem sudah di baseline bagus, jangan cargo-cult tuning. Tool: `tools/kernel/bench_net.sh` | 2026-10-21 |
| 12 | Cek Secure Boot & strategi boot custom kernel | SELESAI | Secure Boot **nonaktif** (`SecureBoot=0`, `SetupMode=1` di efivars) → kernel custom boleh boot tanpa MOK; `mokutil` tidak ada di repo Kali → deteksi efivars (tool env_report + preflight sudah pakai) | 2026-10-21 |
| 14 | **Co-pilot sistem (`kali-ops`)** | SELESAI | 8 tool native namespace `kali` (sys_status, tool_check, net_status, svc_status, fw_status, disk_usage, pkg_info, pkg_change) + guardrail sistem (deny/ask) + context injection; **52/52 assertion**; repo `07-SISTEM/kali-ops/` | 2026-10-21 |
| 15 | Guardrail anti-false-positive | SELESAI | pola di-anchor ke posisi perintah + isi heredoc dibuang → `echo 'rm -rf /boot'` & dokumentasi heredoc LOLOS, eksekusi berbahaya tetap DENY. kernel-lab 39/39, kali-ops 52/52 | 2026-10-21 |
| 16 | Doktrin Kolaborasi Agent↔Kali | SELESAI | section baru di `AGENTS.md` (paket + terpasang): LIHAT→USULKAN→IZIN→KERJAKAN→VERIFIKASI + namespace tool `kali`/`kernel` | 2026-10-21 |
| 17 | **Bootstrap restore (reinstall OS)** | **SELESAI** | paket `bootstrap/` (11 fase idempotent + `verify.sh` + `expected.json`) → drive `07-SISTEM/kali-lab-bootstrap/` + GitHub `kernel-specialist/bootstrap/`. Uji: `bootstrap.sh --skip=1,2,7,8,9` jalan bersih; `verify.sh` → **PARITAS OK** (semua field identik). Bug yg ketemu saat uji: `say()` unbound + `:-{}` pattern expansion → sudah diperbaiki | 2026-10-21 |
| 18 | Perbaikan skrip finish-github-setup | SELESAI | 3 bug ketemu saat uji: (1) `ssh -T` exit=1 walau sukses → deteksi via output; (2) paste token nyasar karakter (`sgithub_pat_…`) → trim+validasi; (3) skrip menimpa env dgn token kosong → guard. Env service diperbaiki (len 93, GET /user HTTP 200) | 2026-10-21 |
| 13 | Push repo ke GitHub | **SELESAI** | 3 repo ter-push via **SSH** (bukan token — fine-grained PAT tak bisa write): `kernel-specialist` (master) · `kali-ops` (master) · `opencode-mesh-v2` (main, 54 commit, rebase bersih). MCP github CONNECTED (token di env service) | 2026-10-21 |

## Milestone kernel

| Tanggal | Target | Status |
|---|---|---|
| 2026-10-21 | Track kernel siap (toolchain + kit + track OpenCode) | **selesai ✓** |
| next | Build baseline kernel custom (bzImage + modules) terverifikasi | — |
| next | Install + boot dual-boot aman (stock kernel tetap ada) | — |
| next | Tuning pertama (1 variabel per build) + ukur before/after | — |

## Pelajaran dari kesalahan

| Kesalahan | Pelajaran (jangan diulang) |
|---|---|
| `config_check.py` crash `NameError: json` saat `--json` | setiap tool wajib smoke-test mode JSON **dan** mode text; gate `tests/run_all.py` wajib hijau sebelum commit |
| `module_inspect.py` return 0 walau modul tidak ada | kode "tidak bisa dibaca" juga harus dihitung sebagai kegagalan (exit 1) |
| `09-MIGRASI/kali/opencode.json` format V1 | OpenCode di mesin ini **v2.1.1** — jangan salin config V1 mentah; konversi field (`permission`→`permissions`, `bash`→`shell`, `task`→`subagent`, `mcp`→`mcp.servers`, `plugin`→`plugins`) |
| `mesh_integrator.py` punya conflict marker ter-commit | 2 mesin push tanpa pull → cek `git status` + `grep '<<<<<<<'` sebelum commit; conflict di file Python = tool mati |
| `HOSTCC="ccache gcc"` bikin build gagal | `scripts/Makefile.host` pakai `-Clinker=$(HOSTCC)` → rustc parse "ccache gcc" sebagai 2 input file. **Ccache hanya lewat `CC=ccache gcc`**, jangan sentuh HOSTCC |
| `CONFIG_RUST` hilang setelah `olddefconfig` | `config RUST` butuh `RUST_IS_AVAILABLE` (dicek saat build) → pakai `make rustavailable` untuk diagnosa. Butuh `bindgen` + paket `rust-src` (std library source) |
| Unduhan `apt-get source` terpotong 2x | proses background dibunuh → unduh manual `curl -L -C -` lalu verifikasi ukuran vs ukuran di `.dsc` (`dpkg-source` akan protes kalau kurang) |
| `mokutil` tidak terpasang → `apt install` gagal | mirror IPv6 mati (`mirror.freedif.org`) → tambah `/etc/apt/apt.conf.d/99force-ipv4` ("Acquire::ForceIPv4 true") |
| Semua plugin V1 gagal load di OpenCode v2 | v2 butuh default export `{id, setup(ctx)}`. Plugin V1 dimuat lewat adapter `v1-compat.js` (atau paket yang punya `v2-bridge`) |
| **Build kernel penuh terlalu berat** | config stock Kali = **4.020 modul** → ~12.000 objek → **~1,5–2 jam** di laptop ini (6C/12T) + **5,6 GB** artefak + 1,4 GB ccache. **Jangan** build penuh untuk iterasi. Pakai `localmodconfig` (hanya modul hardware aktif) → ~15–20 mnt, ±1–2 GB |
| **Ganti 1 opsi config = rebuild ~90% objek** | `include/config/auto.conf` berubah → semua sumber pra-proses berubah → **ccache hit rate anjlok (~5%)**. Jadi "build incremental" setelah ubah config = hampir build penuh. Konsekuensi: 1 build = 1 eksperimen, jangan diubah-ubah di tengah |
| Perkiraan waktu build jangan asal | sempat bilang "±15–25 menit" padahal aslinya ~1 jam → **ukur dulu** (jumlah objek/menit + tahap make) baru janji waktu |

## Status environment (ringkas, detail di `MEMORY-KERNEL.md`)

- kernel running `7.1.5+kali-amd64` · CPU 12 core · RAM 14G · root fs sisa ~67G
- source tree `linux-7.1.5` · build dir `linux-7.1.5` (out-of-tree) · belum ada build
- config base `/boot/config-$(uname -r)` · fragment: belum ada
