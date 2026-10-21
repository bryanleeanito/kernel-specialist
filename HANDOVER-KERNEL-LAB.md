# HANDOVER — Kernel Lab (OpenCode #2, mesin Kali) → mesin Windows (OpenCode #1)

**Tanggal:** 21 Okt 2026 · **Oleh:** sesi OpenCode di Kali (root) · **Untuk:** OpenCode di Windows

> Dokumen ini di `D:\CyberSecurity!!!\07-SISTEM\` (Kali: `/run/media/kzldxxero/Data Lee Samsung/CyberSecurity!!!/07-SISTEM/`).
> **Kedua mesin membaca file yang sama** — ini kanal serah-terima utama.
> Kanal lain: mesh (`broadcast`/`handoff`) + GitHub (repo sudah ter-push).

---

## 1. Ringkasan: apa yang sudah dibuat (semua terverifikasi)

Mesin Kali sekarang punya **track kernel & co-pilot sistem** untuk OpenCode v2:

| Komponen | Isi | Lokasi |
|---|---|---|
| **Plugin `kernel-lab`** | 6 tool kernel native + **guardrail deny/ask** + context injection + pre-flight prompt hook | `~/.config/opencode/plugins/kernel-lab.js` |
| **Plugin `kali-ops`** | 8 tool **co-pilot sistem Kali** (status mesin, cek tool, jaringan, service, firewall, disk, paket apt, ubah paket) + guardrail sistem | `~/.config/opencode/plugins/kali-ops.js` |
| **Plugin `v1-compat`** | adapter: bikin plugin **API V1** jalan di OpenCode v2 (5 plugin lama hidup lagi) | `~/.config/opencode/plugins/v1-compat.js` |
| **Plugin `dev-journal` / `shell-env-dev`** | port V1→V2 (journal perintah shell + env UTF-8) | `~/.config/opencode/plugins/` |
| **Agent** | `kernel` (default), `kernel-reviewer`, `oops-analyst`, `driver-dev` | `~/.config/opencode/agents/` |
| **Command** | `/kbuild` `/kconfig` `/koops` `/kmodule` `/kperf` `/kstatus` | `~/.config/opencode/commands/` |
| **Skill** | `kernel-lab` (SOP: tuning runtime, analisis crash, modul OOT, build kernel) | `~/.config/opencode/skills/kernel-lab/` |
| **Kit tool (Python)** | `env_report` `config_check` `module_inspect` `kbuild` — 66/66 assertion | repo `kernel-specialist` |
| **Framework** | `FRAMEWORK.md` (L0–L8 + mode M1–M4 + 3 lapis proteksi) | repo `kernel-specialist` |
| **Mesh** | mesin terdaftar `kali-kernel` (role kernel) + 4 kit `kernel-*` | `opencode-mesh-v2` |

**Repo GitHub (sudah ter-push via SSH):**
- `git@github.com:bryanleeanito/kernel-specialist.git` (private) — kit + framework + track OpenCode
- `git@github.com:bryanleeanito/kali-ops.git` (private) — plugin co-pilot sistem
- `git@github.com:bryanleeanito/opencode-mesh-v2.git` (public) — mesh (54 commit baru ter-push)

## 1b. Topologi 2 instance OpenCode di mesin KALI (penting!)

| Instance | User | Config | Fokus | Tool native | Plugin |
|---|---|---|---|---|---|
| **#1** | `kzldxxero` | `~/.config/opencode/` | offensive · CTF · OSINT · pentest | 25 MCP (nmap/shodan/nuclei/hexstrike/pentest-mcp/kali-mcp/…) + agent `recon-analyst` `vuln-analyst` + command `/recon /scan /osint /ctf /pentest` + 7 skill | `shell-env` `dev-journal` `token-tracker` `agent-memory` `opencode-mem` **+ `kali-ops` + `kernel-lab` (baru 21 Okt)** |
| **#2** (sesi ini) | `root` | `/root/.config/opencode/` | **kernel & sistem** | namespace `kernel` (6) + `kali` (8) | `kernel-lab` `kali-ops` `v1-compat` `dev-journal` `shell-env-dev` |

**Yang kukasih ke instance #1 (21 Okt 2026):**
- plugin `kali-ops` (8 tool co-pilot sistem: `kali_sys_status` `kali_tool_check` `kali_net_status`
  `kali_svc_status` `kali_fw_status` `kali_disk_usage` `kali_pkg_info` `kali_pkg_change`)
  → **WAJIB dipakai sebelum eksekusi**: cek tool terpasang? status jaringan/firewall? paket mana? ubah paket (dry-run dulu).
- plugin `kernel-lab` (6 tool kernel) → berguna buat offensive: cek `.ko` mencurigakan
  (vermagic/signature/symbol), analisis crash dari exploit (`kernel_crashlog` → agent `oops-analyst`).
- **guardrail** keduanya ikut terpasang di instance #1 → perintah merusak **deny**, berisiko **ask**.
- section "Instance kembar" di `AGENTS.md` instance #1 (cara koordinasi via mesh + lokasi dokumen).

> Instance #1 **tidak** kuganggu setting/config/MCP-nya — hanya nambah 2 plugin + 1 section pointer.
> ✅ **Sudah termuat otomatis** (file watcher service, tanpa restart): `kali-ops` **active** + `kernel-lab` **active**
> di service instance #1 (port 49374). 7 plugin total di sana: dev-journal, shell-env, token-tracker,
> agent-memory, opencode-mem, **kali-ops**, **kernel-lab**.

**Koordinasi lintas instance (semua di mesin ini):**
- **Mesh** (bus): `kali-kernel` (role kernel) ↔ `windows-dev` (role development).
  `python3 scripts/broadcast.py --message "..."` · `handoff.py --to kali-kernel --task "..."`
- **Drive D: bersama**: `07-SISTEM/HANDOVER-KERNEL-LAB.md` + `07-SISTEM/kernel-lab/` (memori & tracker track kernel).
- **GitHub**: repo kit untuk sisi Windows.

## 2. Yang bisa langsung dipakai di Windows

```sh
git clone git@github.com:bryanleeanito/kernel-specialist.git
cd kernel-specialist && sh install.sh      # pasang agent/command/skill/plugin
opencode reload
```
- Tool `kernel` (6) & `kali` (8) langsung tersedia di TUI.
- Skill `kernel-lab` + command `/kbuild` `/kperf` `/koops` dst.
- **Butuh juga**: `linux-headers-$(uname -r)` (Linux) atau tidak (Windows — mode M2 runtime & M1 analisis log tetap jalan dari file log).
- MCP `github` di Windows: pakai PAT/OS key sendiri (token Kali hanya untuk repo yang diberi akses).

## 3. Cara kerja (mode, urut dari paling murah)

| Mode | Isi | Biaya | Catatan |
|---|---|---|---|
| **M1** Read & Debug | pahami kernel running, analisis crash/oops, peta modul | 0 build | skill `kernel-lab`, agent `oops-analyst` |
| **M2** Tuning runtime | BBR+FQ, buffer, swappiness, governor, I/O sched — **tanpa rebuild** | 0 build | 1 variabel/iterasi + ukur before/after |
| **M3** Modul OOT | 1 file C + Makefile → build **detik** → insmod → uji | detik | `KDIR=/lib/modules/$(uname -r)/build` |
| **M4** Build kernel penuh | kernel custom sungguhan | 1,5–2 jam · 5,6 GB · 4.020 modul | **opsional**; wajib `localmodconfig` + izin user |

## 4. Hasil eksperimen nyata (bukan klaim) — bahan belajar

**M2 (tuning runtime, 21 Okt):** `tcp_bbr`/`sch_fq` **ada** di `/lib/modules` tapi belum dimuat → BBR mati default.
A/B median 4 ronde bergantian: connect time debian 0,059→0,055 s · **cloudflare 0,091→0,055 s (−40%)**;
TTFB terlalu noisy (0,15–0,63 s antar request) → **tidak diklaim**. Persist: `/etc/sysctl.d/99-kernel-lab.conf` + `/etc/modules-load.d/kernel-lab.conf`.

**M3 (modul OOT):** modul `kernel_lab` → build detik → vermagic cocok → insmod → `/proc/kernel_lab` terbaca → module param rw via sysfs → rmmod bersih. Contoh lengkap: `kernel-specialist/examples/kernel_lab/`.

**M1 (analisis crash):** modul buggy memicu **Oops sungguhan** (SMAP violation: `buf[0]` di mode kernel tanpa `copy_from_user`).
Agent `oops-analyst` membedakannya dari entry `?` (suspects) dan menemukan **bug tersembunyi kedua**:
`v == 0xDEAD` unreachable (`buf[0]` cuma 0–255) → **GCC menghapus** blok `WARN_ON` → trigger tak pernah jalan.
Fix terverifikasi: `copy_from_user()` + `u16` → `\xAD\xDE` → WARNING muncul, kernel tetap hidup.
→ **Pelajaran inti**: compile ≠ branch reachable; selalu uji trigger-nya.

## 5. Pelajaran yang WAJIB dipakai di mesin Windows (hemat waktu)

1. **OpenCode v2 ≠ v1**: plugin v1 gagal load (`Missing key at [default]`). V2 butuh default export `{ id, setup(ctx) }`.
   Paket yang punya `v2-bridge` (mis. `opencode-goal-plugin`) bisa dipakai lewat adapter → **plugin `v1-compat.js`**.
2. **Config v1 → v2**: `permission`→`permissions`, `bash`→`shell`, `task`→`subagent`, `mcp`→`mcp.servers`, `plugin`→`plugins`.
3. **Conflict marker di repo = tool mati**: `opencode-mesh-v2` punya `<<<<<<<` ter-commit di 3 file → `mesh_integrator.py` **rusak** (SyntaxError).
   Penyebab: 2 mesin push tanpa pull. Fix: `git fetch` + `git rebase` (54/54 bersih 0 konflik), lalu `scripts/fix_state_conflict.py` untuk file JSON state.
4. **Guardrail ≠ hanya regex**: pola di-anchor ke **posisi perintah** + **isi heredoc dibuang** → `echo 'rm -rf /boot'` & dokumentasi LOLOS,
   eksekusi berbahaya tetap DENY. Dan `dd of=/dev/null` harus **boleh** (hanya device disk nyata yang ditolak).
5. **Fine-grained PAT = rebound**: bisa create repo & read public, tapi **tidak bisa write** → push 403 terus.
   **SSH key jauh lebih rebellious**: tanpa scope, tanpa expiry, tanpa secret bocor. `ssh -T git@github.com` = "successfully authenticated".
6. **API kernel 7.1 berbeda**: `struct new_utsname`+`utsname()` (bukan `uname()`) · `single_open()` (bukan `seq_open`) ·
   `ktime_get_boottime_seconds()` · `__DATE__` dilarang (`-Werror=date-time`) · daftar modul **tidak bisa** diakses dari modul.
   → **Baca header asli, jangan nebak.**

## 6. Yang MASIH terbuka (handover)

| Item | Status | Next |
|---|---|---|
| **M4 build kernel penuh** | belum (butuh 1,5–2 jam & 5,6 GB; source tree dihapus) | pakai `localmodconfig` → ~20 mnt; `install-kernel.sh` (dry-run dulu) |
| **Visibilitas 2 repo baru** | private → MCP github (token read-only) tidak bisa baca | ubah jadi public (konsisten dengan repo kit lain) **atau** tambah 2 repo ke "Repository access" token + `Metadata: Read` |
| **Benchmark tuning di rumah** | angka di sekolah noisy | ulangi A/B di jaringan rumah → isi tabel §8 `MEMORY-KERNEL.md` |
| **Modul `kernel_lab` nyangkut "Unloading"** | ±12 KB, fungsi habis | bersih total setelah reboot Kali |
| **Rotasi token GitHub** | token pernah tampil di chat (ikut DB sesi) | rotasi di `github.com/settings/personal-access-tokens` |

## 7. Sumber kebenaran (file yang harus dibaca)

| Dokumen | Isi | Lokasi |
|---|---|---|
| `MEMORY-KERNEL.md` | facts mesin, tuning §8, M1 §7c, M3 §7b, jebakan | `~/.config/opencode/MEMORY-KERNEL.md` (Kali) — **repo `kernel-specialist` tidak memuat file ini** (machine-local) |
| `TRACKER-KERNEL.md` | status per task + pelajaran | idem |
| `FRAMEWORK.md` | L0–L8 + playbook M1–M4 + 3 lapis proteksi | repo `kernel-specialist` (public via GitHub) |
| `HANDOFF.md` (kit) | status antar mesin | repo `kernel-specialist` |
| `07-SISTEM/opencode-mesh-v2/MESH_INTEGRATION.md` | cara pakai mesh (broadcast/handoff/ideas) | shared drive |
| `AGENTS.md` §"Kolaborasi AI Agent ↔ Sistem Kali" | doktrin kerja agent | `09-MIGRASI/kali/AGENTS.md` (shared) + `~/.config/opencode/AGENTS.md` (Kali) |

> **Catatan:** `MEMORY-KERNEL.md` & `TRACKER-KERNEL.md` sengaja **tidak** ikut ke repo (konten spesifik mesin).
> Kalau mau sinkron ke Windows: salin manual ke `D:\CyberSecurity!!!\07-SISTEM\kernel-lab\` (shared drive).

## 8. Rekomendasi untuk OpenCode Windows

1. **Baca dokumen ini dulu** (mulai dari §1 dan §5 — bagian yang paling biar hemat waktu).
2. **Clone 2 repo** (§2) → `sh install.sh` → `opencode reload` → tool `kernel` & `kali` langsung ada.
3. **Jangan ulang** percakapan yang sudah diselesaikan: M1/M2/M3 sudah selesai & terverifikasi (§4). Mulai dari M4 (kalau mau kernel custom) atau dari M2 iterasi-2 di rumah.
4. **Pakai mesh** untukUMBUNG balik: `python3 scripts/broadcast.py --message "..."` / `handoff.py --to kali-kernel --task "..."` (mesin Kali penjaga `kali-kernel`).
5. Kalau butuh **isi MEMORY-KERNEL.md** di sisi Windows: tulis ke `D:\CyberSecurity!!!\07-SISTEM\kernel-lab\` (shared) — jangan tulis ke `%USERPROFILE%\.config\opencode\` (itu miliknya Windows).
