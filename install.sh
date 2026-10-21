#!/bin/sh
# install.sh — pasang track kernel (OpenCode #2) + tool kit ke mesin ini.
#
#   sh install.sh            → pasang config ke ~/.config/opencode (backup dulu)
#   sh install.sh --check    → hanya cek (tanpa mengubah apa pun)
#   sh install.sh --kit-only → hanya pasang tool kit (tidak sentuh config OpenCode)
#
# Aman: menimpa file config hanya dengan backup timestamped.
set -e

SRC="$(cd "$(dirname "$0")" && pwd)"
DST="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}"
LAB="${KERNEL_LAB_DIR:-/root/kernel-lab}"
MODE="${1:-install}"

say() { printf "[%s] %s\n" "$*" ""; }

case "$MODE" in
  --check)
    echo "== CHECK track kernel =="
    for f in "$DST/AGENTS.md" "$DST/KERNEL-AGENTS.md" "$DST/opencode.json"; do
      [ -f "$f" ] && echo "  OK  $f" || echo "  --  $f (belum ada)"
    done
    for a in kernel kernel-reviewer oops-analyst driver-dev; do
      [ -f "$DST/agents/$a.md" ] && echo "  OK  agent $a" || echo "  --  agent $a (belum ada)"
    done
    for c in kbuild kconfig koops kmodule kperf kstatus; do
      [ -f "$DST/commands/$c.md" ] && echo "  OK  command /$c" || echo "  --  command /$c (belum ada)"
    done
    [ -d "$DST/skills/kernel-lab" ] && echo "  OK  skill kernel-lab" || echo "  --  skill kernel-lab (belum ada)"
    echo "== tool kit =="
    [ -d "$LAB/kernel-specialist/tools" ] && echo "  OK  $LAB/kernel-specialist/tools" || echo "  --  tool kit belum ada di $LAB"
    exit 0
    ;;
  --kit-only)
    mkdir -p "$LAB/kernel-specialist"
    cp -rf "$SRC/tools" "$LAB/kernel-specialist/" 2>/dev/null || true
    cp -f "$SRC/README.md" "$SRC/HANDOFF.md" "$LAB/kernel-specialist/" 2>/dev/null || true
    echo "[OK] tool kit → $LAB/kernel-specialist"
    exit 0
    ;;
esac

TS="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$DST/agents" "$DST/commands" "$DST/skills"

backup() {
  [ -f "$1" ] || return 0
  cp -f "$1" "$1.bak-$TS"
  echo "[i] backup $(basename "$1") → $(basename "$1").bak-$TS"
}

# 1) instruksi track kernel
for f in KERNEL-AGENTS.md; do
  backup "$DST/$f"
  cp -f "$SRC/opencode/$f" "$DST/$f"
  echo "[OK] $f"
done

# 2) agent
for f in "$SRC"/opencode/agents/*.md; do
  n="$(basename "$f")"
  backup "$DST/agents/$n"
  cp -f "$f" "$DST/agents/$n"
  echo "[OK] agent $n"
done

# 3) command
for f in "$SRC"/opencode/commands/*.md; do
  n="$(basename "$f")"
  backup "$DST/commands/$n"
  cp -f "$f" "$DST/commands/$n"
  echo "[OK] command /$n"
done

# 4) skill
if [ -d "$SRC/opencode/skills/kernel-lab" ]; then
  mkdir -p "$DST/skills/kernel-lab"
  cp -rf "$SRC/opencode/skills/kernel-lab/." "$DST/skills/kernel-lab/"
  echo "[OK] skill kernel-lab"
fi

# 5) plugin OpenCode (kernel-lab guardrail + v1-compat + journal + shell env)
if [ -d "$SRC/opencode/plugins" ]; then
  mkdir -p "$DST/plugins"
  for f in "$SRC"/opencode/plugins/*.js; do
    n="$(basename "$f")"
    backup "$DST/plugins/$n"
    cp -f "$f" "$DST/plugins/$n"
    echo "[OK] plugin $n"
  done
fi

# 6) tool kit ke area kerja
mkdir -p "$LAB/kernel-specialist"
cp -rf "$SRC/tools" "$LAB/kernel-specialist/" 2>/dev/null || true
echo "[OK] tool kit → $LAB/kernel-specialist/tools"

# 7) area kerja
mkdir -p "$LAB/src" "$LAB/build" "$LAB/logs" "$LAB/config/fragments" "$LAB/stage"
echo "[OK] area kerja → $LAB"

cat <<'EOF'

NEXT (manual):
  1. opencode reload            # muat agent/command/skill/plugin baru
  2. /kstatus                   # cek state lab kernel
  3. /kperf                     # tuning runtime (tanpa rebuild)
  4. /koops <file-log>          # analisis crash kernel
  (install kernel hanya via install-kernel.sh, default dry-run)
EOF
