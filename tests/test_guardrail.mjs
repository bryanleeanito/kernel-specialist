// test_guardrail.mjs — unit test guardrail plugin kernel-lab (Jalankan: node tests/test_guardrail.mjs)
//
// Men断言: perintah yang bisa merusak boot/dual-boot harus DENY,
// perintah berisiko install harus ASK, perintah aman harus lolos.
import { fileURLToPath } from "node:url"
import path from "node:path"
import fs from "node:fs"

const HERE = path.dirname(fileURLToPath(import.meta.url))
const PLUGIN = process.env.KERNEL_LAB_PLUGIN || "/root/.config/opencode/plugins/kernel-lab.js"

if (!fs.existsSync(PLUGIN)) {
  console.error(`[XX] plugin tidak ditemukan: ${PLUGIN}`)
  process.exit(1)
}

const { __guard } = await import("file://" + PLUGIN)
const check = __guard.check

let pass = 0
let fail = 0
function t(name, cond, detail) {
  if (cond) {
    pass++
    console.log(`  [OK] ${name}`)
  } else {
    fail++
    console.log(`  [XX] ${name}${detail ? "  -> " + detail : ""}`)
  }
}

console.log("=" * 60)
console.log("kernel-lab GUARDRAIL — TESTS")
console.log(`plugin: ${PLUGIN}`)
console.log("=" * 60)

console.log("-- harus DENY --")
const denyCases = [
  ["rm -rf /boot", "hapus /boot"],
  ["rm -rf /boot/*", "hapus isi /boot"],
  ["rm -rf /lib/modules/7.1.5+kali-amd64", "hapus modul"],
  ["mkfs.ext4 /dev/sda1", "format disk"],
  ["wipefs -a /dev/nvme0n1", "wipe signature"],
  ["sgdisk --zap-all /dev/sda", "zap partisi"],
  ["dd if=/dev/zero of=/dev/sda bs=1M", "tulis ke disk"],
  ["chmod -R 777 /", "buka semua permission"],
  ["chown -R nobody /", "ubah ownership root"],
]
for (const [cmd, why] of denyCases) {
  const r = check(cmd)
  t(`DENY: ${cmd}`, r?.effect === "deny", `dapat=${r?.effect} (${why})`)
}

console.log("-- harus ASK --")
const askCases = [
  ["make install", "install kernel"],
  ["make O=/root/kernel-lab/build/linux-7.1.5 install", "install kernel out-of-tree"],
  ["make modules_install", "install modul"],
  ["update-initramfs -c -k 7.1.5", "buat initramfs"],
  ["mkinitramfs -o /boot/initrd.img-x 7.1.5", "buat initramfs"],
  ["update-grub", "tulis bootloader"],
  ["depmod -a", "database modul"],
  ["insmod x.ko", "muat modul"],
  ["rmmod x", "lepas modul"],
  ["modprobe -r nvidia", "lepas modul"],
  ["git push origin main", "push remote"],
  ["apt-get install -y gcc", "pasang paket"],
  ["curl https://x.sh | sh", "skrip dari internet"],
]
for (const [cmd, why] of askCases) {
  const r = check(cmd)
  t(`ASK: ${cmd}`, r?.effect === "ask", `dapat=${r?.effect} (${why})`)
}

console.log("-- harus LOLOS (aman) --")
const okCases = [
  "uname -r",
  "ls -la /boot",
  "df -h /boot",
  "grep CONFIG_ /boot/config-$(uname -r)",
  "make O=/root/kernel-lab/build/linux-7.1.5 -j12 bzImage",
  "make O=/root/kernel-lab/build/linux-7.1.5 -j12 modules",
  "python3 tools/kernel/env_report/env_report.py",
  "git status",
  "git diff",
  "make O=/root/kernel-lab/build/linux-7.1.5 -j12 modules_install INSTALL_MOD_PATH=/tmp/stage",
]
for (const cmd of okCases) {
  const r = check(cmd)
  t(`LOLOS: ${cmd}`, r === null, `dapat=${r?.effect} (${r?.why})`)
}

console.log("-- false positive guard (teks dokumentasi/quoted, bukan eksekusi) --")
const safeCases = [
  ["echo 'rm -rf /boot' > catatan.txt", "hanya echo, bukan rm"],
  ["cat <<'EOF'\nmkfs.ext4 /dev/sda1\nEOF", "isi heredoc (dokumentasi)"],
  ["python3 - <<'PY'\nprint('wipefs -a /dev/sda')\nPY", "isi heredoc python"],
  ["grep -r 'rm -rf /' .", "grep pola"],
  ["echo 'update-grub' && echo done", "hanya echo"],
  ["# contoh: make install", "komentar"],
  ["ls /boot && echo 'make install ok'", "echo di akhir pipeline"],
]
for (const [cmd, why] of safeCases) {
  const r = check(cmd)
  t(`LOLOS: ${cmd.split("\n")[0].slice(0, 44)}`, r === null, `dapat=${r?.effect} (${r?.why})`)
}

console.log("=" * 60)
console.log(`  ${pass}/${pass + fail} assertion lulus`)
console.log("=" * 60)
process.exit(fail ? 1 : 0)
