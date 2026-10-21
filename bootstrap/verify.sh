#!/usr/bin/env bash
# verify.sh — bandingkan state mesin sekarang vs expected.json (paritas).
# Exit 0 = identik, 1 = ada perbedaan.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
EXPECTED="${1:-$HERE/expected.json}"
LAB="${LAB:-/root/kernel-lab}"
KIT="${KIT:-$LAB/kernel-specialist}"

command -v jq >/dev/null 2>&1 || { echo "[!] jq belum terpasang (apt install jq)"; exit 2; }
[ -f "$EXPECTED" ] || { echo "[!] expected.json tidak ditemukan: $EXPECTED"; exit 2; }

bash "$HERE/snapshot.sh" > /tmp/_snap_now.json 2>/dev/null
[ -s /tmp/_snap_now.json ] || { echo "[!] snapshot gagal"; exit 2; }

echo "════════ PARITY CHECK ════════"
echo "expected : $EXPECTED"
echo "now      : /tmp/_snap_now.json"
echo

DIFF=0
cmp_list() { # cmp_list <label> <jq-path>
  local label="$1" path="$2"
  local a b
  a=$(jq -c "$path" "$EXPECTED" 2>/dev/null | tr -d ' \n')
  b=$(jq -c "$path" /tmp/_snap_now.json 2>/dev/null | tr -d ' \n')
  if [ "$a" = "$b" ]; then
    printf '  [SAMA]  %-16s %s\n' "$label" "$(echo "$b" | cut -c1-90)"
  else
    printf '  [BEDA]  %-16s\n' "$label"
    printf '           expected: %s\n' "$(echo "$a" | cut -c1-160)"
    printf '           sekarang: %s\n' "$(echo "$b" | cut -c1-160)"
    DIFF=1
  fi
}
cmp_map() { # cmp_map <label> <jq-path>
  local label="$1" path="$2"
  local a b
  a=$(jq -c "$path" "$EXPECTED" 2>/dev/null | tr -d ' \n')
  b=$(jq -c "$path" /tmp/_snap_now.json 2>/dev/null | tr -d ' \n')
  if [ "$a" = "$b" ]; then
    printf '  [SAMA]  %-16s\n' "$label"
  else
    printf '  [BEDA]  %-16s\n' "$label"
    diff <(jq -r "$path" "$EXPECTED" 2>/dev/null | sort) \
         <(jq -r "$path" /tmp/_snap_now.json 2>/dev/null | sort) | sed 's/^/           /' | head -20
    DIFF=1
  fi
}

cmp_list "plugins"  '.plugins'
cmp_list "agents"   '.agents'
cmp_list "commands" '.commands'
cmp_list "skills"   '.skills'
cmp_map  "packages" '.packages'
cmp_map  "tuning"   '.tuning'
cmp_map  "files"    '.files'
cmp_list "mesh"     '.mesh'

echo
echo "── test suite ──"
jq -r '.tests | to_entries[] | "  \(.key): \(.value.summary) (rc=\(.value.rc))"' "$EXPECTED" 2>/dev/null
jq -r '.tests | to_entries[] | "  \(.key): \(.value.summary) (rc=\(.value.rc))"' /tmp/_snap_now.json 2>/dev/null | sed 's/^/  now: /'

echo
if [ "$DIFF" = "0" ]; then
  echo "RESULT: PARITAS OK — mesin sama persis dengan expected.json"
  exit 0
else
  echo "RESULT: ADA PERBEDAAN (lihat [BEDA] di atas)"
  echo "Tindak: jalankan bootstrap.sh untuk memulihkan fase yang terkait."
  exit 1
fi
