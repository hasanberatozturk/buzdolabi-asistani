import assert from "node:assert/strict";
import { test } from "node:test";

import { MAX_IMAGE_URL_LENGTH, imageUrlProblem, normalizeImageUrl } from "../../public/js/url.js";

// Sunucu tarafındaki tests/test_images.py ile aynı örnekler

test("geçerli https adresleri kabul edilir", () => {
  for (const good of [
    "https://example.com/foto.jpg",
    "HTTPS://Example.com/Foto.JPG",
    "https://cdn.example.com/a/b/c.png?w=600&q=80#x",
    "https://example.com:8443/a.jpg",
    "https://sub.example.co.uk/%C3%A7.jpg",
    "  https://example.com/foto.jpg  ",
  ]) {
    assert.equal(imageUrlProblem(good), null, good);
  }
});

test("boş adres geçerlidir (görsel yok)", () => {
  assert.equal(imageUrlProblem(""), null);
  assert.equal(imageUrlProblem("   "), null);
});

test("https olmayan ya da bozuk adresler reddedilir", () => {
  for (const bad of [
    "http://example.com/a.jpg",
    "javascript:alert(1)",
    "data:image/png;base64,AAAA",
    "//example.com/a.jpg",
    "ftp://example.com/a.jpg",
    "https://",
    "https:///a.jpg",
    "https:example.com/a.jpg",
    "example.com/a.jpg",
    "https://user:pass@example.com/a.jpg",
    "https://kullanici@example.com/a.jpg",
    "https://@example.com/a.jpg",
    "https://exa mple.com/a.jpg",
    "https://example.com/a b.jpg",
    "https://example.com/a.jpg\nX",
  ]) {
    assert.notEqual(imageUrlProblem(bad), null, JSON.stringify(bad));
  }
});

test("500 karakterden uzun adres reddedilir, tam 500 kabul edilir", () => {
  const prefix = "https://example.com/";
  assert.equal(imageUrlProblem(prefix + "a".repeat(MAX_IMAGE_URL_LENGTH - prefix.length)), null);
  assert.match(imageUrlProblem(prefix + "a".repeat(MAX_IMAGE_URL_LENGTH)), /500/);
});

test("hata mesajları kullanıcıya yönelik Türkçe metindir", () => {
  assert.equal(imageUrlProblem("http://example.com/a.jpg"), "Görsel adresi https:// ile başlamalı.");
  assert.equal(imageUrlProblem("https://a@b.com/x"), "Adres kullanıcı adı veya şifre içeremez.");
});

test("normalizeImageUrl kırpar, boşsa null döndürür", () => {
  assert.equal(normalizeImageUrl("  https://example.com/a.jpg "), "https://example.com/a.jpg");
  assert.equal(normalizeImageUrl("   "), null);
  assert.equal(normalizeImageUrl(""), null);
});
