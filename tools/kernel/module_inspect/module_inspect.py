#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""module_inspect.py — inspeksi modul kernel (.ko): vermagic, signature, dependensi.

Read-only terhadap modul. Tidak memuat/membongkar modul.

Usage:
    python3 module_inspect.py --module /path/mod.ko
    python3 module_inspect.py --dir /root/kernel-lab/build --json
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

FIELDS = ("filename", "name", "vermagic", "depends", "license", "srcversion",
          "sig_id", "signer", "sig_key", "parm")


def run(cmd, timeout=30):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:  # noqa: BLE001
        return 127, f"error: {e}"


def modinfo(path, fields=FIELDS):
    if not os.path.exists(path):
        return None, f"modul tidak ditemukan: {path}"
    info = {}
    for f in fields:
        rc, o = run(["modinfo", "-F", f, path])
        if rc == 0 and o.strip():
            info[f] = o.strip()
    return info, None


def running_vermagic():
    rc, o = run(["modinfo", "-F", "vermagic", "/lib/modules/%s" %
                 os.uname().release])
    return o.strip()


def sha256(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def unresolved_symbols(ko, symvers=None):
    """Symbol undefined di modul yang tidak ada di Module.symvers (kalau ada)."""
    rc, o = run(["nm", "-u", ko])
    if rc != 0:
        return None, "nm tidak tersedia"
    syms = []
    for line in o.splitlines():
        parts = line.split()
        if parts:
            syms.append(parts[-1])
    if not symvers or not os.path.exists(symvers):
        return syms, None
    known = set()
    try:
        with open(symvers) as f:
            for line in f:
                p = line.split()
                if len(p) >= 2:
                    known.add(p[1])
    except OSError:
        return syms, None
    missing = [s for s in syms if s not in known and not s.startswith("__this_module")]
    return syms, missing


def inspect(path, symvers=None):
    info, err = modinfo(path)
    if err:
        return {"path": path, "error": err}
    st = os.stat(path)
    rep = {
        "path": path,
        "size": st.st_size,
        "sha256": sha256(path),
        "modinfo": info,
        "running_kernel": os.uname().release,
        "running_vermagic": running_vermagic(),
        "warnings": [],
        "errors": [],
    }
    vm = info.get("vermagic", "")
    rvm = rep["running_vermagic"]
    if vm and rvm and vm != rvm:
        rep["errors"].append(
            f"vermagic tidak cocok — modul: '{vm}' | kernel running: '{rvm}' "
            f"→ modul TIDAK bisa dimuat ke kernel yang sedang jalan")
    if not info.get("signer") and info.get("sig_id") in (None, ""):
        rep["warnings"].append("modul tidak signed (tanpa signature) — "
                               "hanya bisa dimuat jika CONFIG_MODULE_SIG_FORCE tidak aktif")
    if info.get("sig_id") == "(null)":
        rep["warnings"].append("signature dibuang/tidak ditandatangani")
    syms, missing = unresolved_symbols(path, symvers)
    if syms is not None:
        rep["undefined_symbols"] = len(syms)
    if missing:
        rep["errors"].append(f"{len(missing)} symbol undefined tidak ada di Module.symvers: "
                             + ", ".join(missing[:10]) + (" ..." if len(missing) > 10 else ""))
    rc, o = run(["modprobe", "--dry-run", "--show-depends", "-S", os.path.basename(path)])
    if rc == 0 and o.strip():
        rep["modprobe_depends"] = o.strip().splitlines()[0]
    return rep


def find_modules(d):
    out = []
    for root, _dirs, files in os.walk(d):
        for f in files:
            if f.endswith(".ko"):
                out.append(os.path.join(root, f))
    return sorted(out)


def render(rep):
    L = ["=" * 68]
    if rep.get("error"):
        L.append(f"[!] {rep['error']}")
        return "\n".join(L)
    L.append(f"MODULE : {rep['path']}")
    L.append(f"size   : {rep['size']:,} bytes")
    L.append(f"sha256 : {rep.get('sha256')}")
    mi = rep.get("modinfo", {})
    for k in ("name", "vermagic", "license", "depends", "srcversion",
              "sig_id", "signer", "parm"):
        if mi.get(k):
            L.append(f"{k:8}: {mi[k]}")
    L.append("-" * 68)
    L.append(f"kernel running : {rep['running_kernel']}")
    L.append(f"vermagic running: {rep['running_vermagic']}")
    if "undefined_symbols" in rep:
        L.append(f"undefined syms  : {rep['undefined_symbols']}")
    if rep.get("modprobe_depends"):
        L.append(f"modprobe deps   : {rep['modprobe_depends']}")
    for w in rep.get("warnings", []):
        L.append(f"  [!] {w}")
    for e in rep.get("errors", []):
        L.append(f"  [X] {e}")
    L.append("=" * 68)
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Inspeksi modul kernel")
    ap.add_argument("--module", help="path file .ko")
    ap.add_argument("--dir", help="direktori yang dicari .ko")
    ap.add_argument("--symvers", help="Module.symvers untuk cek symbol")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    targets = []
    if args.module:
        targets.append(args.module)
    if args.dir:
        targets.extend(find_modules(args.dir))
    if not targets:
        print("[!] gunakan --module PATH atau --dir PATH", file=sys.stderr)
        return 2

    reports = [inspect(t, args.symvers) for t in targets]
    if args.json:
        print(json.dumps(reports, indent=2, ensure_ascii=False))
    else:
        for rep in reports:
            print(render(rep))
    bad = sum(1 for r in reports if r.get("errors") or r.get("error"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
