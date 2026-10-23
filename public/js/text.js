// Metin yardımcıları (saf; tests/js/ altında Node ile test edilir).

// Sunucudaki normalize() ile aynı kural (app/utils/text.py): İ/I/ı → i, küçük harf, tek boşluk.
export function fold(text) {
  return text.trim().replace(/[İIı]/g, "i").toLowerCase().replace(/\s+/g, " ");
}
