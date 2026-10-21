#!/usr/bin/env bash
# bench_net.sh — A/B benchmark congestion control (cubic vs bbr) + throughput.
#
#   bash bench_net.sh [rounds] [host1 host2 ...]
# Contoh: bash bench_net.sh 5 https://deb.debian.org https://cloudflare.com
#
# Output: tabel median per (cc × host) + throughput, lalu simpulan.
# Catatan: pakai median (bukan mean) + ronde bergantian → tahan noise jaringan.
set -uo pipefail

ROUNDS="${1:-5}"; shift || true
HOSTS=("$@")
[ ${#HOSTS[@]} -eq 0 ] && HOSTS=(https://deb.debian.org https://cloudflare.com https://www.kernel.org)
CURL="curl -sS -o /dev/null --max-time 15"

median() { python3 -c "
import sys,statistics
v=[float(x) for x in sys.stdin.read().split() if x.strip()]
print(f'{statistics.median(v):.4f}' if v else 'NA')"; }

echo "════ A/B NETWORK BENCH — $(date '+%F %H:%M') ════"
echo "rounds: $ROUNDS · hosts: ${HOSTS[*]}"
echo

for h in "${HOSTS[@]}"; do
  echo "── $h ──"
  printf "  %-6s %10s %10s\n" "cc" "connect" "ttfb"
  for cc in cubic bbr; do
    sysctl -w net.ipv4.tcp_congestion_control=$cc >/dev/null 2>&1
    con=""; ttfb=""
    for i in $(seq 1 "$ROUNDS"); do
      r=$($CURL -w "%{time_connect} %{time_starttransfer}" "$h" 2>/dev/null)
      con="$con $(echo "$r" | cut -d' ' -f1)"; ttfb="$ttfb $(echo "$r" | cut -d' ' -f2)"
    done
    mc=$(printf "%s" "$con" | median); mt=$(printf "%s" "$ttfb" | median)
    printf "  %-6s %10s %10s\n" "$cc" "$mc" "$mt"
  done
done

echo
echo "── throughput (25MB, 3x tiap cc) ──"
URL="https://speed.cloudflare.com/__down?bytes=25000000"
for cc in cubic bbr; do
  sysctl -w net.ipv4.tcp_congestion_control=$cc >/dev/null 2>&1
  sp=""
  for i in 1 2 3; do
    v=$($CURL -w "%{speed_download}" "$URL" 2>/dev/null | tail -1)
    [ -n "$v" ] && sp="$sp $v"
  done
  if [ -n "$sp" ]; then
    med=$(printf "%s" "$sp" | python3 -c "
import sys,statistics
v=[float(x) for x in sys.stdin.read().split() if x.strip()]
print(f'{statistics.median(v)/1e6:.1f}' if v else 'NA')")
    printf "  %-6s %s MB/s (median)\n" "$cc" "$med"
  else
    printf "  %-6s (gagal unduh — mungkin URL diblokir jaringan)\n" "$cc"
  fi
done

# kembalikan ke setting yang dipakai
sysctl -w net.ipv4.tcp_congestion_control=bbr >/dev/null 2>&1
sysctl -w net.core.default_qdisc=fq >/dev/null 2>&1
echo
echo "(dikembalikan: cc=bbr, qdisc=fq)"
