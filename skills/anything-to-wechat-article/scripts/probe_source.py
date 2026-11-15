#!/usr/bin/env python3
"""Read-only source probe for S0-A feasibility research.

Observes a URL or local file WITHOUT downloading the body, logging in, or
spending credits. Produces probe.json as objective evidence. It never decides
anything: network research and the final choice remain with the Agent / user.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

MAGIC = [
    (b"%PDF", "pdf"), (b"PK\x03\x04", "zip-based (docx/pptx/xlsx)"),
    (b"RIFF", "wav/avi"), (b"ID3", "mp3"),
    (b"\x89PNG", "png"), (b"\xff\xd8\xff", "jpeg"),
    (b"OggS", "ogg"), (b"ftyp", "mp4/m4a"),
]

TOOL_HINTS = {
    "html": ["WebFetch", "curl (正文提取，需用户确认后)"],
    "json": ["curl", "JSON 解析"],
    "pdf": ["PDF 提取工具；扫描件需 OCR"],
    "audio": ["ffmpeg (16 kHz 单声道)", "STT 后端"],
    "video": ["yt-dlp / 直链", "ffmpeg 提取音轨", "STT 后端"],
    "image": ["OCR 或图像理解"],
    "document": ["文档读取工具"],
    "unknown": ["WebSearch / domain_search 核实提取方式"],
}


def classify(content_type, suffix, magic_kind):
    ct = (content_type or "").lower()
    s = (suffix or "").lower()
    if "pdf" in ct or s == ".pdf" or magic_kind == "pdf":
        return "pdf", "pdf"
    if any(k in ct for k in ["audio"]) or s in [".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"]:
        return "audio", "audio"
    if any(k in ct for k in ["video", "mp4"]) or s in [".mp4", ".mov", ".mkv", ".webm"]:
        return "video", "video"
    if "image" in ct or s in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
        return "image", "image"
    if "json" in ct or s == ".json":
        return "json", "json"
    if "html" in ct or s in [".html", ".htm"]:
        return "html", "html"
    if s in [".docx", ".doc", ".md", ".txt", ".pptx", ".xlsx"] or (magic_kind or "").startswith("zip"):
        return "document", "document"
    return "unknown", "unknown"


def head(target, timeout, proxy=None):
    curl = shutil.which("curl")
    if not curl:
        return {"error": "curl not found"}
    cmd = [curl, "-sS", "-I", "-L", "-m", str(timeout),
           "-w", "\n__PROBE__%{http_code}|%{content_type}|%{url_effective}", target]
    if proxy:
        cmd[1:1] = ["-x", proxy]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        text = r.stdout or ""
        m = re.search(r"__PROBE__(\d+)\|([^|]*)\|(.*)", text)
        status = m.group(1) if m else None
        ctype = (m.group(2) if m else "").strip() or None
        final_url = (m.group(3) if m else "").strip()
        lengths = re.findall(r"content-length:\s*(\d+)", text, re.I)
        return {
            "http_status": status,
            "content_type": ctype,
            "content_length": int(lengths[-1]) if lengths else None,
            "final_url": final_url or None,
            "error": ("HTTP 000: channel unreachable or proxy refused" if status == "000"
                      else ((r.stderr.strip()[:120] or None) if not status else None)),
        }
    except Exception as exc:
        return {"error": str(exc)[:120]}


def local_probe(path):
    p = Path(path)
    if not p.exists():
        return {"error": "path not found"}
    if p.is_dir():
        return {"kind": "directory", "entries": len(list(p.iterdir()))}
    head_bytes = p.open("rb").read(16)
    magic_kind = next((name for sig, name in MAGIC if head_bytes.startswith(sig)
                       or (sig == b"ftyp" and head_bytes[4:8] == sig)), None)
    return {
        "kind": "local-file",
        "size_bytes": p.stat().st_size,
        "suffix": p.suffix.lower(),
        "magic": magic_kind,
        "magic_hex": head_bytes[:8].hex(),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, help="URL or local file path")
    ap.add_argument("--out", default="", help="write probe.json here")
    ap.add_argument("--proxy", default="", help="optional custom proxy to test alongside the default")
    ap.add_argument("--timeout", type=int, default=12)
    args = ap.parse_args()

    t = args.target.strip()
    is_url = t.startswith(("http://", "https://"))
    report = {
        "target": t,
        "kind": "url" if is_url else "local",
        "evidence_level": "observed (read-only probe)",
        "notes": ["只读探测，未下载正文、未登录、未消耗积分"],
    }

    if is_url:
        u = urlparse(t)
        report.update({"host": u.netloc, "path_suffix": Path(u.path).suffix.lower()})
        d = head(t, args.timeout)
        report["default_channel"] = d
        if args.proxy:
            report["custom_proxy"] = args.proxy
            report["custom_channel"] = head(t, args.timeout, args.proxy)
        ctype = d.get("content_type")
        k, group = classify(ctype, report["path_suffix"], None)
        report["detected_type"] = k
        report["suggested_tools"] = TOOL_HINTS.get(group, TOOL_HINTS["unknown"])
    else:
        info = local_probe(t)
        report.update(info)
        k, group = classify(None, info.get("suffix"), info.get("magic"))
        report["detected_type"] = k
        report["suggested_tools"] = TOOL_HINTS.get(group, TOOL_HINTS["unknown"])

    report["next_step"] = ("用 WebSearch / domain_search 核实当下做法，形成 feasibility.json "
                           "(≥2 条候选路径 + 代价 + 风险 + 回退 + 置信度)，再交 S0-B 由人拍板")
    report["disclaimer"] = "本脚本只提供客观观测；不构成可行性结论，更不构成决定"

    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
        print("WROTE", str(out.resolve()))


if __name__ == "__main__":
    main()
