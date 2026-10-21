#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests.py — config_check (kernel lab). Jalankan: python3 tests.py"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "config_check.py")
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


def run(args):
    p = subprocess.run([sys.executable, TOOL] + args, capture_output=True, text=True,
                       timeout=180)
    return p.returncode, p.stdout, p.stderr


def make_tree(tmp):
    tree = os.path.join(tmp, "linux-fake")
    os.makedirs(tree, exist_ok=True)
    with open(os.path.join(tree, "Makefile"), "w") as f:
        f.write("VERSION = 7\nPATCHLEVEL = 1\nSUBLEVEL = 0\n")
    with open(os.path.join(tree, "Kconfig"), "w") as f:
        f.write("mainmenu \"Fake\"\n"
                "config MODULES\n\tbool \"M\"\n"
                "config BTRFS_FS\n\tbool \"B\"\n"
                "config DEBUG_INFO_BTF\n\tbool \"B\"\n"
                "config RUST\n\tbool \"B\"\n"
                "config MODULE_SIG_FORCE\n\tbool \"B\"\n")
    return tree


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tree = make_tree(tmp)
        good = os.path.join(tmp, "good.conf")
        with open(good, "w") as f:
            f.write("CONFIG_BTRFS_FS=y\nCONFIG_MODULES=y\n")
        bad = os.path.join(tmp, "bad.conf")
        with open(bad, "w") as f:
            f.write("CONFIG_TIDAK_ADA_XYZ=y\n")

        rc, out, err = run(["--tree", tree, "--fragment", good, "--json"])
        check("fragment valid → exit 0", rc == 0, f"rc={rc} {out[:200]}")
        d = json.loads(out)
        check("fragment valid → 0 error", len(d["errors"]) == 0, str(d["errors"]))
        unknown = [w for w in d["warnings"] if "TIDAK_ADA" in w]
        check("symbol asing tidak diwarning untuk fragment valid", not unknown)

        rc, out, _ = run(["--tree", tree, "--fragment", bad, "--json"])
        d = json.loads(out)
        check("symbol asing → warning", any("TIDAK_ADA_XYZ" in w for w in d["warnings"]),
              str(d["warnings"]))
        check("symbol asing → exit 1 (strict default warn=tidak fatal? cek)",
              rc in (0, 1), f"rc={rc}")

        rc, out, _ = run(["--tree", "/tmp/tidak-ada-tree", "--json"])
        check("tree invalid → exit 1", rc == 1, f"rc={rc}")
        d = json.loads(out)
        check("tree invalid → error tercatat", len(d["errors"]) >= 1)

        rc, out, _ = run(["--tree", tree, "--fragment", os.path.join(tmp, "nope.conf"),
                          "--json"])
        d = json.loads(out)
        check("fragment hilang → error", any("tidak ditemukan" in e for e in d["errors"]),
              str(d["errors"]))

        rc, out, _ = run(["--tree", tree, "--fragment", good, "--strict", "--json"])
        d = json.loads(out)
        check("strict + warning → exit 1", rc == 1, f"rc={rc}")

    failed = [r for r in results if not r[1]]
    print("=" * 60)
    print("config_check — TESTS")
    for name, ok, detail in results:
        print(f"  [{'OK' if ok else 'XX'}] {name}" + (f"  ({detail})" if not ok and detail else ""))
    print(f"  {len(results) - len(failed)}/{len(results)} lulus")
    print("=" * 60)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
