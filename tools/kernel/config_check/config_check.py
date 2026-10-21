#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""config_check.py — validasi config/fragment kernel terhadap source tree.

Read-only terhadap tree (tidak menulis .config).

Usage:
    python3 config_check.py --tree /root/kernel-lab/src/linux-7.1.5 \
        --fragment /root/kernel-lab/config/fragments/perf.conf
    python3 config_check.py --tree ... --config /boot/config-7.1.5+kali-amd64
"""
import argparse
import json
import os
import re
import sys

DEFAULT_TREE = os.environ.get("KERNEL_TREE", "/root/kernel-lab/src/linux-7.1.5")

# Opsi baseline yang wajib ada agar kernel bisa boot & berguna di workstation.
REQUIRED = [
    ("CONFIG_64BIT=y", "kernel 64-bit"),
    ("CONFIG_MODULES=y", "dukungan modul (wajib untuk driver tambahan)"),
    ("CONFIG_BLK_DEV_INITRD=y", "initramfs (wajib untuk boot)"),
    ("CONFIG_SYSFS=y", "sysfs (wajib untuk modul & udev)"),
    ("CONFIG_PROC_FS=y", "procfs (wajib)"),
    ("CONFIG_PRINTK=y", "printk (wajib untuk debug)"),
    ("CONFIG_FHANDLE=y", "fhandle (dipakai systemd)"),
    ("CONFIG_INOTIFY_USER=y", "inotify (dipakai desktop/apps)"),
]

# Kombinasi berisiko → warning (bukan error).
# CATATAN: CONFIG_DEBUG_INFO_BTF & CONFIG_RUST tidak boleh ada di sini —
# keduanya dicek terpisah (bagian 4) supaya warning hanya muncul kalau
# toolnya benar-benar tidak ada / versinya tidak cocok.
RISKY = [
    ("CONFIG_MODULE_SIG_FORCE=y", "CONFIG_MODULE_SIG_FORCE",
     "semua modul WAJIB signed — modul custom tidak bisa dimuat tanpa signing key"),
    ("CONFIG_LOCK_DOWN_KERNEL_FORCE=y", "CONFIG_LOCK_DOWN_KERNEL_FORCE",
     "kernel terkunci;-features kernel akan diblokir"),
    ("CONFIG_SYSTEM_TRUSTED_KEYS=\"\"", "CONFIG_SYSTEM_TRUSTED_KEYS",
     "tidak ada trusted key — Secure Boot tidak bisa diverifikasi"),
]


def parse_kconfig_symbols(tree):
    """Kumpulkan nama symbol yang ada di Kconfig* tree.

    PENTING (kernel >= 6.x/7.x): banyak simbol dideklarasikan dengan
    `menuconfig` (mis. HUGETLBFS, TCP_CONG_ADVANCED, KFENCE,
    TRANSPARENT_HUGEPAGE, GCC_PLUGINS). Kalau hanya dicari "config",
    resulted false-positive "symbol tidak dikenal".
    """
    syms = set()
    pattern = re.compile(r"^\s*(?:menu)?config\s+([A-Za-z0-9_]+)")
    for root, dirs, files in os.walk(tree):
        dirs[:] = [d for d in dirs if d not in (".git", "Documentation", "tools")]
        for fn in files:
            if fn.startswith("Kconfig"):
                path = os.path.join(root, fn)
                try:
                    with open(path, errors="ignore") as f:
                        for line in f:
                            m = pattern.match(line)
                            if m:
                                syms.add(m.group(1))
                except OSError:
                    continue
    return syms


def parse_config_file(path):
    """Baca file .config atau fragment → dict symbol -> value."""
    out = {}
    try:
        with open(path, errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                m = re.match(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$", line)
                if m:
                    out[m.group(1)] = m.group(2).strip().strip('"')
                elif line.startswith("# CONFIG_") and "is not set" in line:
                    out[line[2:].split(" ")[0]] = "n"
    except OSError as e:
        return None, str(e)
    return out, None


def is_kernel_tree(tree):
    return (os.path.isdir(tree)
            and os.path.exists(os.path.join(tree, "Kconfig"))
            and os.path.exists(os.path.join(tree, "Makefile")))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Validasi config/fragment kernel")
    ap.add_argument("--tree", default=DEFAULT_TREE)
    ap.add_argument("--config", help="file .config utuh untuk diperiksa")
    ap.add_argument("--fragment", action="append", default=[],
                    help="fragment .conf (boleh diulang)")
    ap.add_argument("--strict", action="store_true", help="warning ikut menggagalkan exit code")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    errors, warnings = [], []
    info = {}

    if not is_kernel_tree(args.tree):
        msg = f"bukan kernel tree yang valid: {args.tree} (butuh Kconfig + Makefile)"
        errors.append(msg)
        if args.json:
            print(json.dumps({"ok": False, "errors": errors, "warnings": warnings}, indent=2))
        else:
            print(f"[!] ERROR: {msg}")
        return 1

    syms = parse_kconfig_symbols(args.tree)
    info["tree_symbols"] = len(syms)

    merged = {}
    for path in [args.config] + args.fragment:
        if not path:
            continue
        if not os.path.exists(path):
            errors.append(f"file tidak ditemukan: {path}")
            continue
        data, err = parse_config_file(path)
        if err:
            errors.append(f"gagal baca {path}: {err}")
            continue
        info[os.path.basename(path)] = len(data)
        merged.update(data)

    # 1) symbol di fragment harus dikenal tree
    for path in args.fragment:
        data, _ = parse_config_file(path)
        if not data:
            continue
        unknown = [s for s in data if s.replace("CONFIG_", "") not in syms
                   and s not in syms]
        for s in sorted(unknown):
            warnings.append(f"{os.path.basename(path)}: symbol '{s}' tidak dikenal di tree "
                            f"(kemungkinan salah nama / opsi sudah dihapus)")

    # 2) baseline wajib
    for want, why in REQUIRED:
        val = merged.get(want.replace("=y", ""))
        if val is None:
            warnings.append(f"baseline hilang: {want} ({why})")
        elif val != "y":
            warnings.append(f"baseline non-aktif: {want} = {val!r} ({why})")

    # 3) kombinasi berisiko
    for want, sym, why in RISKY:
        val = merged.get(sym)
        if val in ("y", "") and want.endswith('=""'):
            warnings.append(f"{sym}: {why}")
        elif val == "y":
            warnings.append(f"{sym}=y: {why}")

    # 4) env vs config: toolchain wajib untuk opsi tertentu
    if merged.get("CONFIG_RUST") == "y":
        import shutil
        if not shutil.which("rustc"):
            errors.append("CONFIG_RUST=y tapi `rustc` tidak ada di PATH")
        else:
            import subprocess
            try:
                rv = subprocess.run(["rustc", "--version"], capture_output=True,
                                    text=True, timeout=15).stdout.strip()
            except Exception:  # noqa: BLE001
                rv = "?"
            info["rustc"] = rv
            cfg_rustc = merged.get("CONFIG_RUSTC_VERSION_TEXT")
            if cfg_rustc:
                want = re.search(r"rustc (\d+\.\d+\.\d+)", cfg_rustc)
                have = re.search(r"rustc (\d+\.\d+\.\d+)", rv)
                if want and have and want.group(1) != have.group(1):
                    errors.append(f"versi rustc tidak cocok: config butuh {want.group(1)}, "
                                  f"terpasang {have.group(1)}")
    if merged.get("CONFIG_DEBUG_INFO_BTF") == "y":
        import shutil
        if not shutil.which("pahole"):
            errors.append("CONFIG_DEBUG_INFO_BTF=y tapi `pahole` (dwarves) tidak ada di PATH")

    ok = not errors and (not warnings or not args.strict)
    if args.json:
        print(json.dumps({"ok": ok, "errors": errors, "warnings": warnings, "info": info},
                         indent=2, ensure_ascii=False))
    else:
        print("=" * 68)
        print("KERNEL CONFIG CHECK")
        print(f"tree     : {args.tree}")
        for k, v in info.items():
            print(f"  {k:16}: {v}")
        print("-" * 68)
        if errors:
            print("ERRORS:")
            for e in errors:
                print(f"  [X] {e}")
        if warnings:
            print("WARNINGS:")
            for w in warnings:
                print(f"  [!] {w}")
        if not errors and not warnings:
            print("  [OK] tidak ada temuan")
        print("=" * 68)
        print(f"RESULT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
