// =========================================================
// Resume Analyzer — UI helpers and animations
// Every block checks that its elements exist, so one file serves all pages.
// The app still works with JavaScript turned off; JS only adds polish.
// =========================================================

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// ---------- 1. Show / hide password ----------
document.querySelectorAll(".toggle-password").forEach((btn) => {
  btn.addEventListener("click", () => {
    const input = document.getElementById(btn.dataset.target);
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    btn.classList.toggle("is-on", show);
    btn.setAttribute("aria-label", show ? "Hide password" : "Show password");
  });
});

// ---------- 2. Password strength meter (register page) ----------
const pwd = document.querySelector("#register-form #password");
if (pwd) {
  const box = document.querySelector(".strength");
  const text = document.getElementById("strength-text");
  pwd.addEventListener("input", () => {
    const v = pwd.value;
    let level = 0;
    if (v.length >= 8) level++;
    if (/[A-Z]/.test(v) && /[a-z]/.test(v)) level++;
    if (/\d/.test(v) && /[^A-Za-z0-9]/.test(v)) level++;
    box.dataset.level = v ? Math.max(level, 1) : 0;
    text.textContent = !v ? "At least 8 characters" : ["Weak", "Weak", "Medium", "Strong"][level];
  });
}

// Confirm password: say right away whether the two passwords match
const confirmPwd = document.querySelector("#register-form #confirm");
const matchHint = document.getElementById("match-hint");
if (pwd && confirmPwd && matchHint) {
  const check = () => {
    const done = confirmPwd.value.length > 0;
    const same = confirmPwd.value === pwd.value;
    matchHint.textContent = !done ? "" : same ? "✓ Passwords match" : "Passwords don't match yet";
    matchHint.className = "match-hint" + (done ? (same ? " ok" : " bad") : "");
  };
  confirmPwd.addEventListener("input", check);
  pwd.addEventListener("input", check);
}

// ---------- 3. Upload drop zone: show chosen file, check type/size before sending ----------
const fileInput = document.getElementById("resume-input");
if (fileInput) {
  const zone = document.getElementById("dropzone");
  const label = document.getElementById("dropzone-text");
  const btn = document.getElementById("upload-btn");
  const MAX = 5 * 1024 * 1024;

  const handle = (file) => {
    const ok = file && /\.(pdf|docx)$/i.test(file.name) && file.size <= MAX && file.size > 0;
    zone.classList.toggle("has-file", Boolean(ok));
    btn.disabled = !ok;
    if (!file) return;
    label.textContent = ok
      ? `${file.name} · ${Math.ceil(file.size / 1024)} KB`   // textContent: never inject HTML from a file name
      : "Please choose a PDF or DOCX under 5 MB";
    label.style.color = ok ? "" : "var(--danger)";
  };

  fileInput.addEventListener("change", () => handle(fileInput.files[0]));
  ["dragenter", "dragover"].forEach((e) =>
    zone.addEventListener(e, (ev) => { ev.preventDefault(); zone.classList.add("is-dragover"); }));
  ["dragleave", "drop"].forEach((e) =>
    zone.addEventListener(e, (ev) => { ev.preventDefault(); zone.classList.remove("is-dragover"); }));
  zone.addEventListener("drop", (ev) => {
    fileInput.files = ev.dataTransfer.files;
    handle(fileInput.files[0]);
  });

  document.getElementById("upload-form").addEventListener("submit", () => {
    btn.disabled = true;
    btn.textContent = "Uploading…";
  });
}

// ---------- 4. "Retry" buttons scroll to the upload panel and open the file picker ----------
document.querySelectorAll("[data-retry]").forEach((link) => {
  link.addEventListener("click", () => {
    if (fileInput) setTimeout(() => fileInput.click(), 400);
  });
});

// ---------- 5. Toasts can be dismissed (errors stay until dismissed) ----------
document.querySelectorAll(".toast-close").forEach((btn) => {
  btn.addEventListener("click", () => btn.closest(".toast").remove());
});

// ---------- 5b. Mobile menu ----------
document.querySelectorAll("[data-toggle]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const open = document.getElementById(btn.dataset.toggle).classList.toggle("is-open");
    btn.classList.toggle("is-open", open);
    btn.setAttribute("aria-expanded", open);
  });
});

