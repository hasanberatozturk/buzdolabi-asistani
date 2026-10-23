// Güvenli DOM oluşturma: metinler her zaman metin düğümü olarak eklenir (innerHTML yok).
export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === false || value == null) continue;
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat()) {
    if (child === false || child == null) continue;
    node.append(child);
  }
  return node;
}

export function clear(node) {
  node.replaceChildren();
}

// Harici görsel: Referer göndermeden yüklenir, yüklenemezse kendini kaldırır (kırık görsel simgesi kalmaz).
// lazy=false sayfanın üstündeki ana görseller içindir (tembel yükleme orada gecikme ve yer kayması yaratır).
export function image(url, alt, className, { lazy = true } = {}) {
  const img = el("img", {
    src: url,
    alt,
    class: className,
    loading: lazy ? "lazy" : "eager",
    decoding: "async",
    referrerpolicy: "no-referrer",
  });
  img.addEventListener("error", () => img.remove());
  return img;
}

