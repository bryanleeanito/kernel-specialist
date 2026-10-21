#!/usr/bin/env bash
# bootstrap.sh — restore lingkungan "Kernel Lab" di mesin Kali (fresh install OS).
#
# Semua fase IDEMPOTEN: aman dijalankan berulang, fase yang sudah beres dilewati.
#
#   sudo bash bootstrap.sh                 # semua fase
#   sudo bash bootstrap.sh --only=4,5      # hanya fase tertentu
#   sudo bash bootstrap.sh --skip=2        # lewati fase
#   sudo bash bootstrap.sh --list          # daftar fase
#
# Sumber kebenaran (berurutan prioritas):
#   1. Drive D: /run/media/*/*/CyberSecurity*  (offline, selalu ada)
#   2. GitHub (butuh SSH key / token)
#   3. Isi paket ini (fallback minimum)
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
LAB="${LAB:-/root/kernel-lab}"
KIT="${KIT:-$LAB/kernel-specialist}"
CFG="${CFG:-/HOME/.config/opencode}"
DRIVE=""
for base in "/run/media"/*/*/CyberSecurity* "/mnt/d/CyberSecurity"* "/media"/*/CyberSecurity*; do
  [ -d "$base" ] && { DRIVE="$base"; break; }
done
MESH="$DRIVE/07-SISTEM/opencode-mesh-v2"
MIG="$DRIVE/09-MIGRASI"
SHARED="$DRIVE/07-SISTEM/kernel-lab"
BOOT="$DRIVE/07-SISTEM/kali-lab-bootstrap"

ONLY=""; SKIP=""
for a in "$@"; do
  case "$a" in
    --only=*) ONLY="${a#--only=}" ;;
    --skip=*) SKIP="${a#--skip=}" ;;
    --list) echo "fase: 0 preflight · 1 base-pkg · 2 offensive-tools · 3 skills · 4 plugins · 5 track-config · 6 memory · 7 tuning · 8 git · 9 mesh · 10 verify"; exit 0 ;;
  esac
done

say()  { printf '\n\033[1;36m[%s]\033[0m %s\n' "$1" "${2:-}"; }
ok()   { printf '  [OK]   %s\n' "$*"; }
skip() { printf '  [--]   %s\n' "$*"; }
warn() { printf '  [!]    %s\n' "$*"; }
run_phase() { # run_phase <n> <nama> <fungsi>
  local n="$1" name="$2" fn="$3"
  if [ -n "$ONLY" ] && ! echo ",$ONLY," | grep -q ",$n,"; then skip "fase $n ($name) — dilewati (--only)"; return 0; fi
  if [ -n "$SKIP" ] && echo ",$SKIP," | grep -q ",$n,"; then skip "fase $n ($name) — dilewati (--skip)"; return 0; fi
  say "FASE $n" "$name"
  "$fn"
}

need_root() { [ "$(id -u)" -eq 0 ] || { warn "harus root (sudo)"; exit 1; }; }

# ---------------------------------------------------------------- 0 preflight
ph0() {
  need_root
  ok "root ✓"
  ok "OS     : $(. /etc/os-release; echo "$PRETTY_NAME")"
  ok "kernel : $(uname -r)"
  [ -n "$DRIVE" ] && ok "drive  : $DRIVE" || warn "drive D: TIDAK ditemukan — fase yang butuh drive akan dilewati (pakai GitHub/fallback)"
  [ -d "$KIT" ] && ok "kit    : $KIT" || warn "kit kernel-specialist tidak ada di $KIT (klon dari GitHub: git clone git@github.com:bryanleeanito/kernel-specialist.git $KIT)"
  mkdir -p "$LAB" "$CFG"/{agents,commands,skills,plugins} "$LAB"/{src,build,logs,config/fragments,stage} "$LAB"/{kernel-specialist,kali-ops}
}

# --------------------------------------------------------------- 1 base-pkg
ph1() {
  export DEBIAN_FRONTEND=noninteractive
  say "apt update + paket dasar"
  echo 'Acquire::ForceIPv4 "true";' > /etc/apt/apt.conf.d/99force-ipv4
  apt-get update -qq
  apt-get install -y -qq build-essential bc bison flex libssl-dev libelf-dev dwarves ccache lld rustc \
    rust-src bindgen nodejs jq cpio zstd rsync kmod python3-dev libncurses-dev ca-certificates git curl
  apt-get install -y -qq "linux-headers-$(uname -r)" 2>/dev/null || warn "headers $(uname -r) tidak ada di repo — pasang versi yang cocok"
  ok "toolchain kernel + base siap"
}

# --------------------------------------------------------- 2 offensive-tools
ph2() {
  if [ -f "$MIG/kali-tools.sh" ]; then
    say "tool offensive (dari 09-MIGRASI/kali-tools.sh)"
    sh "$MIG/kali-tools.sh" 2>&1 | tail -12
    ok "tool offensive & node/uv terpasang"
  else
    skip "kali-tools.sh tidak ditemukan (butuh drive) — lewati"
  fi
}

# ----------------------------------------------------------------- 3 skills
ph3() {
  say "skills (eksternal + track kernel)"
  if [ -d "$MIG/skills-eksternal" ]; then
    mkdir -p "$HOME/.agents/skills"
    cp -rf "$MIG/skills-eksternal/." "$HOME/.agents/skills/"
    ok "skills eksternal → ~/.agents/skills ($(ls -1 "$HOME/.agents/skills" | wc -l))"
  else
    warn "bundle skills eksternal tidak ditemukan"
  fi
  if [ -d "$KIT/opencode/skills" ]; then
    mkdir -p "$CFG/skills"
    cp -rf "$KIT/opencode/skills/." "$CFG/skills/"
    ok "skill track kernel → ~/.config/opencode/skills"
  fi
}

# ---------------------------------------------------------------- 4 plugins
ph4() {
  say "plugin OpenCode (kernel-lab, kali-ops, v1-compat, journal, shell-env)"
  local src=""
  for cand in "$KIT/opencode/plugins" "$BOOT/plugins" "$LAB/kernel-specialist/opencode/plugins"; do
    [ -d "$cand" ] && { src="$cand"; break; }
  done
  if [ -z "$src" ]; then warn "sumber plugin tidak ditemukan"; return 0; fi
  mkdir -p "$CFG/plugins"
  for f in "$src"/*.js; do
    n="$(basename "$f")"
    [ -f "$CFG/plugins/$n" ] && cp -f "$CFG/plugins/$n" "$CFG/plugins/$n.bak-$(date +%Y%m%d-%H%M%S)"
    cp -f "$f" "$CFG/plugins/$n"
    ok "plugin $n"
  done
  # instance kedua (user biasa) — kalau ada
  local other="/home/kzldxxero/.config/opencode"
  if [ -d "$other" ] && [ "$(id -un)" = "root" ]; then
    mkdir -p "$other/plugins"
    for f in "$src"/kali-ops.js "$src"/kernel-lab.js; do
      [ -f "$f" ] && { cp -f "$f" "$other/plugins/$(basename $f)"; chown -R kzldxxero:kzldxxero "$other/plugins" 2>/dev/null; ok "plugin $(basename $f) → instance #1"; }
    done
  fi
}

# ------------------------------------------------------- 5 track-config
ph5() {
  say "track config (agent, command, instruksi)"
  if [ -x "$KIT/install.sh" ] || [ -f "$KIT/install.sh" ]; then
    sh "$KIT/install.sh" 2>&1 | tail -20
    ok "install.sh kit dijalankan"
  else
    warn "install.sh kit tidak ada — fase dilewati"
  fi
}

# --------------------------------------------------------------- 6 memory
ph6() {
  say "restore MEMORY / TRACKER / AGENTS (memori per-OS)"
  # 6a. track kernel (dari drive bersama atau repo)
  local msrc=""
  for cand in "$SHARED" "$KIT/docs/machine-local"; do
    [ -d "$cand" ] && { msrc="$cand"; break; }
  done
  if [ -n "$msrc" ]; then
    for f in MEMORY-KERNEL.md TRACKER-KERNEL.md KERNEL-AGENTS.md; do
      [ -f "$msrc/$f" ] && { cp -f "$msrc/$f" "$CFG/$f"; ok "$f → ~/.config/opencode/"; }
    done
  else
    warn "salinan memori track kernel tidak ditemukan"
  fi
  # 6b. track offensive (dari paket 09-MIGRASI)
  if [ -d "$MIG/kali" ]; then
    for f in AGENTS.md MEMORY.md TRACKER.md; do
      [ -f "$MIG/kali/$f" ] && { cp -f "$MIG/kali/$f" "$CFG/$f.bak-$(date +%Y%m%d-%H%M%S)" 2>/dev/null; cp -f "$MIG/kali/$f" "$CFG/$f"; ok "$f → ~/.config/opencode/"; }
    done
    [ -d "$MIG/kali/skills" ] && { mkdir -p "$CFG/skills"; cp -rf "$MIG/kali/skills/." "$CFG/skills/"; ok "skill track offensive → ~/.config/opencode/skills"; }
  fi
  # 6c. config opencode.json (V2) — pakai yang di repo kalau ada
  if [ -f "$BOOT/opencode.json" ]; then
    cp -f "$BOOT/opencode.json" "$CFG/opencode.json.bak-$(date +%Y%m%d-%H%M%S)" 2>/dev/null
    cp -f "$BOOT/opencode.json" "$CFG/opencode.json"
    ok "opencode.json (V2) → ~/.config/opencode/"
  fi
}

# ---------------------------------------------------------------- 7 tuning
ph7() {
  say "tuning runtime M2 (BBR+FQ, buffer, swappiness) — persist reboot"
  if [ -f "$BOOT/tuning/99-kernel-lab.conf" ]; then
    cp -f "$BOOT/tuning/99-kernel-lab.conf" /etc/sysctl.d/99-kernel-lab.conf
    ok "/etc/sysctl.d/99-kernel-lab.conf"
  else
    cat > /etc/sysctl.d/99-kernel-lab.conf <<'EOF'
# 99-kernel-lab.conf — track kernel M2 (lihat MEMORY-KERNEL.md §8)
net.ipv4.tcp_congestion_control = bbr
net.core.default_qdisc = fq
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 131072 16777216
net.ipv4.tcp_wmem = 4096 16384 16777216
vm.swappiness = 10
vm.vfs_cache_pressure = 50
EOF
    ok "/etc/sysctl.d/99-kernel-lab.conf (default ditulis)"
  fi
  cat > /etc/modules-load.d/kernel-lab.conf <<'EOF'
tcp_bbr
sch_fq
EOF
  ok "/etc/modules-load.d/kernel-lab.conf (tcp_bbr, sch_fq)"
  modprobe tcp_bgr 2>/dev/null; modprobe tcp_bbr 2>/dev/null; modprobe sch_fq 2>/dev/null
  sysctl -p /etc/sysctl.d/99-kernel-lab.conf >/dev/null 2>&1
  ok "diterapkan sekarang: cc=$(sysctl -n net.ipv4.tcp_congestion_control) qdisc=$(sysctl -n net.core.default_qdisc)"
}

# ------------------------------------------------------------------- 8 git
ph8() {
  say "git: identitas, credential helper, SSH key, remote"
  git config --global user.name "kzldx"
  git config --global user.email "kzldx@users.noreply.github.com"
  git config --global credential.helper '!f() { echo username=x-access-token; echo "password=$GITHUB_TOKEN"; }; f'
  ok "identitas + credential helper (baca env var, tanpa file kredensial)"
  if [ ! -f "$HOME/.ssh/id_ed25519_github" ]; then
    ssh-keygen -t ed25519 -N "" -C "kzldx@users.noreply.github.com (kali-kernel-lab)" -f "$HOME/.ssh/id_ed25519_github" >/dev/null 2>&1
    cat > "$HOME/.ssh/config" <<'EOF'
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_github
  IdentitiesOnly yes
EOF
    chmod 600 "$HOME/.ssh/config"
    warn "PUBLIC KEY BARU (tambahkan di https://github.com/settings/ssh/keys):"
    cat "$HOME/.ssh/id_ed25519_github.pub" | sed 's/^/    /'
  else
    ok "SSH key sudah ada"
  fi
  # remote untuk repo kit
  for pair in "$KIT:kernel-specialist" "$LAB/kali-ops:kali-ops" "$MESH:opencode-mesh-v2"; do
    d="${pair%%:*}"; n="${pair##*:}"
    [ -d "$d/.git" ] || continue
    if git -C "$d" remote get-url origin >/dev/null 2>&1; then
      git -C "$d" remote set-url origin "git@github.com:bryanleeanito/$n.git" 2>/dev/null && ok "remote $n → SSH"
    else
      git -C "$d" remote add origin "git@github.com:bryanleeanito/$n.git" 2>/dev/null && ok "remote $n ditambahkan (SSH)"
    fi
  done
  # MCP github butuh token
  if [ -f "$CFG/service.json" ] && ! grep -q GITHUB_TOKEN "$CFG/service.json" 2>/dev/null; then
    printf 'Token GitHub untuk MCP github (kosong = lewati): '
    stty -echo 2>/dev/null; read -r GT; stty echo 2>/dev/null; printf '\n'
    [ -n "$GT" ] && { python3 - "$CFG/service.json" "$GT" <<'PY'
import json,sys
p, tok = sys.argv[1], sys.argv[2]
d = json.load(open(p)); d.setdefault("env", {})["GITHUB_TOKEN"] = tok
json.dump(d, open(p,"w"), indent=2); open(p,"a").write("\n")
import os; os.chmod(p, 0o600)
print("  [OK] env service diset (MCP github aktif setelah restart)")
PY
    }
  else
    skip "GITHUB_TOKEN sudah ada di service config"
  fi
}

# ----------------------------------------------------------------- 9 mesh
ph9() {
  say "mesh: daftar sebagai kali-kernel + presence"
  if [ ! -d "$MESH" ]; then warn "repo mesh tidak ditemukan ($MESH)"; return 0; fi
  python3 "$MESH/scripts/register.py" --name "kali-kernel" --role kernel --ip "$(ip -4 -o addr show wlan0 2>/dev/null | awk '{print $4}' | cut -d/ -f1 | head -1)" --capabilities kernel,kbuild,driver,perf,debug 2>&1 | sed 's/^/  /'
  python3 "$MESH/scripts/mesh_status.py" --name kali-kernel --local 2>&1 | sed 's/^/  /' | head -8
  ok "terdaftar + presence ditulis (IP DHCP aman: presence di-refresh tiap sync)"
  # presence cron (agar tetap online setelah reboot) — idempotent
  if crontab -l 2>/dev/null | grep -q "mesh-presence"; then
    ok "cron presence sudah ada"
  else
    ( cd "$MESH" && python3 scripts/mesh_status.py --install 2>&1 | tail -4 | sed 's/^/  /' )
    ok "cron presence di-install (*/15 + @reboot)"
  fi
}

# --------------------------------------------------------------- 10 verify
ph10() {
  say "verifikasi paritas"
  if [ -f "$HERE/verify.sh" ]; then
    bash "$HERE/verify.sh" || warn "paritas: ada yang beda (lihat report di atas)"
  else
    warn "verify.sh tidak ada"
  fi
}

run_phase 0 preflight     ph0
run_phase 1 base-pkg      ph1
run_phase 2 offensive-tools ph2
run_phase 3 skills        ph3
run_phase 4 plugins       ph4
run_phase 5 track-config  ph5
run_phase 6 memory        ph6
run_phase 7 tuning        ph7
run_phase 8 git           ph8
run_phase 9 mesh          ph9
run_phase 10 verify       ph10

say "BOOTSTRAP SELESAI"
cat <<'EOF'
Langkah manual yang tersisa:
  1. Kalau SSH key baru dibuat → tempel public key ke https://github.com/settings/ssh/keys
  2. Restart OpenCode (atau: opencode service restart) → MCP github connect
  3. Cek parity: bash verify.sh
EOF
