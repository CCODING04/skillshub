/* WBI image viewer — 审核用查看器（工具外壳，非排版内容）
 *
 * 单击正文图片 → 全屏查看（自动缩到适应屏幕）；拖拽平移；滚轮 / 双指 / 键盘缩放；
 * 双击切换适应 ↔ 1:1；再次单击或 Esc 退回。
 *
 * 注意：微信编辑器会剥掉 script，这段代码只用于本机浏览器审核图片。
 * 需要上传微信时用 scripts/strip_viewer.py 剥掉它，别手改 HTML。
 */
(function () {
  var MARK = 'wbi_imgview';
  if (window[MARK]) return;
  window[MARK] = true;

  var ov = document.createElement('div');
  ov.setAttribute('data-wbi-viewer', '1');
  ov.style.cssText = 'display:none;position:fixed;left:0;top:0;right:0;bottom:0;'
    + 'width:100vw;height:100vh;background:rgba(18,18,20,.95);z-index:2147483000;'
    + 'overflow:hidden;touch-action:none;cursor:grab;';
  var img = document.createElement('img');
  img.style.cssText = 'position:absolute;left:0;top:0;transform-origin:0 0;'
    + 'user-select:none;-webkit-user-drag:none;-webkit-user-select:none;'
    + 'pointer-events:none;max-width:none;max-height:none;';
  var hint = document.createElement('div');
  hint.style.cssText = 'position:absolute;left:0;right:0;bottom:30px;text-align:center;'
    + 'color:rgba(255,255,255,.72);font:13px/1.7 -apple-system,BlinkMacSystemFont,'
    + '"PingFang SC","Microsoft YaHei",sans-serif;letter-spacing:.5px;'
    + 'pointer-events:none;transition:opacity .55s;opacity:0;';
  hint.textContent = '拖拽平移 · 滚轮或双指缩放 · 双击切换 1:1 · 再次单击或 Esc 退出';
  var tag = document.createElement('div');
  tag.style.cssText = 'position:absolute;right:22px;top:18px;color:rgba(255,255,255,.45);'
    + 'font:12px/1 -apple-system,sans-serif;letter-spacing:1.5px;pointer-events:none;';
  ov.appendChild(img); ov.appendChild(hint); ov.appendChild(tag);
  document.body.appendChild(ov);

  var st = { s: 1, tx: 0, ty: 0, iw: 0, ih: 0, vw: 0, vh: 0 };
  var open = false, dragging = false, moved = 0, lx = 0, ly = 0;
  var pinch = null, hintTimer = 0;

  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
  function apply() {
    img.style.transform = 'translate(' + st.tx + 'px,' + st.ty + 'px) scale(' + st.s + ')';
  }
  function fit() {
    st.vw = window.innerWidth; st.vh = window.innerHeight;
    var pad = 56;
    var k = Math.min((st.vw - pad) / st.iw, (st.vh - pad) / st.ih);
    st.s = k;
    st.tx = (st.vw - st.iw * k) / 2;
    st.ty = (st.vh - st.ih * k) / 2;
    apply();
  }
  function zoomAt(factor, cx, cy) {
    var ns = clamp(st.s * factor, 0.15, 14);
    var r = ns / st.s;
    st.tx = cx - (cx - st.tx) * r;
    st.ty = cy - (cy - st.ty) * r;
    st.s = ns;
    apply();
  }
  function showHint() {
    hint.style.opacity = '1';
    clearTimeout(hintTimer);
    hintTimer = setTimeout(function () { hint.style.opacity = '0'; }, 3600);
  }
  function openView(src, n, total) {
    img.onload = function () {
      st.iw = img.naturalWidth || 1080;
      st.ih = img.naturalHeight || 600;
      ov.style.display = 'block';
      document.documentElement.style.overflow = 'hidden';
      ov.style.cursor = 'grab';
      fit();
      open = true;
      tag.textContent = total > 1 ? (n + ' / ' + total) : '';
      showHint();
    };
    img.src = src;
  }
  function closeView() {
    ov.style.display = 'none';
    document.documentElement.style.overflow = '';
    open = false;
    img.removeAttribute('src');
  }

  function articleImgs() {
    var all = document.querySelectorAll('img');
    var list = [];
    for (var i = 0; i < all.length; i++) {
      if (all[i] === img) continue;
      if (!all[i].getAttribute('src')) continue;
      list.push(all[i]);
    }
    return list;
  }

  document.addEventListener('click', function (e) {
    var t = e.target;
    if (t && t.tagName === 'IMG' && t !== img && t.getAttribute('src')) {
      e.preventDefault();
      var list = articleImgs();
      var n = 1;
      for (var i = 0; i < list.length; i++) { if (list[i] === t) { n = i + 1; break; } }
      openView(t.getAttribute('src'), n, list.length);
    }
  }, true);

  ov.addEventListener('mousedown', function (e) {
    if (!open) return;
    e.preventDefault();
    dragging = true; moved = 0; lx = e.clientX; ly = e.clientY;
    ov.style.cursor = 'grabbing';
    clearTimeout(hintTimer); hint.style.opacity = '0';
  });
  window.addEventListener('mousemove', function (e) {
    if (!open || !dragging) return;
    var dx = e.clientX - lx, dy = e.clientY - ly;
    lx = e.clientX; ly = e.clientY;
    moved += Math.abs(dx) + Math.abs(dy);
    st.tx += dx; st.ty += dy;
    apply();
  });
  window.addEventListener('mouseup', function () {
    if (!open) return;
    var wasDrag = moved > 7;
    dragging = false; ov.style.cursor = 'grab';
    if (!wasDrag) closeView();
  });

  ov.addEventListener('wheel', function (e) {
    if (!open) return;
    e.preventDefault();
    zoomAt(e.deltaY < 0 ? 1.13 : 1 / 1.13, e.clientX, e.clientY);
  }, { passive: false });

  ov.addEventListener('dblclick', function (e) {
    if (!open) return;
    e.preventDefault();
    if (Math.abs(st.s - 1) < 0.02) { fit(); }
    else { zoomAt(1 / st.s, e.clientX, e.clientY); }
    showHint();
  });

  ov.addEventListener('touchstart', function (e) {
    if (!open) return;
    clearTimeout(hintTimer); hint.style.opacity = '0';
    if (e.touches.length === 1) {
      dragging = true; moved = 0;
      lx = e.touches[0].clientX; ly = e.touches[0].clientY;
    } else if (e.touches.length === 2) {
      dragging = false;
      var dx = e.touches[0].clientX - e.touches[1].clientX;
      var dy = e.touches[0].clientY - e.touches[1].clientY;
      pinch = {
        d: Math.sqrt(dx * dx + dy * dy),
        cx: (e.touches[0].clientX + e.touches[1].clientX) / 2,
        cy: (e.touches[0].clientY + e.touches[1].clientY) / 2
      };
    }
  }, { passive: false });
  ov.addEventListener('touchmove', function (e) {
    if (!open) return;
    e.preventDefault();
    if (e.touches.length === 1 && dragging) {
      var dx = e.touches[0].clientX - lx, dy = e.touches[0].clientY - ly;
      lx = e.touches[0].clientX; ly = e.touches[0].clientY;
      moved += Math.abs(dx) + Math.abs(dy);
      st.tx += dx; st.ty += dy;
      apply();
    } else if (e.touches.length === 2 && pinch) {
      var ddx = e.touches[0].clientX - e.touches[1].clientX;
      var ddy = e.touches[0].clientY - e.touches[1].clientY;
      var d = Math.sqrt(ddx * ddx + ddy * ddy);
      if (pinch.d > 0) {
        var cx = (e.touches[0].clientX + e.touches[1].clientX) / 2;
        var cy = (e.touches[0].clientY + e.touches[1].clientY) / 2;
        zoomAt(d / pinch.d, cx, cy);
        pinch.d = d;
      }
    }
  }, { passive: false });
  ov.addEventListener('touchend', function (e) {
    if (!open) return;
    if (pinch && e.touches.length < 2) { pinch = null; dragging = false; return; }
    if (dragging && e.touches.length === 0) {
      dragging = false;
      if (moved < 8) closeView();
    }
  });

  window.addEventListener('keydown', function (e) {
    if (!open) return;
    if (e.key === 'Escape' || e.key === 'Esc') closeView();
    else if (e.key === '+' || e.key === '=') zoomAt(1.2, st.vw / 2, st.vh / 2);
    else if (e.key === '-' || e.key === '_') zoomAt(1 / 1.2, st.vw / 2, st.vh / 2);
    else if (e.key === '0') fit();
  });
  window.addEventListener('resize', function () { if (open) fit(); });
})();
