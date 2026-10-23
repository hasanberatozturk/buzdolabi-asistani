import assert from "node:assert/strict";
import { test } from "node:test";

import {
  MAX_TAGS,
  buildMatchQuery,
  filtersToSearch,
  hasActiveFilters,
  hasTag,
  parseFilterParams,
  parseTags,
  toggleTag,
} from "../../public/js/tags.js";
import { fold } from "../../public/js/text.js";

test("fold sunucudaki normalize() ile aynı kuralı uygular", () => {
  assert.equal(fold("İrmik"), "irmik");
  assert.equal(fold("ISPANAK"), "ispanak");
  assert.equal(fold("ıspanak"), "ispanak");
  assert.equal(fold("  Sivri   Biber "), "sivri biber");
  assert.equal(fold(""), "");
});

test("parseTags virgülle ayırır, boşları atar, boşlukları sadeleştirir", () => {
  assert.deepEqual(parseTags("kahvaltı, Vejetaryen ,, ana   yemek"), ["kahvaltı", "Vejetaryen", "ana yemek"]);
  assert.deepEqual(parseTags(""), []);
  assert.deepEqual(parseTags(" , ,, "), []);
});

test("parseTags katlanmış hâlde tekrar edenleri tek bırakır ve ilk yazılışı korur", () => {
  assert.deepEqual(parseTags("Kahvaltı, kahvalti, KAHVALTI"), ["Kahvaltı"]);
  assert.deepEqual(parseTags("Irmak, ırmak, İrmak"), ["Irmak"]);
});

test("toggleTag ekler ve çıkarır, yazım farkını görmezden gelir", () => {
  assert.deepEqual(toggleTag(["kahvaltı"], "vegan"), ["kahvaltı", "vegan"]);
  assert.deepEqual(toggleTag(["kahvaltı", "vegan"], "KAHVALTI"), ["vegan"]);
  assert.deepEqual(toggleTag(["kahvaltı"], "kahvalti"), []);
  assert.deepEqual(toggleTag([], "çorba"), ["çorba"]);
});

test("toggleTag girdi dizisini değiştirmez", () => {
  const list = ["a", "b"];
  toggleTag(list, "a");
  toggleTag(list, "c");
  assert.deepEqual(list, ["a", "b"]);
});

test("hasTag büyük/küçük harf ve i/ı farkını görmezden gelir", () => {
  assert.equal(hasTag(["Kahvaltı"], "kahvalti"), true);
  assert.equal(hasTag(["Kahvaltı"], "tatlı"), false);
  assert.equal(hasTag([], "x"), false);
});

test("buildMatchQuery eksik sayısını, etiketleri ve süreyi kodlar", () => {
  assert.equal(buildMatchQuery({ maxMissing: 2 }), "max_missing=2");
  assert.equal(buildMatchQuery({ maxMissing: 0, tags: ["kahvaltı", "ana yemek"], maxMinutes: 30 }), "max_missing=0&tag=kahvalt%C4%B1&tag=ana+yemek&max_minutes=30");
});

test("buildMatchQuery özel karakterleri sorguyu bozmayacak biçimde kodlar", () => {
  const query = buildMatchQuery({ maxMissing: 1, tags: ["a&b=c#d", "x y"] });
  const parsed = new URLSearchParams(query);
  assert.deepEqual(parsed.getAll("tag"), ["a&b=c#d", "x y"]);
  assert.equal(parsed.get("max_missing"), "1");
  assert.equal(parsed.has("max_minutes"), false);
});

test("parseFilterParams adresten etiket ve süreyi okur", () => {
  assert.deepEqual(parseFilterParams("?tag=kahvalt%C4%B1&tag=vegan&max_minutes=30"), { tags: ["kahvaltı", "vegan"], maxMinutes: 30 });
  assert.deepEqual(parseFilterParams(""), { tags: [], maxMinutes: null });
});

test("parseFilterParams geçersiz değerleri yok sayar", () => {
  assert.equal(parseFilterParams("?max_minutes=abc").maxMinutes, null);
  assert.equal(parseFilterParams("?max_minutes=-5").maxMinutes, null);
  assert.equal(parseFilterParams("?max_minutes=10001").maxMinutes, null);
  assert.equal(parseFilterParams("?max_minutes=0").maxMinutes, 0);
  assert.deepEqual(parseFilterParams("?tag=&tag=%20%20").tags, []);
  assert.deepEqual(parseFilterParams("?tag=" + "x".repeat(51)).tags, []);
});

test("parseFilterParams tekrar edenleri ve fazlalığı sınırlar", () => {
  assert.deepEqual(parseFilterParams("?tag=Vegan&tag=vegan&tag=VEGAN").tags, ["Vegan"]);
  const many = Array.from({ length: 15 }, (_, i) => `tag=e${i}`).join("&");
  assert.equal(parseFilterParams(`?${many}`).tags.length, MAX_TAGS);
});

test("filtersToSearch ve parseFilterParams birbirinin tersidir", () => {
  const filters = { tags: ["ana yemek", "çorba"], maxMinutes: 30 };
  assert.deepEqual(parseFilterParams(filtersToSearch(filters)), filters);
  assert.equal(filtersToSearch({ tags: [], maxMinutes: null }), "");
});

test("hasActiveFilters", () => {
  assert.equal(hasActiveFilters({ tags: [], maxMinutes: null }), false);
  assert.equal(hasActiveFilters({ tags: ["a"], maxMinutes: null }), true);
  assert.equal(hasActiveFilters({ tags: [], maxMinutes: 30 }), true);
});