// =========================================================
// Landing page only
// =========================================================

// ---------- 6. Reveal on scroll ----------
// IntersectionObserver tells us when an element enters the screen, without
// checking positions on every scroll (which would be slow).
const revealEls = document.querySelectorAll(".reveal");
if (revealEls.length) {
  if (reduceMotion || !("IntersectionObserver" in window)) {
    revealEls.forEach((el) => el.classList.add("in"));
  } else {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("in");
          io.unobserve(entry.target);          // animate once
        }
      });
    }, { threshold: 0.15, rootMargin: "0px 0px -8% 0px" });
    revealEls.forEach((el) => io.observe(el));
  }
}

// ---------- 7. Hero demo timeline ----------
// Each element has data-at="N". Every tick we move to the next step and switch on
// all elements whose step number has been reached. CSS transitions do the animating.
const stage = document.getElementById("stage");
if (stage) {
  const parts = stage.querySelectorAll("[data-at]");
  const paper = stage.querySelector(".paper");
  const STEPS = [  // [step number, milliseconds to wait before the next step]
    [0, 500], [1, 1200], [2, 700], [3, 900], [4, 1000], [5, 1000], [6, 1000], [7, 1100], [8, 3200],
  ];
  let i = 0, timer = null, visible = false;

  const setStep = (step) => {
    parts.forEach((el) => el.classList.toggle("on", Number(el.dataset.at) <= step && step > 0));
    stage.classList.toggle("is-done", step >= 8);
  };
  const tick = () => {
    const [step, wait] = STEPS[i];
    setStep(step);
    i = (i + 1) % STEPS.length;
    timer = setTimeout(tick, wait);
  };
  const setPaperHeight = () => stage.style.setProperty("--paper-h", `${paper.offsetHeight}px`);
  setPaperHeight();
  window.addEventListener("resize", setPaperHeight, { passive: true });

  if (reduceMotion) {
    setStep(8);                                   // show the finished result, no loop
  } else {
    // Pause the loop when the demo is off-screen, so it costs nothing while you read.
    new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      if (visible && !timer) tick();
      if (!visible && timer) { clearTimeout(timer); timer = null; }
    }).observe(stage);

    // Gentle 3D tilt that follows the mouse (desktop only)
    if (window.matchMedia("(hover: hover)").matches) {
      let raf = null;
      stage.addEventListener("pointermove", (e) => {
        if (raf) return;
        raf = requestAnimationFrame(() => {
          const r = stage.getBoundingClientRect();
          const x = (e.clientX - r.left) / r.width - 0.5;
          const y = (e.clientY - r.top) / r.height - 0.5;
          stage.style.setProperty("--ry", `${x * 5}deg`);
          stage.style.setProperty("--rx", `${-y * 5}deg`);
          raf = null;
        });
      });
      stage.addEventListener("pointerleave", () => {
        stage.style.setProperty("--ry", "0deg");
        stage.style.setProperty("--rx", "0deg");
      });
    }
  }
}

// ---------- 8. Spotlight that follows the mouse inside feature tiles ----------
document.querySelectorAll(".spot").forEach((tile) => {
  tile.addEventListener("pointermove", (e) => {
    const r = tile.getBoundingClientRect();
    tile.style.setProperty("--mx", `${e.clientX - r.left}px`);
    tile.style.setProperty("--my", `${e.clientY - r.top}px`);
  });
});

// ---------- 9. Scroll-linked effects (one listener, at most one update per frame) ----------
const nav = document.getElementById("lp-nav");
const stepsBox = document.getElementById("steps");
const stepsFill = document.getElementById("steps-fill");
const principle = document.getElementById("principle");
let words = [];

if (principle) {
  // Split the sentence into words so each can light up separately.
  const KEY = ["never", "replace", "reason,"];
  principle.innerHTML = principle.textContent.trim().split(/\s+/)
    .map((w) => `<span class="pw${KEY.includes(w.toLowerCase()) ? " key" : ""}">${w}</span>`)
    .join(" ");
  words = [...principle.querySelectorAll(".pw")];
  if (reduceMotion) words.forEach((w) => w.classList.add("lit"));
}

