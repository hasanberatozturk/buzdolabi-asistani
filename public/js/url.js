// Görsel adresi doğrulaması (saf; tests/js/ altında Node ile test edilir).
// Kural sunucudakiyle aynı olmalı (app/schemas.py::RecipeIn.image_url_must_be_https).

export const MAX_IMAGE_URL_LENGTH = 500;

// Adres uygunsa null, değilse kullanıcıya gösterilecek hata metnini döndürür. Boş adres geçerlidir (görsel yok).
export function imageUrlProblem(text) {
  const value = text.trim();
  if (!value) return null;
  if (value.length > MAX_IMAGE_URL_LENGTH) return `Görsel adresi en çok ${MAX_IMAGE_URL_LENGTH} karakter olabilir.`;
  if (/[\s\u0000-\u001f]/.test(value)) return "Görsel adresi boşluk içeremez.";
  // "https:host/a.jpg" gibi tarayıcının tolere ettiği ama sunucunun reddettiği biçimleri baştan ele
  if (!value.toLowerCase().startsWith("https://")) return "Görsel adresi https:// ile başlamalı.";
  const authority = value.slice("https://".length).split(/[/?#]/)[0];
  if (!authority) return "Geçerli bir adres değil.";
  if (authority.includes("@")) return "Adres kullanıcı adı veya şifre içeremez.";
  try {
    if (!new URL(value).hostname) return "Geçerli bir adres değil.";
  } catch {
    return "Geçerli bir adres değil.";
  }
  return null;
}

// Kaydedilecek değer: kırpılmış adres, boşsa null.
export function normalizeImageUrl(text) {
  return text.trim() || null;
}
