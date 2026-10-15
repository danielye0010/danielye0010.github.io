(function () {
  var root = document.documentElement;

  function currentTheme() {
    var set = root.getAttribute('data-theme');
    if (set) return set;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  var toggle = document.querySelector('.theme-toggle');
  if (toggle) {
    toggle.addEventListener('click', function () {
      var next = currentTheme() === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('xl-theme', next); } catch (e) {}
    });
  }

  /* ---------- landscape playground ----------
     f(x, y) = (x^2 - 1)^2 + 1.2 y^2 : two global minima at (+-1, 0), a strict saddle at the origin. */
  var canvas = document.getElementById('landscape');
  if (canvas && canvas.getContext) {
    var ctx = canvas.getContext('2d');
    var W = canvas.width, H = canvas.height;
    var X0 = -2.05, X1 = 2.05, Y0 = -1.15, Y1 = 1.15;
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var bg = null, balls = [], running = false;

    var f = function (x, y) { var a = x * x - 1; return a * a + 1.2 * y * y; };
    var grad = function (x, y) { return [4 * x * (x * x - 1), 2.4 * y]; };
    var toPx = function (x, y) { return [(x - X0) / (X1 - X0) * W, (Y1 - y) / (Y1 - Y0) * H]; };
    var toXY = function (px, py) { return [X0 + px / W * (X1 - X0), Y1 - py / H * (Y1 - Y0)]; };

    var cssVar = function (name) { return getComputedStyle(root).getPropertyValue(name).trim(); };
    var hex = function (c) {
      c = c.replace('#', '');
      if (c.length === 3) c = c.split('').map(function (ch) { return ch + ch; }).join('');
      var n = parseInt(c, 16);
      return isNaN(n) ? [200, 160, 180] : [(n >> 16) & 255, (n >> 8) & 255, n & 255];
    };

    var paintBackground = function () {
      var low = hex(cssVar('--thumb-fill-2')), high = hex(cssVar('--surface-2')),
          line = hex(cssVar('--accent')), mid = hex(cssVar('--thumb-fill-1'));
      var img = ctx.createImageData(W, H), d = img.data;
      for (var j = 0; j < H; j++) {
        for (var i = 0; i < W; i++) {
          var p = toXY(i + 0.5, j + 0.5), v = Math.log(1 + 3 * f(p[0], p[1]));
          var t = Math.min(1, v / 2.6);
          var r = low[0] + (high[0] - low[0]) * t, g = low[1] + (high[1] - low[1]) * t, b = low[2] + (high[2] - low[2]) * t;
          if (t < 0.35) { var m = 1 - t / 0.35; r += (mid[0] - r) * m * 0.6; g += (mid[1] - g) * m * 0.6; b += (mid[2] - b) * m * 0.6; }
          var band = v * 5, fr = band - Math.floor(band);
          if (fr < 0.06 || fr > 0.94) { r += (line[0] - r) * 0.35; g += (line[1] - g) * 0.35; b += (line[2] - b) * 0.35; }
          var k = (j * W + i) * 4;
          d[k] = r; d[k + 1] = g; d[k + 2] = b; d[k + 3] = 255;
        }
      }
      bg = img;
    };

    var draw = function () {
      if (!bg) paintBackground();
      ctx.putImageData(bg, 0, 0);
      var accent = cssVar('--accent'), accent2 = cssVar('--accent-2'), muted = cssVar('--muted');
      ctx.font = 'italic 15px Fraunces, Georgia, serif';
      ctx.fillStyle = muted;
      ctx.textAlign = 'center';
      [[-1, '−x★'], [1, '+x★']].forEach(function (m) {
        var q = toPx(m[0], 0);
        ctx.fillText(m[1], q[0], q[1] + 40);
      });
      var s = toPx(0, 0);
      ctx.fillText('saddle', s[0], s[1] - 18);
      ctx.beginPath(); ctx.arc(s[0], s[1], 4, 0, 2 * Math.PI); ctx.strokeStyle = muted; ctx.lineWidth = 1.5; ctx.stroke();

      balls.forEach(function (b) {
        ctx.beginPath();
        b.trail.forEach(function (pt, idx) { var q = toPx(pt[0], pt[1]); if (idx) ctx.lineTo(q[0], q[1]); else ctx.moveTo(q[0], q[1]); });
        ctx.strokeStyle = accent2; ctx.lineWidth = 2; ctx.setLineDash([2, 5]); ctx.lineCap = 'round'; ctx.stroke(); ctx.setLineDash([]);
        var q = toPx(b.x, b.y);
        ctx.beginPath(); ctx.arc(q[0], q[1], b.done ? 7 : 6, 0, 2 * Math.PI);
        ctx.fillStyle = accent; ctx.fill();
        if (b.done) { ctx.lineWidth = 2.5; ctx.strokeStyle = cssVar('--surface'); ctx.stroke(); }
      });
    };

    var step = function (b) {
      for (var k = 0; k < 2; k++) {
        var g = grad(b.x, b.y);
        b.x -= 0.018 * g[0]; b.y -= 0.018 * g[1];
        if (Math.abs(b.x) < 1e-3) b.x += (Math.random() - 0.5) * 2e-3; /* tiny noise: strict saddles are escapable */
      }
      b.trail.push([b.x, b.y]);
      var gg = grad(b.x, b.y);
      if (Math.hypot(gg[0], gg[1]) < 2e-3 || b.trail.length > 900) b.done = true;
    };

    var loop = function () {
      var active = false;
      balls.forEach(function (b) { if (!b.done) { step(b); active = true; } });
      draw();
      if (active) requestAnimationFrame(loop); else running = false;
    };

    var drop = function (x, y) {
      var b = { x: x, y: y, trail: [[x, y]], done: false };
      balls.push(b);
      if (balls.length > 8) balls.shift();
      if (reduce) { while (!b.done) step(b); draw(); return; }
      if (!running) { running = true; requestAnimationFrame(loop); }
    };

    canvas.addEventListener('click', function (e) {
      var r = canvas.getBoundingClientRect();
      var p = toXY((e.clientX - r.left) / r.width * W, (e.clientY - r.top) / r.height * H);
      drop(p[0], p[1]);
    });

    var repaint = function () { bg = null; draw(); };
    if (toggle) toggle.addEventListener('click', repaint);
    if (window.matchMedia) {
      var mq = window.matchMedia('(prefers-color-scheme: dark)');
      if (mq.addEventListener) mq.addEventListener('change', repaint);
    }
    var start = function () {
      draw();
      [[-0.05, 1.0], [1.85, -0.9], [-1.9, -0.6]].forEach(function (p, i) {
        setTimeout(function () { drop(p[0], p[1]); }, reduce ? 0 : 350 * i);
      });
    };
    if ('IntersectionObserver' in window && !reduce) {
      var io = new IntersectionObserver(function (entries) {
        if (entries[0].isIntersecting) { io.disconnect(); start(); }
      }, { threshold: 0.3 });
      draw();
      io.observe(canvas);
    } else {
      start();
    }
  }

  document.querySelectorAll('.bib-box .copy').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var code = btn.parentElement.querySelector('code');
      if (!code) return;
      var text = code.textContent;
      var done = function () {
        btn.textContent = 'Copied';
        setTimeout(function () { btn.textContent = 'Copy'; }, 1500);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function () {});
      } else {
        var ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        try { document.execCommand('copy'); done(); } catch (e) {}
        document.body.removeChild(ta);
      }
    });
  });
})();
