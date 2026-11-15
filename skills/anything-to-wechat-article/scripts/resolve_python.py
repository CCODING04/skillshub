#!/usr/bin/env python3
"""Resolve the Python interpreter for this skill (first-use rule).

User rule 2026-11-15:
- A remembered path wins; the Agent asked for it once and stored it here.
- If the OS has a usable default python/python3 -> use it, do NOT ask.
- If uv or another Python environment manager is installed -> do NOT ask.
- Only when none of the above is true must the Agent ask the user for the
  interpreter path, then run `--set <path>` to remember it.

Config lives in the user's home directory, never inside the skill repo/package.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

CONFIG = Path.home() / ".skillshub" / "python.json"
MANAGERS = ["uv", "conda", "mamba", "micromamba", "poetry", "pipenv",
            "hatch", "pdm", "pyenv", "rye"]


def usable(exe):
    """Return the real interpreter path, or None for stubs / broken launchers."""
    if not exe:
        return None
    try:
        r = subprocess.run([exe, "-c", "import sys; print(sys.executable)"],
                           capture_output=True, text=True, timeout=8)
        if r.returncode != 0:
            return None
        path = r.stdout.strip()
        if not path or "WindowsApps" in path or "Microsoft/Store" in path.replace("\\", "/"):
            return None
        return path
    except Exception:
        return None


def remembered():
    if not CONFIG.exists():
        return None
    try:
        p = json.loads(CONFIG.read_text(encoding="utf-8")).get("python_path")
        return p if p and usable(p) else None
    except Exception:
        return None


def detect():
    p = remembered()
    if p:
        return {"python_path": p, "source": "remembered", "manager": None,
                "needs_ask": False, "config_path": str(CONFIG)}
    found = [m for m in MANAGERS if shutil.which(m)]
    if found:
        candidate = usable(shutil.which("python3")) or usable(shutil.which("python")) or sys.executable
        return {"python_path": candidate, "source": "manager", "manager": found[0],
                "needs_ask": False, "config_path": str(CONFIG),
                "note": "环境管理器已安装，按用户规则不询问；可用其默认解释器或 " + found[0] + " 运行"}
    for name in ("python3", "python"):
        p = usable(shutil.which(name))
        if p:
            return {"python_path": p, "source": "system", "manager": None,
                    "needs_ask": False, "config_path": str(CONFIG)}
    return {"python_path": None, "source": "none", "manager": None,
            "needs_ask": True, "config_path": str(CONFIG),
            "note": "未找到可用默认解释器，也未检测到环境管理器：请在 S0 主动询问用户 Python 运行地址，然后用 --set 记住"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="print full detection result")
    ap.add_argument("--print", action="store_true", help="print only the interpreter path")
    ap.add_argument("--set", default="", metavar="PATH", help="remember an interpreter path")
    ap.add_argument("--clear", action="store_true", help="forget the remembered path")
    args = ap.parse_args()
    if args.set:
        p = usable(args.set)
        if not p:
            print(json.dumps({"ok": False, "error": "not a usable python", "path": args.set},
                             ensure_ascii=False), file=sys.stderr)
            return 1
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        CONFIG.write_text(json.dumps({"python_path": p}, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
        print(json.dumps({"ok": True, "python_path": p, "saved_to": str(CONFIG)},
                         ensure_ascii=False))
        return 0
    if args.clear:
        CONFIG.unlink(missing_ok=True)
        print(json.dumps({"ok": True, "cleared": True}, ensure_ascii=False))
        return 0
    r = detect()
    if args.print:
        print(r["python_path"] or "")
    else:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
