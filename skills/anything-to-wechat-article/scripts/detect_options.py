#!/usr/bin/env python3
"""Detect objective environment data before asking the user to decide (Step 0).

Standard library only. Prints a JSON report; optionally writes it with --out.
This script never decides anything - it only supplies evidence.
"""
import argparse
import importlib.util
import json
import os
import shutil
import subprocess


def curl_code(url, proxy=None, timeout=8):
    cmd = ["curl", "-sS", "-o", os.devnull, "-m", str(timeout), "-w", "%{http_code}"]
    if proxy:
        cmd += ["-x", proxy]
    cmd.append(url)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        out = r.stdout.strip()
        return out[-3:] if out else (r.stderr.strip()[:80] or "ERR")
    except Exception as exc:
        return "ERR " + str(exc)[:60]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proxy", default=os.environ.get("CUSTOM_PROXY", ""),
                    help="optional custom proxy to test; set CUSTOM_PROXY env var or pass --proxy")
    ap.add_argument("--hosts", default="video.twimg.com,huggingface.co,api.fxtwitter.com",
                    help="comma separated hosts to probe")
    ap.add_argument("--model-root", default=os.environ.get("ASR_MODEL_ROOT", ""),
                    help="directory containing local model weights")
    ap.add_argument("--media-json", default="",
                    help="optional fxtwitter-style JSON with media.videos[].formats")
    ap.add_argument("--out", default="", help="write report to this path")
    args = ap.parse_args()

    tools = {name: (shutil.which(name) or "") for name in
             ["ffmpeg", "ffprobe", "curl", "node", "python", "yt-dlp"]}
    browsers = [p for p in [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        shutil.which("google-chrome") or "",
        shutil.which("chromium") or "",
    ] if p and os.path.exists(p)]

    proxies = {}
    for host in [h.strip() for h in args.hosts.split(",") if h.strip()]:
        url = "https://" + host + "/"
        proxies[host] = {"default": curl_code(url), "custom": curl_code(url, args.proxy)}

    qualities = []
    if args.media_json and os.path.exists(args.media_json):
        with open(args.media_json, encoding="utf-8") as f:
            data = json.load(f)
        for v in data.get("tweet", {}).get("media", {}).get("videos", []):
            for fmt in v.get("formats", []):
                if fmt.get("container") == "mp4":
                    res = next((p for p in fmt["url"].split("/")
                                if "x" in p and p[0].isdigit()), "?")
                    qualities.append({"id": res, "bitrate": fmt.get("bitrate"), "url": fmt["url"]})

    models = []
    root = args.model_root
    if root and os.path.isdir(root):
        for name in sorted(os.listdir(root)):
            d = os.path.join(root, name)
            if not os.path.isdir(d):
                continue
            safes = [f for f in os.listdir(d) if f.endswith(".safetensors")]
            has_cfg = os.path.exists(os.path.join(d, "config.json"))
            models.append({"name": name, "ready": has_cfg and bool(safes),
                           "safetensors": len(safes),
                           "size_gb": round(sum(os.path.getsize(os.path.join(d, f)) for f in safes) / 1024 ** 3, 2)})

    try:
        import torch
        gpu = {"torch": torch.__version__, "cuda": torch.cuda.is_available(),
               "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}
    except Exception as exc:
        gpu = {"torch": None, "error": str(exc)[:80]}

    backends = {
        "platform-transcript": {"available": True, "note": "由 Agent 调用平台工具"},
        "qwen-local": {"available": importlib.util.find_spec("qwen_asr") is not None and
                       any(m["ready"] and "ASR" in m["name"] for m in models)},
        "funasr": {"available": importlib.util.find_spec("funasr") is not None},
        "faster-whisper": {"available": importlib.util.find_spec("faster_whisper") is not None},
    }

    report = {
        "tools": tools,
        "headless_browsers": browsers,
        "gpu": gpu,
        "proxy_reachability": proxies,
        "custom_proxy": args.proxy,
        "video_qualities": qualities,
        "local_models": models,
        "stt_backends": backends,
        "note": "客观数据，不构成决定。涉及口径、画质、代理、后端与成本的选择须由用户拍板。",
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print("WROTE", args.out)


if __name__ == "__main__":
    main()
