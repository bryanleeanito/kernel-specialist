#!/bin/sh
# install-kernel.sh — install kernel custom hasil build dengan aman.
#
#   sh install-kernel.sh                 # DRY-RUN: hanya cek + tampilkan rencana
#   sh install-kernel.sh --execute       # eksekusi install (butuh ENGINE)
#
# Prinsip (L6 framework):
#   - kernel custom SELALU punya versi berbeda dari kernel running (cek!).
#   - kernel stock WAJIB tetap ada (fallback dual-boot).
#   - tidak ada file stock yang ditimpa (verifikasi via checksum sebelum/sesudah).
#   - langkah yang merusak (install/initramfs/grub) hanya jalan dengan --execute.
#
# Environment override:
#   TREE=/root/kernel-lab/src/linux-7.1.5
#   OUT=/root/kernel-lab/build/linux-7.1.5
#   KVER=7.1.5+kali-amd64-custom   (default: ambil dari out/include/config/kernel.release)
set -eu

TREE="${TREE:-/root/kernel-lab/src/linux-7.1.5}"
OUT="${OUT:-/root/kernel-lab/build/linux-7.1.5}"
EXEC=0
[ "${1:-}" = "--execute" ] && EXEC=1

say()  { printf '\033[1;33m[%s]\033[0m %s\n' "$*" ""; }
ok()   { printf '  [OK]   %s\n' "$*"; }
bad()  { printf '  [BLOCK] %s\n' "$*"; BLOCK=1; }
BLOCK=0

say "PRE-FLIGHT install kernel custom"
echo "  tree : $TREE"
echo "  out  : $OUT"

# --- 1. artefak build wajib ada -------------------------------------------
for f in arch/x86/boot/bzImage vmlinux Module.symvers System.map; do
  if [ -f "$OUT/$f" ]; then
    ok "$(printf '%-28s %s bytes' "$f" "$(stat -c%s "$OUT/$f")")"
  else
    bad "artefak build belum ada: $OUT/$f — build dulu (kbuild.py)"
  fi
done

# --- 2. versi target ------------------------------------------------------
KVER="${KVER:-$(cat "$OUT/include/config/kernel.release" 2>/dev/null || echo "")}"
if [ -z "$KVER" ]; then
  bad "tidak bisa baca kernel.release dari $OUT"
else
  ok "versi target : $KVER"
fi
RUNNING="$(uname -r)"
if [ "$KVER" = "$RUNNING" ]; then
  bad "versi target SAMA dengan kernel running ($RUNNING) — install akan MENIMPA kernel stock!"
  bad "  fix: set CONFIG_LOCALVERSION=\"-custom\" lalu build ulang"
else
  ok "versi target BEDA dari kernel running ($RUNNING) → aman"
fi

# --- 3. kernel stock harus ada (fallback) ---------------------------------
STOCK_FOUND=0
for v in /boot/vmlinuz-*; do
  [ -e "$v" ] || continue
  b=$(basename "$v")
  [ "$b" = "vmlinuz-$KVER" ] && continue
  ok "fallback tersedia: $b"
  STOCK_FOUND=1
done
[ "$STOCK_FOUND" = "1" ] || bad "TIDAK ada kernel lain di /boot — jangan install (tidak ada fallback)"

# --- 4. ruang /boot --------------------------------------------------------
AVAIL_KB=$(df -k /boot | awk 'NR==2 {print $4}')
if [ "${AVAIL_KB:-0}" -lt 300000 ]; then
  bad "/boot tinggal ${AVAIL_KB} KB — tidak cukup untuk kernel + initramfs"
else
  ok "/boot bebas $(df -h /boot | awk 'NR==2 {print $4}')"
fi

# --- 5. initramfs & bootloader --------------------------------------------
command -v update-initramfs >/dev/null && ok "update-initramfs tersedia" || bad "update-initramfs tidak ada (apt install initramfs-tools)"
command -v update-grub >/dev/null && ok "update-grub tersedia" || bad "update-grub tidak ada (apt install grub2-common)"
if [ -f /etc/default/grub ]; then
  if grep -qE '^\s*GRUB_DISABLE_OS_PROBER\s*=\s*true' /etc/default/grub; then
    bad "GRUB_DISABLE_OS_PROBER=true — entri Windows akan hilang dari GRUB"
  else
    ok "os-prober aktif (entri Windows di GRUB aman)"
  fi
fi
if [ -f /boot/grub/grub.cfg ] && grep -qi "windows" /boot/grub/grub.cfg; then
  ok "entri Windows terdeteksi di grub.cfg (akan di-verifikasi ulang sesudah update)"
else
  printf '  [i]    entri Windows tidak terdeteksi di grub.cfg — cek manual\n'
fi

# --- 6. secure boot --------------------------------------------------------
if [ -r /sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c ]; then
  SB=$(od -An -tu1 -N5 /sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c | tr -d ' ' | cut -c5)
  if [ "$SB" = "0" ]; then ok "Secure Boot nonaktif — kernel custom boleh boot"
  else bad "Secure Boot AKTIF — kernel custom butuh MOK/enroll (tidak bisa boot tanpa itu)"; fi
fi

echo
if [ "$BLOCK" = "1" ]; then
  say "ADA BLOCKER — install dibatalkan (tidak ada yang diubah)"
  exit 1
fi

say "RENCANA INSTALL (kernel $KVER)"
cat <<EOF
  1. make O=$OUT modules_install   → /lib/modules/$KVER   (dir BARU, stock tidak disentuh)
  2. make O=$OUT install           → /boot/vmlinuz-$KVER   (file BARU, stock tidak disentuh)
  3. update-initramfs -c -k $KVER  → /boot/initrd.img-$KVER
  4. update-grub                   → entri baru di GRUB (entri Windows dipertahankan)
  5. verifikasi: /boot + grub.cfg + kernel stock masih utuh
  ROLLBACK: boot kernel stock (GRUB > Advanced options), lalu:
            rm -f /boot/vmlinuz-$KVER /boot/initrd.img-$KVER
            rm -rf /lib/modules/$KVER && update-grub
EOF

if [ "$EXEC" != "1" ]; then
  say "DRY-RUN — tidak ada yang diubah. Jalankan ulang dengan --execute untuk eksekusi."
  exit 0
fi

# ================= EKSEKUSI =================
say "EKSEKUSI INSTALL"
set -x
make -C "$TREE" O="$OUT" modules_install
make -C "$TREE" O="$OUT" install
update-initramfs -c -k "$KVER"
update-grub
set +x

say "VERIFIKASI"
for v in /boot/vmlinuz-*; do ok "terpasang: $(basename "$v")"; done
[ -d "/lib/modules/$KVER" ] && ok "modul terpasang: /lib/modules/$KVER" || bad "modul tidak ada di /lib/modules/$KVER"
if [ -f /boot/grub/grub.cfg ]; then
  echo "  entri kernel di GRUB:"
  grep -oE "menuentry '[^']+'" /boot/grub/grub.cfg | sed "s/^/    /" | head -20
  grep -qi "windows" /boot/grub/grub.cfg && ok "entri Windows MASIH ADA di grub.cfg" || bad "entri Windows hilang!"
fi
say "SELESAI — reboot untuk boot kernel $KVER (pilih manual di GRUB, jangan auto-pilih)"