// How far through an element we have scrolled: 0 = just entering, 1 = reached `end`.
const progress = (el, start = 0.85, end = 0.35) => {
  const r = el.getBoundingClientRect();
  const vh = window.innerHeight;
  return Math.min(1, Math.max(0, (vh * start - r.top) / (vh * start - vh * end)));
};

if (nav || stepsFill || words.length) {
  let ticking = false;
  const update = () => {
    if (nav) nav.classList.toggle("is-scrolled", window.scrollY > 40);
    if (stepsFill && stepsBox) stepsFill.style.setProperty("--p", progress(stepsBox, 0.8, 0.45).toFixed(3));
    if (words.length && !reduceMotion) {
      const lit = Math.round(progress(principle, 0.9, 0.4) * words.length);
      words.forEach((w, n) => w.classList.toggle("lit", n < lit));
    }
    ticking = false;
  };
  window.addEventListener("scroll", () => {
    if (!ticking) { ticking = true; requestAnimationFrame(update); }
  }, { passive: true });
  update();
}

// =========================================================
// Liquid Glass (all pages)
// =========================================================

// ---------- 10. Refraction: the glass bends the wallpaper at its edges ----------
// How it works (idea from the MIT-licensed GlassiFy and nopde/liquid-glass projects):
// we draw a small "displacement map" picture for each glass element. Its red and
// green values say how far to shift each pixel left/right and up/down. Near the
// rounded edge the shift points inward, so the wallpaper looks bent, like a lens.
// The browser applies it with an SVG <feDisplacementMap> inside backdrop-filter.
// Only Chromium browsers (Chrome, Edge, Opera, Brave) support SVG filters in
// backdrop-filter, so other browsers simply keep the frosted glass.
const isChromium = Boolean(window.chrome) ||
  Boolean(navigator.userAgentData && navigator.userAgentData.brands.some((b) => b.brand === "Chromium"));
const lowTransparency = window.matchMedia("(prefers-reduced-transparency: reduce)").matches;

