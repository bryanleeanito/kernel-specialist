#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests.py — kbuild (kernel lab). Jalankan: python3 tests.py

Tidak melakukan build sungguhan (memakan waktu/CPU); hanya menguji
jalur validasi, dry-run, dan penanganan error.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "kbuild.py")
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
        f.write("VERSION = 7\nPATCHLEVEL = 1\nSUBLEVEL = 0\nEXTRAVERSION =\n")
    with open(os.path.join(tree, "Kconfig"), "w") as f:
        f.write("mainmenu \"Fake\"\n")
    return tree


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tree = make_tree(tmp)
        out = os.path.join(tmp, "build")

        rc, o, e = run(["--tree", "/tmp/tree-hilang", "--out", out, "--dry-run"])
        check("tree invalid → exit 1", rc == 1, f"rc={rc} {e[:120]}")

        rc, o, e = run(["--tree", tree, "--out", out, "--target", "bzImage",
                        "--dry-run", "--jobs", "4"])
        check("dry-run → exit 0", rc == 0, f"rc={rc} {e[:200]}")
        check("dry-run tidak menjalankan make", "dry-run" in o.lower())
        check("dry-run menampilkan perintah make", "make" in o)

        rc, o, e = run(["--tree", tree, "--out", out, "--target", "modules",
                        "--dry-run", "--fragment", "/tmp/frag-hilang.conf"])
        check("fragment hilang + dry-run tetap 0", rc == 0, f"rc={rc}")

        rc, o, e = run(["--tree", tree, "--out", out, "--target", "bzImage",
                        "--base-config", "/tmp/base-hilang.conf"])
        check("base config hilang → exit non-zero", rc != 0, f"rc={rc}")

        rc, o, e = run(["--tree", tree, "--out", out, "--target", "bzImage",
                        "--dry-run", "--llvm", "--ccache"])
        check("flag llvm+ccache diterima", rc == 0, f"rc={rc}")
        check("llvm dicetak di dry-run", "LLVM=1" in o, o[:200])
        check("ccache dicetak di dry-run", "CC=ccache gcc" in o)

    failed = [r for r in results if not r[1]]
    print("=" * 60)
    print("kbuild — TESTS")
    for name, ok, detail in results:
        print(f"  [{'OK' if ok else 'XX'}] {name}" + (f"  ({detail})" if not ok and detail else ""))
    print(f"  {len(results) - len(failed)}/{len(results)} lulus")
    print("=" * 60)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
