// Etiket ve filtre yardımcıları (saf; tests/js/ altında Node ile test edilir).
import { fold } from "./text.js";

// Sunucudaki sınırlarla aynı olmalı (app/schemas.py::MAX_TAGS_PER_RECIPE, MAX_TAG_LENGTH)
export const MAX_TAGS = 10;
export const MAX_TAG_LENGTH = 50;
export const QUICK_MINUTES = 30; // "30 dk altı" filtresi

// "kahvaltı, Vejetaryen ,, ana   yemek" → ["kahvaltı", "Vejetaryen", "ana yemek"]
// Boşlar atılır, katlanmış hâlde tekrar edenler tek bırakılır (ilk yazılış korunur).
export function parseTags(text) {
  const result = [];
  const seen = new Set();
  for (const part of text.split(",")) {
    const name = part.trim().replace(/\s+/g, " ");
    const key = fold(name);
    if (!key || seen.has(key)) continue;
    seen.add(key);
    result.push(name);
  }
  return result;
}

export function hasTag(list, name) {
  const key = fold(name);
  return list.some((item) => fold(item) === key);
}

// Etiket listesinde varsa çıkarır, yoksa sona ekler (büyük/küçük harf ve i/ı fark etmez).
export function toggleTag(list, name) {
  if (hasTag(list, name)) {
    const key = fold(name);
    return list.filter((item) => fold(item) !== key);
  }
  return [...list, name];
}

// Eşleştirme uç noktasının sorgu dizesi: /api/recipes/match?max_missing=2&tag=a&tag=b&max_minutes=30
export function buildMatchQuery({ maxMissing, tags = [], maxMinutes = null }) {
  const params = new URLSearchParams({ max_missing: String(maxMissing) });
  for (const tag of tags) params.append("tag", tag);
  if (maxMinutes != null) params.set("max_minutes", String(maxMinutes));
  return params.toString();
}

// Tüm tarifler görünümü için liste sorgusu: /api/recipes?limit=12&offset=0&tag=a&max_minutes=30
export function buildListQuery({ limit, offset = 0, tags = [], maxMinutes = null }) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  for (const tag of tags) params.append("tag", tag);
  if (maxMinutes != null) params.set("max_minutes", String(maxMinutes));
  return params.toString();
}

// Sayfa adresindeki filtreler: ?tag=kahvaltı&tag=vegan&max_minutes=30&view=all (geçersizler yok sayılır).
// view: "match" (buzdolabına göre öneriler, varsayılan) ya da "all" (tüm tarifler).
export function parseFilterParams(search) {
  const params = new URLSearchParams(search);
  const tags = [];
  for (const raw of params.getAll("tag")) {
    const name = raw.trim().replace(/\s+/g, " ");
    if (name && name.length <= MAX_TAG_LENGTH && !hasTag(tags, name)) tags.push(name);
  }
  const minutes = params.get("max_minutes");
  const maxMinutes = minutes !== null && /^\d{1,5}$/.test(minutes) && Number(minutes) <= 10000 ? Number(minutes) : null;
  const view = params.get("view") === "all" ? "all" : "match";
  return { tags: tags.slice(0, MAX_TAGS), maxMinutes, view };
}

// Filtreleri sayfa adresine yazar (paylaşılabilir bağlantı); filtre yoksa sorgu dizesi boş kalır.
export function filtersToSearch({ tags = [], maxMinutes = null, view = "match" }) {
  const params = new URLSearchParams();
  if (view === "all") params.set("view", "all");
  for (const tag of tags) params.append("tag", tag);
  if (maxMinutes != null) params.set("max_minutes", String(maxMinutes));
  const text = params.toString();
  return text ? `?${text}` : "";
}

export function hasActiveFilters({ tags = [], maxMinutes = null }) {
  return tags.length > 0 || maxMinutes != null;
}
