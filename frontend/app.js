// Dung chung cho host va nguoi choi. Chi chua tien ich, khong co logic man hinh.

const COLORS = ["#e74c3c", "#3498db", "#f1c40f", "#2ecc71"];
const LETTERS = ["A", "B", "C", "D"];

// Goi API. Tra ve {ok, status, data}. Khong nem loi khi HTTP loi.
async function api(method, path, { body, headers } = {}) {
  const opts = { method, headers: { ...(headers || {}) } };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  try {
    const res = await fetch(path, opts);
    let data = null;
    try { data = await res.json(); } catch (e) { data = null; }
    return { ok: res.ok, status: res.status, data };
  } catch (e) {
    return { ok: false, status: 0, data: null };
  }
}

// Goi fn() moi `ms` mili giay, khong chong cheo. Tra ve ham dung.
function poll(fn, ms = 1000) {
  let stopped = false;
  async function tick() {
    if (stopped) return;
    try { await fn(); } catch (e) { console.error(e); }
    if (!stopped) setTimeout(tick, ms);
  }
  tick();
  return () => { stopped = true; };
}

// Lay/ghi gia tri theo phong trong sessionStorage (khong lam vo trang neu bi chan).
function store(key, value) {
  try {
    if (value === undefined) return sessionStorage.getItem(key);
    if (value === null) sessionStorage.removeItem(key);
    else sessionStorage.setItem(key, value);
  } catch (e) { return null; }
  return value;
}

function el(id) { return document.getElementById(id); }

function show(id, visible) { el(id).hidden = !visible; }
