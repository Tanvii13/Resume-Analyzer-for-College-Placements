// Small UI helpers. The app still works if JavaScript is turned off.

// 1. Show / hide password
document.querySelectorAll(".toggle-password").forEach((btn) => {
  btn.addEventListener("click", () => {
    const input = document.getElementById(btn.dataset.target);
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    btn.classList.toggle("is-on", show);
    btn.setAttribute("aria-label", show ? "Hide password" : "Show password");
  });
});

// 2. Password strength meter (register page)
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

// 3. Upload drop zone: show chosen file, check type/size before sending
const input = document.getElementById("resume-input");
if (input) {
  const zone = document.getElementById("dropzone");
  const label = document.getElementById("dropzone-text");
  const btn = document.getElementById("upload-btn");
  const MAX = 5 * 1024 * 1024;

  const handle = (file) => {
    const ok = file && /\.(pdf|docx)$/i.test(file.name) && file.size <= MAX && file.size > 0;
    zone.classList.toggle("has-file", ok);
    btn.disabled = !ok;
    if (!file) return;
    label.innerHTML = ok
      ? `<strong>${file.name}</strong> · ${Math.ceil(file.size / 1024)} KB`
      : `<strong style="color:var(--danger)">Please choose a PDF or DOCX under 5 MB</strong>`;
  };

  input.addEventListener("change", () => handle(input.files[0]));

  ["dragenter", "dragover"].forEach((e) =>
    zone.addEventListener(e, (ev) => { ev.preventDefault(); zone.classList.add("is-dragover"); }));
  ["dragleave", "drop"].forEach((e) =>
    zone.addEventListener(e, (ev) => { ev.preventDefault(); zone.classList.remove("is-dragover"); }));
  zone.addEventListener("drop", (ev) => {
    input.files = ev.dataTransfer.files;
    handle(input.files[0]);
  });

  document.getElementById("upload-form").addEventListener("submit", () => {
    btn.disabled = true;
    btn.textContent = "Uploading…";
  });
}

// 4. "Retry" buttons scroll to the upload panel and open the file picker
document.querySelectorAll("[data-retry]").forEach((link) => {
  link.addEventListener("click", () => {
    const picker = document.getElementById("resume-input");
    if (picker) setTimeout(() => picker.click(), 300);
  });
});

// 5. Mobile menu
document.querySelectorAll("[data-toggle]").forEach((btn) => {
  btn.addEventListener("click", () =>
    document.getElementById(btn.dataset.toggle).classList.toggle("is-open"));
});
