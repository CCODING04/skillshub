#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Submit a PDF to MinerU v4, poll until done, download and unzip the result.

Generic CLI — no WorkBuddy / project-specific paths. Token is resolved from
(first match wins):
  1. env var MINERU_API_TOKEN
  2. --token-file PATH (a plain token or JSON with a 'mineru' key)
  3. ./.env.json  (JSON key 'mineru'; tolerates trailing commas)

The token is used internally and NEVER printed.

Usage:
  python mineru_convert.py --url https://arxiv.org/pdf/XXXX.XXXXX --out temp/mineru_out
  python mineru_convert.py --pdf ./paper.pdf --out temp/mineru_out --language en
"""
import argparse, io, json, os, re, sys, time, zipfile

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: pip install requests")

BASE = "https://mineru.net"


def strip_trailing_commas(s):
    return re.sub(r",\s*([}\]])", r"\1", s)


def resolve_token(token_file=None):
    tok = os.environ.get("MINERU_API_TOKEN")
    if tok:
        return tok.strip()
    candidates = [token_file, ".env.json", os.path.expanduser("~/.mineru/token")]
    for p in candidates:
        if not p or not os.path.exists(p):
            continue
        raw = open(p, encoding="utf-8").read().strip()
        try:
            d = json.loads(strip_trailing_commas(raw))
            if isinstance(d, dict):
                tok = d.get("mineru") or d.get("token") or d.get("api_token")
                if tok:
                    return str(tok)
            elif isinstance(d, str):
                return d
        except Exception:
            if raw and not raw.startswith("{"):
                return raw  # plain token file
    sys.exit("No MinerU token found. Set MINERU_API_TOKEN or pass --token-file.")


def headers_for(token):
    return {"Content-Type": "application/json",
            "Authorization": "Bearer " + token,
            "Accept": "*/*"}


def submit_by_url(hdrs, url, language, data_id):
    payload = {"url": url, "model_version": "vlm", "is_ocr": False,
               "enable_formula": True, "enable_table": True, "language": language}
    if data_id:
        payload["data_id"] = data_id
    return requests.post(BASE + "/api/v4/extract/task", headers=hdrs, json=payload, timeout=60)


def upload_local(hdrs, path):
    r = requests.post(BASE + "/api/v4/file-urls/batch", headers=hdrs,
                      json={"files": [{"name": os.path.basename(path)}]}, timeout=60)
    r.raise_for_status()
    j = r.json()["data"]
    batch_id, upload_url = j["batch_id"], j["file_urls"][0]
    with open(path, "rb") as f:
        requests.put(upload_url, data=f, timeout=180).raise_for_status()
    return batch_id


def poll(hdrs, url, max_wait, interval, label):
    started = time.time()
    while time.time() - started < max_wait:
        r = requests.get(url, headers=hdrs, timeout=60)
        j = r.json()
        data = j.get("data", {})
        # task endpoint
        state = data.get("state")
        prog = data.get("extract_progress") or {}
        if state:
            print("%s STATE=%s pages=%s/%s" % (label, state, prog.get("extracted_pages"),
                                               prog.get("total_pages")), flush=True)
            if state == "done":
                return data.get("full_zip_url")
            if state == "failed":
                raise RuntimeError("%s failed: %s" % (label, data.get("err_msg")))
        # batch endpoint
        results = data.get("extract_results") if isinstance(data, dict) else data
        if results:
            item = results[0] if isinstance(results, list) else results
            st = item.get("state")
            print("%s STATE=%s" % (label, st), flush=True)
            if st == "done":
                return item.get("full_zip_url")
            if st == "failed":
                raise RuntimeError("%s failed: %s" % (label, item.get("err_msg")))
        time.sleep(interval)
    raise TimeoutError("%s polling timed out" % label)


def download_unzip(zip_url, out_dir):
    print("Downloading result zip ...", flush=True)
    r = requests.get(zip_url, timeout=240)
    r.raise_for_status()
    os.makedirs(out_dir, exist_ok=True)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall(out_dir)
    names = z.namelist()
    md = [n for n in names if n.lower().endswith(".md")]
    imgs = [n for n in names if n.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]
    print("ZIP entries=%d markdown=%d images=%d" % (len(names), len(md), len(imgs)), flush=True)
    for n in md:
        print("MD: %s (%d bytes)" % (n, os.path.getsize(os.path.join(out_dir, n))), flush=True)
    return md


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", help="PDF URL (preferred submission path)")
    ap.add_argument("--pdf", help="local PDF path (fallback / URL-less mode)")
    ap.add_argument("--out", default="temp/mineru_out", help="output directory")
    ap.add_argument("--language", default="en", help="document language (default: en)")
    ap.add_argument("--data-id", default=None, help="optional MinerU data_id")
    ap.add_argument("--token-file", default=None, help="path to token / .env.json")
    ap.add_argument("--max-wait", type=int, default=420, help="polling timeout seconds")
    args = ap.parse_args()
    if not args.url and not args.pdf:
        ap.error("provide --url or --pdf")

    hdrs = headers_for(resolve_token(args.token_file))
    zip_url = None

    if args.url:
        try:
            print("Submitting by URL ...", flush=True)
            r = submit_by_url(hdrs, args.url, args.language, args.data_id)
            print("submit http=%s" % r.status_code, flush=True)
            j = r.json()
            if j.get("code") == 0 and j.get("data", {}).get("task_id"):
                zip_url = poll(hdrs, BASE + "/api/v4/extract/task/" + j["data"]["task_id"],
                               args.max_wait, 4, "TASK")
            else:
                print("URL submit rejected: code=%s msg=%s" % (j.get("code"), j.get("msg")), flush=True)
        except Exception as e:
            print("URL path error: %s" % type(e).__name__, flush=True)

    if not zip_url and args.pdf:
        print("Falling back to local upload ...", flush=True)
        batch_id = upload_local(hdrs, args.pdf)
        zip_url = poll(hdrs, BASE + "/api/v4/extract-results/batch/" + batch_id,
                       args.max_wait, 4, "BATCH")

    if not zip_url:
        raise RuntimeError("no zip url obtained; supply a reachable --url or a valid --pdf")
    download_unzip(zip_url, args.out)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
