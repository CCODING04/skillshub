#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""产出「上传微信版」：剥掉审核用的图片查看器外壳。

    python scripts/strip_viewer.py dist/wechat-article.html
    python scripts/strip_viewer.py dist/wechat-article.html --out dist/wechat-wechat.html

默认输出到同目录 <原名去 .html>-wechat.html。

为什么要这一步：build_article.py 默认产出的 wechat-article.html 带图片查看器
（单击全屏、拖拽、缩放），那是给人在浏览器里审核图片用的。微信编辑器会剥掉
script，这段代码粘过去不生效，还会让门禁的 S03 报错。上传微信前用本脚本剥掉。
"""
import argparse
import json
import sys
from pathlib import Path

# 允许直接运行：把 scripts/ 加进 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import viewer_util  # noqa: E402


def default_out(src: Path) -> Path:
    return src.with_name(src.stem + "-wechat.html")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="剥掉审核用图片查看器，产出可上传微信公众号的 HTML")
    ap.add_argument("html", help="build_article.py 产出的 wechat-article.html（审核版）")
    ap.add_argument("--out", default="", help="输出路径（默认 <原名去 .html>-wechat.html）")
    args = ap.parse_args()

    src = Path(args.html)
    if not src.exists():
        print("ERROR file not found: %s" % src, file=sys.stderr)
        return 2
    dst = Path(args.out) if args.out else default_out(src)
    if dst.resolve() == src.resolve():
        print("ERROR --out 不能与输入同名（审核版要保留，别覆盖）", file=sys.stderr)
        return 2

    try:
        stat = viewer_util.strip_path(src, dst)
    except viewer_util.ViewerError as exc:
        print("ERROR %s" % exc, file=sys.stderr)
        return 1

    stat["note"] = ("已剥离图片查看器外壳，可直接粘贴公众号"
                    if stat["had_viewer"] else
                    "源文件不含查看器外壳，已原样复制")
    print(json.dumps(stat, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
