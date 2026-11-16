#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查看器外壳的注入与剥离（单一实现，build_article / strip_viewer / validate_article 共用）。

设计边界：
- 查看器是**工具外壳**，不是排版内容。它只服务「本机浏览器审核图片」，
  微信编辑器会剥掉 script，所以上传微信前必须剥掉它。
- 注入与剥离都只认一对标记注释，用户手写的 script 不在标记内，
  照样被 validate_article 的 S03 拦下——这道闸不能被这个功能架空。

标记格式：
    <!-- WBI-VIEWER:START -->
    <script> ... </script>
    <!-- WBI-VIEWER:END -->
"""
import re
from pathlib import Path

START = "<!-- WBI-VIEWER:START -->"
END = "<!-- WBI-VIEWER:END -->"

# 整块匹配：START 到 END 之间的全部内容（含标记本身）
BLOCK_RE = re.compile(
    re.escape(START) + r".*?" + re.escape(END),
    re.S,
)


class ViewerError(RuntimeError):
    pass


def _asset_path() -> Path:
    """assets/viewer.js — 与本文件同属一个 skill 的 assets/。"""
    return Path(__file__).resolve().parent.parent / "assets" / "viewer.js"


def load_js() -> str:
    p = _asset_path()
    if not p.exists():
        raise ViewerError("missing assets/viewer.js at %s" % p)
    return p.read_text(encoding="utf-8").strip()


def has_viewer(html: str) -> bool:
    return START in html


def build_block() -> str:
    """组装待注入的标记块。"""
    return "\n".join([START, "<script>", load_js(), "</script>", END])


def inject(html: str) -> tuple:
    """注入查看器外壳。返回 (html, injected_bytes)。已存在则原样返回。"""
    if has_viewer(html):
        if not END in html:
            raise ViewerError("found %s but no %s — 标记不完整，拒绝注入" % (START, END))
        return html, 0
    block = build_block()
    marker = "</body></html>"
    if marker not in html:
        raise ViewerError("cannot find </body></html>; is this an article built by build_article.py?")
    out = html.replace(marker, block + marker, 1)
    return out, len(block.encode("utf-8"))


def strip(html: str) -> tuple:
    """剥离查看器外壳。返回 (html, stripped_bytes)。没有外壳则原样返回。"""
    if not has_viewer(html):
        return html, 0
    if END not in html:
        raise ViewerError("found %s but no %s — 标记不完整，拒绝剥离（请手动检查）" % (START, END))
    m = BLOCK_RE.search(html)
    if not m:
        raise ViewerError("viewer markers present but block not matched")
    out = html[:m.start()] + html[m.end():]
    return out, len(m.group(0).encode("utf-8"))


def strip_path(src: Path, dst: Path) -> dict:
    """剥离文件并写出，返回统计。"""
    html = src.read_text(encoding="utf-8")
    out, n = strip(html)
    dst.write_text(out, encoding="utf-8")
    return {
        "source": str(src),
        "output": str(dst),
        "had_viewer": n > 0,
        "stripped_bytes": n,
        "bytes": len(out.encode("utf-8")),
    }
