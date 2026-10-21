#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kbuild.py — wrapper aman untuk build kernel (kbuild) + fragment config.

Default: TIDAK pernah menyentuh /boot, /lib/modules, atau partisi.
`--install` ke root sistem harus lewat flag eksplisit + staging dir.

Usage:
    python3 kbuild.py --tree /root/kernel-lab/src/linux-7.1.5 \
        --out /root/kernel-lab/build/linux-7.1.5 \
        --base-config /boot/config-$(uname -r) \
        --fragment /root/kernel-lab/config/fragments/perf.conf \
        --target bzImage --jobs 12

    python3 kbuild.py --tree ... --out ... --target modules --jobs 12
    python3 kbuild.py --tree ... --out ... --dry-run
"""
import argparse
import os
import shlex
import shutil
import subprocess
import sys
import time

DEFAULT_TREE = os.environ.get("KERNEL_TREE", "/root/kernel-lab/src/linux-7.1.5")
DEFAULT_OUT = os.environ.get("KERNEL_BUILD", "/root/kernel-lab/build/linux-7.1.5")
LOG_DIR = os.environ.get("KERNEL_LOG_DIR", "/root/kernel-lab/logs")

DESTRUCTIVE_NOTE = ("`make install` menulis ke /boot dan /lib/modules — "
                    "berburu merusak dual-boot. Default tool ini: STAGING ONLY.")


def run(cmd, cwd=None, log=None, timeout=None):
    """Jalankan perintah; stream ke log; kembalikan rc."""
    printable = cmd if isinstance(cmd, str) else " ".join(shlex.quote(c) for c in cmd)
    if log:
        with open(log, "a") as lf:
            lf.write(f"\n$ {printable}\n")
            lf.flush()
            p = subprocess.run(cmd, cwd=cwd, stdout=lf, stderr=subprocess.STDOUT,
                               timeout=timeout)
            return p.returncode
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          timeout=timeout).returncode


def is_kernel_tree(tree):
    return (os.path.isdir(tree)
            and os.path.exists(os.path.join(tree, "Kconfig"))
            and os.path.exists(os.path.join(tree, "Makefile")))


def tree_version(tree):
    ver = {}
    try:
        with open(os.path.join(tree, "Makefile")) as f:
            for line in f:
                for k in ("VERSION", "PATCHLEVEL", "SUBLEVEL", "EXTRAVERSION"):
                    if line.startswith(k + " ="):
                        ver[k.lower()] = line.split("=", 1)[1].strip()
    except OSError:
        pass
    if ver:
        return f"{ver.get('version','?')}.{ver.get('sublevel','?')}{ver.get('extraversion','')}"
    return "unknown"


def merge_fragments(tree, out, base_config, fragments, log):
    """Siapkan .config di out/: base config + fragments via merge_config.sh."""
    os.makedirs(out, exist_ok=True)
    cfg = os.path.join(out, ".config")
    if base_config:
        if not os.path.exists(base_config):
            raise SystemExit(f"[X] base config tidak ada: {base_config}")
        shutil.copy2(base_config, cfg)
    elif not os.path.exists(cfg):
        raise SystemExit("[X] tidak ada base config dan out/.config belum ada")

    for frag in fragments:
        if not os.path.exists(frag):
            raise SystemExit(f"[X] fragment tidak ada: {frag}")
    if fragments:
        merge = os.path.join(tree, "scripts", "kconfig", "merge_config.sh")
        if not os.path.exists(merge):
            raise SystemExit("[X] scripts/kconfig/merge_config.sh tidak ada di tree")
        rc = run(["bash", merge, "-O", out, "-m", "-n", cfg] + fragments, cwd=tree, log=log)
        if rc != 0:
            raise SystemExit(f"[X] merge_config.sh gagal (rc={rc}) — cek log")
    # olddefconfig: terapkan fragmen, tanpa interaksi
    rc = run(["make", f"O={out}", "olddefconfig"], cwd=tree, log=log)
    if rc != 0:
        raise SystemExit(f"[X] make olddefconfig gagal (rc={rc}) — cek log")
    return cfg


def verify(out, target):
    arts = {}
    for name, rel in (("bzImage", "arch/x86/boot/bzImage"),
                      ("vmlinux", "vmlinux"),
                      ("System.map", "System.map"),
                      (".config", ".config")):
        p = os.path.join(out, rel)
        arts[name] = os.path.exists(p)
    ko = 0
    for _r, _d, files in os.walk(out):
        ko += sum(1 for f in files if f.endswith(".ko"))
    arts["ko_count"] = ko
    ok = True
    if target in ("bzImage", "all") and not arts["bzImage"]:
        ok = False
    if target in ("modules", "all") and ko == 0:
        ok = False
    return arts, ok


def main(argv=None):
    ap = argparse.ArgumentParser(description="Wrapper build kernel (aman, staging-only)")
    ap.add_argument("--tree", default=DEFAULT_TREE)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--base-config", help="file .config dasar (mis. /boot/config-$(uname -r))")
    ap.add_argument("--fragment", action="append", default=[], help="fragment .conf")
    ap.add_argument("--target", default="bzImage",
                    choices=["bzImage", "modules", "all", "prepare", "defconfig"])
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--ccache", action="store_true", help="aktifkan ccache")
    ap.add_argument("--llvm", action="store_true", help="LLVM=1 (clang + lld)")
    ap.add_argument("--dry-run", action="store_true", help="tampilkan perintah, jangan jalankan")
    ap.add_argument("--install", action="store_true",
                    help=f"install ke sistem (berbahaya). {DESTRUCTIVE_NOTE}")
    ap.add_argument("--install-to", default="/", help="tujuan install (default: /)")
    args = ap.parse_args(argv)

    if not is_kernel_tree(args.tree):
        print(f"[X] bukan kernel tree: {args.tree}", file=sys.stderr)
        return 1

    os.makedirs(LOG_DIR, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    log = os.path.join(LOG_DIR, f"kbuild-{stamp}.log")
    ver = tree_version(args.tree)

    cmds = []
    if args.base_config or args.fragment:
        cmds.append(["make", f"O={args.out}", "olddefconfig"])
    target_cmd = ["make", f"O={args.out}", f"-j{args.jobs}"]
    if args.ccache:
        # kbuild tidak punya flag ccache; cara benar: bungkus compiler target.
        # JANGAN set HOSTCC="ccache gcc" — scripts/Makefile.host memakai
        # `-Clinker=$(HOSTCC)` untuk host-rust, dan rustc akan salah parse
        # "ccache gcc" sebagai dua input file (error: multiple input filenames).
        target_cmd.append("CC=ccache gcc")
    if args.llvm:
        target_cmd.append("LLVM=1")
    if args.target == "defconfig":
        cmds.append(["make", f"O={args.out}", "defconfig"])
    else:
        cmds.append(target_cmd + [args.target])
    if args.install:
        if args.install_to == "/":
            cmds.append(["make", f"O={args.out}", "modules_install"])
            cmds.append(["make", f"O={args.out}", "install"])
        else:
            cmds.append(["make", f"O={args.out}",
                         f"INSTALL_MOD_PATH={args.install_to}", "modules_install"])

    print("=" * 68)
    print("KBUILD")
    print(f"  tree    : {args.tree}  (v{ver})")
    print(f"  out     : {args.out}")
    print(f"  target  : {args.target}   jobs: {args.jobs}")
    print(f"  log     : {log}")
    if args.install:
        print(f"  [!] INSTALL MODE → {args.install_to}  ({DESTRUCTIVE_NOTE})")
    print("=" * 68)
    for c in cmds:
        print("  $ " + " ".join(c))

    if args.dry_run:
        print("\n[dry-run] tidak ada yang dijalankan.")
        return 0

    t0 = time.time()
    rc = 0
    for c in cmds:
        if c[1] == "olddefconfig" and (args.base_config or args.fragment):
            merge_fragments(args.tree, args.out, args.base_config, args.fragment, log)
            continue
        rc = run(c, cwd=args.tree, log=log)
        if rc != 0:
            break
    dt = time.time() - t0

    print("-" * 68)
    if rc != 0:
        print(f"[X] build GAGAL (rc={rc}) setelah {dt:.1f}s → tail log:")
        try:
            with open(log) as f:
                lines = f.readlines()
            print("".join(lines[-40:]))
        except OSError:
            pass
        return rc

    arts, ok = verify(args.out, args.target)
    for k, v in arts.items():
        print(f"  {k:12}: {v if not isinstance(v, bool) else ('OK' if v else 'MISSING')}")
    print(f"[OK] build selesai dalam {dt:.1f}s → {log}")
    if args.install:
        print(f"[!] sudah di-install ke {args.install_to} — "
              f"lalu jalankan: update-initramfs -c -k <ver> && update-grub")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
