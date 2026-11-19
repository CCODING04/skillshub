#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Headless-browser interaction test — generic, no ego lite / WorkBuddy needed.

Strategy: copy the target HTML, inject a self-test <script> that runs the same
assertions as the ego test, writes results into <pre id="__TEST_RESULT__">, then
run Chrome/Edge headless with --dump-dom and parse that node. Only a browser is
required (no Python websocket libs).

Usage:
  python browser_test.py path/to/paper_bilingual.html
  python browser_test.py paper_bilingual.html --chrome /path/to/chrome
"""
import argparse, os, re, shutil, subprocess, sys, tempfile, html

TEST_JS = r"""
<script>
(function(){
  var out=[], R=function(n,ok,d){out.push((ok?'PASS':'FAIL')+' | '+n+' | '+(d||''))};
  function click(sel){var e=document.querySelector(sel);if(e)e.click();return e}
  try{
    // 1. TOC collapse + mode switch keeps it collapsed (the classic state-clobber bug)
    click('#sbCollapse');
    var c1=document.body.classList.contains('toc-collapsed');
    click('#modeSeg button[data-mode="stack"]');
    var md=[].filter.call(document.body.classList,function(x){return x.indexOf('mode-')===0})[0];
    var c2=document.body.classList.contains('toc-collapsed');
    R('模式切换保持目录收起', c1&&c2&&md==='mode-stack', 'before='+c1+' after='+c2+' mode='+md);
    click('#modeSeg button[data-mode="side"]');

    // 2. TOC two-level expander
    var g=document.querySelector('.toc-group:not(.no-children)');
    if(g){var btn=g.querySelector('.toc-expander');var b0=g.classList.contains('collapsed');
      btn.click();var b1=g.classList.contains('collapsed');btn.click();
      R('二级目录展开收起', !b0&&b1, 'before='+b0+' after='+b1);
    } else R('二级目录展开收起',false,'no group');

    // 3. TOC filter
    var inp=document.getElementById('sbFilter');
    if(inp){inp.value='Agent';inp.dispatchEvent(new Event('input'));
      var hid=[].filter.call(document.querySelectorAll('#sbList a'),function(a){return a.hidden}).length;
      inp.value='';inp.dispatchEvent(new Event('input'));
      R('目录筛选',hid>0,'hidden='+hid);
    } else R('目录筛选',false,'no filter');

    // 4. citation hover popup + jump target
    var a=document.querySelector('a.cite');
    if(a){a.dispatchEvent(new MouseEvent('mouseover',{bubbles:true}));
      var pop=document.getElementById('citePopup');
      var ok=pop&&pop.style.display==='block'&&!!pop.querySelector('.cp-jump');
      var target=document.getElementById(a.getAttribute('href').slice(1));
      R('引用悬浮预览+跳转锚点', ok&&!!target, 'href='+a.getAttribute('href'));
    } else R('引用悬浮预览+跳转锚点',false,'no cite');

    // 5. image lightbox open/zoom/close
    var img=document.querySelector('figure img'), box=document.getElementById('imgLightbox');
    if(img&&box){img.click();var op=box.classList.contains('show');
      document.getElementById('lbZoomIn').click();var z1=document.getElementById('lbImg').style.transform;
      document.getElementById('lbReset').click();var z2=document.getElementById('lbImg').style.transform;
      box.click();R('图片全屏/缩放/还原',op&&z1!==z2&&!box.classList.contains('show'),'');
    } else R('图片全屏/缩放/还原',false,'no img/box');

    // 6. font slider can decrease AND increase
    var s=document.getElementById('fpSize');
    if(s){s.value=12;s.dispatchEvent(new Event('input'));var lo=document.body.style.fontSize;
      s.value=24;s.dispatchEvent(new Event('input'));var hi=document.body.style.fontSize;
      s.value=15;s.dispatchEvent(new Event('input'));
      R('字号可调小/放大',lo==='12px'&&hi==='24px','lo='+lo+' hi='+hi);
    } else R('字号可调小/放大',false,'no slider');

    // 7. anchor offset clears sticky header (measured, not hardcoded)
    var h=document.querySelector('header');
    if(h){var off=parseInt(getComputedStyle(document.documentElement).getPropertyValue('--anchor-offset'));
      R('锚点偏移≥顶栏高度', off>=Math.round(h.getBoundingClientRect().height)+10,
        'offset='+off+' header='+Math.round(h.getBoundingClientRect().height));
    } else R('锚点偏移≥顶栏高度',false,'no header');

    // 8. no leftover LaTeX escapes / code fences in rendered HTML
    var bs=String.fromCharCode(92);
    R('无字面LaTeX转义', document.body.textContent.indexOf(bs+'$')<0 &&
      document.documentElement.outerHTML.indexOf(bs+'$')<0, '');

    // 9. refs <-> citations no dead links
    var cited={},anchors={};
    [].forEach.call(document.querySelectorAll('a.cite'),function(x){cited[x.getAttribute('data-ref')]=1});
    [].forEach.call(document.querySelectorAll('[id^="ref-"]'),function(x){anchors[x.id]=1});
    var dead=Object.keys(cited).filter(function(k){return !anchors[k]});
    R('引用零死链',dead.length===0,'cited='+Object.keys(cited).length+' dead='+dead.length);
  }catch(e){R('测试执行异常',false,String(e))}
  // Build markers by concatenation so the literal never appears in the script text
  // (otherwise --dump-dom would match the source inside <script>).
  var B='__BEGIN'+'__', E='__END'+'__';
  var pre=document.createElement('pre');pre.id='__TEST_RESULT__';
  pre.textContent=B+'\n'+out.join('\n')+'\n'+E;
  document.body.appendChild(pre);
})();
</script>
"""


def find_chrome(explicit=None):
    if explicit and os.path.exists(explicit):
        return explicit
    candidates = [
        "C:/Program Files/Google/Chrome/Application/chrome.exe",
        "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
        "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
        "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    for name in ("google-chrome", "chromium", "chrome"):
        p = shutil.which(name)
        if p:
            return p
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("html", help="bilingual HTML to test")
    ap.add_argument("--chrome", default=None, help="explicit browser path")
    args = ap.parse_args()
    if not os.path.exists(args.html):
        ap.error("HTML not found")
    chrome = find_chrome(args.chrome)
    if not chrome:
        sys.exit("No Chrome/Edge found. Pass --chrome /path/to/browser")

    tmpdir = tempfile.mkdtemp(prefix="bilingual-test-")
    testhtml = os.path.join(tmpdir, "test.html")
    src = open(args.html, encoding="utf-8").read()
    # images use relative paths -> copy them alongside, or rewrite to absolute
    src_abs = re.sub(r'src="(images/[^"]+)"',
                     lambda m: 'src="%s"' % os.path.join(os.path.dirname(os.path.abspath(args.html)), m.group(1)).replace("\\", "/"),
                     src)
    src_abs = src_abs.replace("</body>", TEST_JS + "</body>")
    open(testhtml, "w", encoding="utf-8").write(src_abs)

    try:
        proc = subprocess.run(
            [chrome, "--headless", "--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage",
             "--virtual-time-budget=4000", "--dump-dom", "file:///" + testhtml.replace("\\", "/")],
            capture_output=True, text=True, errors="ignore", timeout=90)
        dom = proc.stdout
        m = re.search(r"__BEGIN__(.*?)__END__", dom, re.S)
        if not m:
            sys.exit("No test result in DOM. Browser stderr:\n" + proc.stderr[:500])
        lines = html.unescape(m.group(1)).strip().splitlines()
        print("=== BROWSER TEST (%s) ===" % os.path.basename(chrome))
        for ln in lines:
            print(ln)
        total = len(lines)
        passed = sum(1 for ln in lines if ln.startswith("PASS"))
        print("TOTAL: %d/%d PASS" % (passed, total))
        sys.exit(0 if passed == total else 1)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
