import assert from "node:assert/strict";
import { test } from "node:test";

import {
  MAX_SERVINGS,
  MIN_SERVINGS,
  clampServings,
  formatQuantity,
  parseServings,
  scaleQuantity,
} from "../../public/js/scale.js";

test("scaleQuantity orantılı çarpar", () => {
  assert.equal(scaleQuantity(200, 2, 4), 400);
  assert.equal(scaleQuantity(1, 2, 3), 1.5);
  assert.equal(scaleQuantity(0.75, 4, 2), 0.375);
  assert.equal(scaleQuantity(3, 3, 3), 3); // aynı porsiyon: değişmez
});

test("scaleQuantity küçülürken de çalışır", () => {
  assert.equal(scaleQuantity(4, 4, 1), 1);
  assert.equal(scaleQuantity(1, 4, 1), 0.25);
});

test("formatQuantity Türkçe biçim kullanır", () => {
  assert.equal(formatQuantity(1.5), "1,5");
  assert.equal(formatQuantity(400), "400");
  assert.equal(formatQuantity(1000), "1.000");
  assert.equal(formatQuantity(0), "0");
});

test("formatQuantity en çok 2 basamak gösterir ve kayan nokta gürültüsünü temizler", () => {
  assert.equal(formatQuantity(1.125), "1,13");
  assert.equal(formatQuantity(1 / 3), "0,33");
  assert.equal(formatQuantity(0.1 + 0.2), "0,3"); // 0.30000000000000004
  assert.equal(formatQuantity(0.375), "0,38");
});

test("formatQuantity küçük değerlerde 3 basamak, çok küçüklerde alt sınır gösterir", () => {
  assert.equal(formatQuantity(0.05), "0,05");
  assert.equal(formatQuantity(0.0123), "0,012");
  assert.equal(formatQuantity(0.0004), "<0,001");
});

test("parseServings yalnızca 1..MAX arası tam sayıyı kabul eder", () => {
  assert.equal(parseServings("4"), 4);
  assert.equal(parseServings(" 12 "), 12);
  assert.equal(parseServings(String(MIN_SERVINGS)), MIN_SERVINGS);
  assert.equal(parseServings(String(MAX_SERVINGS)), MAX_SERVINGS);
});

test("parseServings geçersiz girdiyi reddeder", () => {
  for (const bad of ["", "  ", "0", "-3", "2,5", "2.5", "1e2", "abc", "4a", String(MAX_SERVINGS + 1), "99999999999999999999"]) {
    assert.equal(parseServings(bad), null, JSON.stringify(bad));
  }
});

test("clampServings sınırları korur", () => {
  assert.equal(clampServings(0), MIN_SERVINGS);
  assert.equal(clampServings(-5), MIN_SERVINGS);
  assert.equal(clampServings(MAX_SERVINGS + 1), MAX_SERVINGS);
  assert.equal(clampServings(7), 7);
});
