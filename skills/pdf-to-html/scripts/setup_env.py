#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Preflight & initialize environment: project Python + MinerU API key.

Checks (in order) and optionally creates what is missing:
  * project default Python  — .env.json['python'] (valid path) or auto-detected
  * MinerU API key          — MINERU_API_TOKEN env / .env.json['mineru'] / ~/.mineru/token

SECURITY: this script NEVER prints the key value — only presence, source and length.

Usage:
  python setup_env.py --workdir .                 # check only (JSON report)
  python setup_env.py --workdir . --init          # create/fix config, detect python
  python setup_env.py --workdir . --set-key YOUR_KEY   # store key into .env.json
  python setup_env.py --workdir . --key-from-env      # copy MINERU_API_TOKEN into .env.json
  python setup_env.py --workdir . --set-python /path/to/python
Exit code 0 = ready, 2 = missing key (needs user action), 1 = other error.
"""
import argparse, json, os, re, shutil, sys

ENV_NAME = ".env.json"


def strip_trailing_commas(s):
    return re.sub(r",\s*([}\]])", r"\1", s)


def read_env(path):
    if not os.path.exists(path):
        return {}
    raw = open(path, encoding="utf-8").read().strip()
    if not raw:
        return {}
    d = json.loads(strip_trailing_commas(raw))
    if not isinstance(d, dict):
        raise ValueError(".env.json must be a JSON object")
    return d


def write_env(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        f.write("\n")
    os.replace(tmp, path)


def looks_like_real_python(path):
    if not path or not os.path.exists(path):
        return False
    try:
        import subprocess
        r = subprocess.run([path, "-c", "import sys;sys.stdout.write(sys.executable)"],
                           capture_output=True, text=True, timeout=10)
        #商店占位符会返回非 0 或输出提示信息；真 python 正常输出路径
        return r.returncode == 0 and os.path.exists(r.stdout.strip())
    except Exception:
        return False


def detect_python():
    """Find a usable Python without trusting PATH aliases blindly."""
    candidates = [
        os.environ.get("PYTHON"),
        sys.executable,
        shutil.which("python3"),
        shutil.which("python"),
    ]
    seen = set()
    for c in candidates:
        if not c or c in seen:
            continue
        seen.add(c)
        if looks_like_real_python(c):
            return os.path.abspath(c)
    return None


def find_key_source(workdir, env):
    """Return (source, length) without exposing the key itself."""
    tok = os.environ.get("MINERU_API_TOKEN")
    if tok:
        return ("env:MINERU_API_TOKEN", len(tok))
    if env.get("mineru"):
        return (ENV_NAME + ":mineru", len(str(env["mineru"])))
    p = os.path.expanduser("~/.mineru/token")
    if os.path.exists(p):
        txt = open(p, encoding="utf-8").read().strip()
        if txt:
            return ("~/.mineru/token", len(txt))
    return (None, 0)


def check(workdir):
    env = read_env(os.path.join(workdir, ENV_NAME))
    cfg_py = env.get("python")
    py_ok = looks_like_real_python(cfg_py)
    detected = None if py_ok else detect_python()
    key_src, key_len = find_key_source(workdir, env)
    return env, {
        "python": {
            "configured": bool(cfg_py),
            "valid": py_ok,
            "path": cfg_py if cfg_py else None,
            "detected": detected,
            "ready": py_ok or bool(detected),
        },
        "mineru_key": {
            "ready": bool(key_src),
            "source": key_src,
            "length": key_len,
        },
        "ready": (py_ok or bool(detected)) and bool(key_src),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workdir", default=".", help="project root containing .env.json")
    ap.add_argument("--init", action="store_true", help="create/fix .env.json, detect python")
    ap.add_argument("--set-key", default=None, help="store MinerU key into .env.json (never echoed)")
    ap.add_argument("--key-from-env", action="store_true", help="copy MINERU_API_TOKEN into .env.json")
    ap.add_argument("--set-python", default=None, help="explicit python path to store")
    args = ap.parse_args()

    wd = os.path.abspath(args.workdir)
    env_path = os.path.join(wd, ENV_NAME)
    os.makedirs(wd, exist_ok=True)
    env = read_env(env_path)

    # --- write actions ---
    if args.set_python:
        if not looks_like_real_python(args.set_python):
            sys.exit("ERROR: not a usable Python: %s" % args.set_python)
        env["python"] = os.path.abspath(args.set_python)
        write_env(env_path, env)
        print("Wrote python path to %s" % ENV_NAME)

    key_to_store = args.set_key
    if args.key_from_env:
        key_to_store = os.environ.get("MINERU_API_TOKEN")
        if not key_to_store:
            sys.exit("ERROR: MINERU_API_TOKEN is not set")
    if key_to_store:
        env["mineru"] = key_to_store.strip()
        write_env(env_path, env)
        print("Wrote MinerU key to %s (value not shown)" % ENV_NAME)

    if args.init:
        if not looks_like_real_python(env.get("python")):
            found = detect_python()
            if found:
                env["python"] = found
                write_env(env_path, env)
                print("Auto-detected and stored project python (value not shown).")
            else:
                print("WARN: no usable Python detected; pass --set-python /path/to/python")

    _, report = check(wd)
    print("\n=== ENVIRONMENT PREFLIGHT ===")
    print("project Python : %s" % ("READY" if report["python"]["ready"] else "MISSING"))
    if report["python"]["configured"] and report["python"]["valid"]:
        print("  source: .env.json:python")
    elif report["python"]["detected"]:
        print("  detected (not yet stored): pass --init to save it")
    print("MinerU API key : %s" % ("READY" if report["mineru_key"]["ready"] else "MISSING"))
    if report["mineru_key"]["ready"]:
        print("  source: %s, length=%d" % (report["mineru_key"]["source"],
                                          report["mineru_key"]["length"]))
    print(json.dumps({"ready": report["ready"]}))

    if not report["mineru_key"]["ready"]:
        print("\nNEXT ACTION (key cannot be auto-generated):")
        print("  1) Get a token at https://mineru.net")
        print("  2) Either: export MINERU_API_TOKEN=<your_token>")
        print("     Or:     python setup_env.py --workdir <dir> --set-key <your_token>")
        sys.exit(2)
    if not report["ready"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