if (isChromium && !lowTransparency) {
  const NS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("aria-hidden", "true");
  svg.style.cssText = "position:absolute;width:0;height:0;overflow:hidden";
  document.body.appendChild(svg);

  // Build the map: R,G = 128 means "no shift"; above/below 128 shifts one way or the other.
  const makeMap = (w, h, radius, edge) => {
    const scale = Math.min(w, h) < 200 ? 1 : 0.5;       // small bars: full detail; big sheets: half (4x faster)
    const cw = Math.max(2, Math.round(w * scale)), ch = Math.max(2, Math.round(h * scale));
    const canvas = document.createElement("canvas");
    canvas.width = cw; canvas.height = ch;
    const ctx = canvas.getContext("2d");
    const img = ctx.createImageData(cw, ch);
    const r = Math.min(radius, w / 2, h / 2);
    const m = Math.min(w, h);
    for (let y = 0; y < ch; y++) {
      for (let x = 0; x < cw; x++) {
        const px = (x + 0.5) / scale - w / 2, py = (y + 0.5) / scale - h / 2;
        // distance from this pixel to the rounded edge (0 at the edge, grows inward)
        const qx = Math.abs(px) - (w / 2 - r), qy = Math.abs(py) - (h / 2 - r);
        const outside = Math.hypot(Math.max(qx, 0), Math.max(qy, 0));
        const depth = r - outside - Math.min(Math.max(qx, qy), 0);
        // direction pointing out of the glass at this pixel
        let nx = 0, ny = 0;
        if (qx > 0 && qy > 0) { nx = qx / (outside || 1); ny = qy / (outside || 1); }
        else if (qx > qy) nx = 1; else ny = 1;
        nx *= Math.sign(px); ny *= Math.sign(py);
        const t = Math.max(0, 1 - depth / edge);       // 1 at the edge, 0 deeper inside
        const k = t * t * (3 - 2 * t);                 // smoothstep: soft, lens-like falloff
        const i = (y * cw + x) * 4;
        img.data[i] = 128 - nx * k * 127 * (m / w);    // shift inward (scaled so both axes
        img.data[i + 1] = 128 - ny * k * 127 * (m / h); //  bend by the same number of pixels)
        img.data[i + 2] = 128;
        img.data[i + 3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);
    return canvas.toDataURL();
  };

  let count = 0;
  const attach = (el, strength) => {
    const id = `lg-${++count}`;
    const filter = document.createElementNS(NS, "filter");
    const image = document.createElementNS(NS, "feImage");
    image.setAttribute("preserveAspectRatio", "none");
    filter.setAttribute("id", id);
    filter.setAttribute("color-interpolation-filters", "sRGB");
    // Coordinates are fractions of the element's box (0..1), which is what backdrop-filter expects
    filter.setAttribute("primitiveUnits", "objectBoundingBox");
    for (const node of [filter, image]) {
      node.setAttribute("x", 0); node.setAttribute("y", 0);
      node.setAttribute("width", 1); node.setAttribute("height", 1);
    }

    image.setAttribute("result", "map");
    const disp = document.createElementNS(NS, "feDisplacementMap");
    disp.setAttribute("in", "SourceGraphic");
    disp.setAttribute("in2", "map");
    disp.setAttribute("xChannelSelector", "R");
    disp.setAttribute("yChannelSelector", "G");
    filter.append(image, disp);
    svg.appendChild(filter);

    let lastKey = "";
    const update = () => {
      const w = Math.round(el.offsetWidth), h = Math.round(el.offsetHeight);
      if (!w || !h) { el.classList.remove("lg-refract"); return; }
      const radius = parseFloat(getComputedStyle(el).borderTopLeftRadius) || 0;
      const key = `${w}x${h}x${radius}`;
      if (key === lastKey) return;                   // size unchanged: keep the old map
      lastKey = key;
      const edge = Math.min(30, Math.min(w, h) / 3);    // how far in from the rim the bending reaches
      image.setAttribute("href", makeMap(w, h, radius, edge));
      // scale is a fraction of the box; the map already evens out wide vs tall boxes
      disp.setAttribute("scale", (strength / Math.min(w, h)).toFixed(4));
      el.style.setProperty("--lg-filter", `url(#${id})`);
      el.classList.add("lg-refract");
    };
    update();
    if ("ResizeObserver" in window) {
      let pending = null;
      new ResizeObserver(() => {                       // rebuild (debounced) when the element resizes
        clearTimeout(pending);
        pending = setTimeout(update, 120);
      }).observe(el);
    }
  };

  // The floating controls get refraction; big content cards stay frosted (cheaper while scrolling).
  document.querySelectorAll(".lp-nav-inner, .nav-inner, .auth-card, .toast, .nav-links")
    .forEach((el) => attach(el, el.classList.contains("auth-card") ? 40 : 20));
}

// ---------- 11. A soft light that follows the pointer across glass ----------
if (window.matchMedia("(hover: hover)").matches && !reduceMotion) {
  const GLASS = ".glass, .card, .list, .stat-row, .stage";
  let target = null, raf = null, px = 0, py = 0;
  document.addEventListener("pointermove", (e) => {
    const el = e.target.closest(GLASS);
    if (target && target !== el) { target.style.removeProperty("--mx"); target.style.removeProperty("--my"); }
    target = el; px = e.clientX; py = e.clientY;
    if (!el || raf) return;
    raf = requestAnimationFrame(() => {               // at most one update per frame
      raf = null;
      if (!target) return;
      const r = target.getBoundingClientRect();
      target.style.setProperty("--mx", `${px - r.left}px`);
      target.style.setProperty("--my", `${py - r.top}px`);
    });
  }, { passive: true });
}

// ---------- 12. The segmented-control lens stretches while it slides (like iOS) ----------
document.querySelectorAll(".role-tabs").forEach((tabs) => {
  tabs.addEventListener("change", () => {
    tabs.classList.remove("is-moving");
    void tabs.offsetWidth;                            // restart the animation
    tabs.classList.add("is-moving");
  });
  tabs.addEventListener("animationend", () => tabs.classList.remove("is-moving"));
});
