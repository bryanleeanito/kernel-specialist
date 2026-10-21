#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests.py — module_inspect (kernel lab). Jalankan: python3 tests.py"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "module_inspect.py")
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


def run(args):
    p = subprocess.run([sys.executable, TOOL] + args, capture_output=True, text=True,
                       timeout=180)
    return p.returncode, p.stdout, p.stderr


def find_real_ko():
    for base in ("/lib/modules", "/root/kernel-lab/build"):
        if not os.path.isdir(base):
            continue
        for root, _d, files in os.walk(base):
            for f in files:
                if f.endswith(".ko"):
                    return os.path.join(root, f)
    return None


def main():
    rc, out, err = run(["--module", "/tmp/tidak-ada-xyz.ko", "--json"])
    check("modul tak ada → exit non-zero", rc != 0, f"rc={rc}")
    d = json.loads(out)
    check("modul tak ada → error field", bool(d[0].get("error")), str(d[0])[:120])

    rc, out, _ = run([])
    check("tanpa arg → exit 2", rc == 2, f"rc={rc}")

    ko = find_real_ko()
    if ko:
        rc, out, _ = run(["--module", ko, "--json"])
        rep = json.loads(out)[0]
        check("modul nyata → ada modinfo", bool(rep.get("modinfo")), ko)
        check("modul nyata → ada running kernel",
              bool(rep.get("running_kernel")), str(rep.get("running_kernel")))
        check("modul nyata → vermagic terbaca",
              bool(rep.get("modinfo", {}).get("vermagic")),
              str(rep.get("modinfo", {})))
        check("sha256 terisi", bool(rep.get("sha256")))
    else:
        results.append(("modul nyata tersedia untuk tes (SKIP — tidak ada .ko di sistem)",
                        True, ""))

    with tempfile.TemporaryDirectory() as tmp:
        mods = os.path.join(tmp, "mods")
        os.makedirs(mods, exist_ok=True)
        with open(os.path.join(mods, "dummy.ko"), "wb") as f:
            f.write(b"\x7fELFdummy")
        rc, out, _ = run(["--dir", mods, "--json"])
        check("--dir jalan tanpa crash", rc in (0, 1), f"rc={rc}")
        d = json.loads(out)
        check("--dir menemukan .ko", len(d) >= 1, str(d)[:150])

    failed = [r for r in results if not r[1]]
    print("=" * 60)
    print("module_inspect — TESTS")
    for name, ok, detail in results:
        print(f"  [{'OK' if ok else 'XX'}] {name}" + (f"  ({detail})" if not ok and detail else ""))
    print(f"  {len(results) - len(failed)}/{len(results)} lulus")
    print("=" * 60)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
