// Page behavior: dark-mode toggle, the gradient-descent playground, and BibTeX copy buttons.
const root = document.documentElement;

function currentTheme(): string {
  const set = root.getAttribute('data-theme');
  if (set) return set;
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

const toggle = document.querySelector<HTMLButtonElement>('.theme-toggle');
toggle?.addEventListener('click', () => {
  const next = currentTheme() === 'dark' ? 'light' : 'dark';
  root.setAttribute('data-theme', next);
  try {
    localStorage.setItem('xl-theme', next);
  } catch {
    /* storage unavailable (private mode): the choice lasts for this page view only */
  }
});

/* ---------- landscape playground ----------
   f(x, y) = (x^2 - 1)^2 + 1.2 y^2 : two global minima at (+-1, 0), a strict saddle at the origin. */
type Ball = { x: number; y: number; trail: [number, number][]; done: boolean };
type RGB = [number, number, number];

const canvas = document.getElementById('landscape');
if (canvas instanceof HTMLCanvasElement && canvas.getContext) {
  const ctx = canvas.getContext('2d')!;
  const W = canvas.width;
  const H = canvas.height;
  const X0 = -2.05, X1 = 2.05, Y0 = -1.15, Y1 = 1.15;
  const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
  let bg: ImageData | null = null;
  const balls: Ball[] = [];
  let running = false;

  const f = (x: number, y: number) => {
    const a = x * x - 1;
    return a * a + 1.2 * y * y;
  };
  const grad = (x: number, y: number): [number, number] => [4 * x * (x * x - 1), 2.4 * y];
  const toPx = (x: number, y: number): [number, number] => [((x - X0) / (X1 - X0)) * W, ((Y1 - y) / (Y1 - Y0)) * H];
  const toXY = (px: number, py: number): [number, number] => [X0 + (px / W) * (X1 - X0), Y1 - (py / H) * (Y1 - Y0)];

  const cssVar = (name: string) => getComputedStyle(root).getPropertyValue(name).trim();
  const hex = (c: string): RGB => {
    c = c.replace('#', '');
    if (c.length === 3) c = c.split('').map((ch) => ch + ch).join('');
    const n = parseInt(c, 16);
    return Number.isNaN(n) ? [200, 160, 180] : [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  };

  const paintBackground = () => {
    const low = hex(cssVar('--thumb-fill-2')), high = hex(cssVar('--surface-2')),
      line = hex(cssVar('--accent')), mid = hex(cssVar('--thumb-fill-1'));
    const img = ctx.createImageData(W, H), d = img.data;
    for (let j = 0; j < H; j++) {
      for (let i = 0; i < W; i++) {
        const p = toXY(i + 0.5, j + 0.5), v = Math.log(1 + 3 * f(p[0], p[1]));
        const t = Math.min(1, v / 2.6);
        let r = low[0] + (high[0] - low[0]) * t, g = low[1] + (high[1] - low[1]) * t, b = low[2] + (high[2] - low[2]) * t;
        if (t < 0.35) {
          const m = 1 - t / 0.35;
          r += (mid[0] - r) * m * 0.6; g += (mid[1] - g) * m * 0.6; b += (mid[2] - b) * m * 0.6;
        }
        const band = v * 5, fr = band - Math.floor(band);
        if (fr < 0.06 || fr > 0.94) {
          r += (line[0] - r) * 0.35; g += (line[1] - g) * 0.35; b += (line[2] - b) * 0.35;
        }
        const k = (j * W + i) * 4;
        d[k] = r; d[k + 1] = g; d[k + 2] = b; d[k + 3] = 255;
      }
    }
    bg = img;
  };

  const draw = () => {
    if (!bg) paintBackground();
    ctx.putImageData(bg!, 0, 0);
    const accent = cssVar('--accent'), accent2 = cssVar('--accent-2'), muted = cssVar('--muted');
    ctx.font = 'italic 15px Fraunces, Georgia, serif';
    ctx.fillStyle = muted;
    ctx.textAlign = 'center';
    for (const [x, label] of [[-1, '−x★'], [1, '+x★']] as const) {
      const q = toPx(x, 0);
      ctx.fillText(label, q[0], q[1] + 40);
    }
    const s = toPx(0, 0);
    ctx.fillText('saddle', s[0], s[1] - 18);
    ctx.beginPath(); ctx.arc(s[0], s[1], 4, 0, 2 * Math.PI); ctx.strokeStyle = muted; ctx.lineWidth = 1.5; ctx.stroke();

    for (const b of balls) {
      ctx.beginPath();
      b.trail.forEach((pt, idx) => {
        const q = toPx(pt[0], pt[1]);
        if (idx) ctx.lineTo(q[0], q[1]); else ctx.moveTo(q[0], q[1]);
      });
      ctx.strokeStyle = accent2; ctx.lineWidth = 2; ctx.setLineDash([2, 5]); ctx.lineCap = 'round'; ctx.stroke(); ctx.setLineDash([]);
      const q = toPx(b.x, b.y);
      ctx.beginPath(); ctx.arc(q[0], q[1], b.done ? 7 : 6, 0, 2 * Math.PI);
      ctx.fillStyle = accent; ctx.fill();
      if (b.done) { ctx.lineWidth = 2.5; ctx.strokeStyle = cssVar('--surface'); ctx.stroke(); }
    }
  };

  const step = (b: Ball) => {
    for (let k = 0; k < 2; k++) {
      const g = grad(b.x, b.y);
      b.x -= 0.018 * g[0]; b.y -= 0.018 * g[1];
      if (Math.abs(b.x) < 1e-3) b.x += (Math.random() - 0.5) * 2e-3; /* tiny noise: strict saddles are escapable */
    }
    b.trail.push([b.x, b.y]);
    const gg = grad(b.x, b.y);
    if (Math.hypot(gg[0], gg[1]) < 2e-3 || b.trail.length > 900) b.done = true;
  };

  const loop = () => {
    let active = false;
    for (const b of balls) if (!b.done) { step(b); active = true; }
    draw();
    if (active) requestAnimationFrame(loop); else running = false;
  };

  const drop = (x: number, y: number) => {
    const b: Ball = { x, y, trail: [[x, y]], done: false };
    balls.push(b);
    if (balls.length > 8) balls.shift();
    if (reduce) { while (!b.done) step(b); draw(); return; }
    if (!running) { running = true; requestAnimationFrame(loop); }
  };

  canvas.addEventListener('click', (e) => {
    const r = canvas.getBoundingClientRect();
    const p = toXY(((e.clientX - r.left) / r.width) * W, ((e.clientY - r.top) / r.height) * H);
    drop(p[0], p[1]);
  });

  const repaint = () => { bg = null; draw(); };
  toggle?.addEventListener('click', repaint);
  window.matchMedia?.('(prefers-color-scheme: dark)').addEventListener?.('change', repaint);

  const start = () => {
    draw();
    ([[-0.05, 1.0], [1.85, -0.9], [-1.9, -0.6]] as const).forEach((p, i) => {
      setTimeout(() => drop(p[0], p[1]), reduce ? 0 : 350 * i);
    });
  };
  if ('IntersectionObserver' in window && !reduce) {
    const io = new IntersectionObserver((entries) => {
      if (entries[0]?.isIntersecting) { io.disconnect(); start(); }
    }, { threshold: 0.3 });
    draw();
    io.observe(canvas);
  } else {
    start();
  }
}

document.querySelectorAll<HTMLButtonElement>('.bib-box .copy').forEach((btn) => {
  btn.addEventListener('click', () => {
    const code = btn.parentElement?.querySelector('code');
    if (!code) return;
    const text = code.textContent ?? '';
    const label = btn.textContent;
    const done = () => {
      btn.textContent = btn.getAttribute('data-copied') || 'Copied';
      setTimeout(() => { btn.textContent = label; }, 1500);
    };
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text).then(done, () => {});
    } else {
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); done(); } catch { /* copying unsupported */ }
      document.body.removeChild(ta);
    }
  });
});
