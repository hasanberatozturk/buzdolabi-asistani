// Porsiyon ölçekleme için saf yardımcılar (DOM yok; tests/js/scale.test.mjs ile test edilir).

export const MIN_SERVINGS = 1;
export const MAX_SERVINGS = 1000; // sunucudaki RecipeIn.servings üst sınırı (app/schemas.py) ile aynı

export function scaleQuantity(quantity, baseServings, targetServings) {
  return (quantity * targetServings) / baseServings;
}

// Türkçe biçim (virgüllü ondalık, binlik noktası). En çok 2 basamak; 0,1'in altındakiler 3 basamak.
export function formatQuantity(value) {
  if (value > 0 && value < 0.001) return "<0,001";
  const digits = Math.abs(value) < 0.1 ? 3 : 2;
  return value.toLocaleString("tr-TR", { maximumFractionDigits: digits });
}

// Kullanıcının yazdığı metni porsiyon sayısına çevirir; geçersizse null.
export function parseServings(text) {
  const trimmed = String(text).trim();
  if (!/^\d+$/.test(trimmed)) return null;
  const value = Number(trimmed);
  return value >= MIN_SERVINGS && value <= MAX_SERVINGS ? value : null;
}

export function clampServings(value) {
  return Math.min(MAX_SERVINGS, Math.max(MIN_SERVINGS, value));
}
