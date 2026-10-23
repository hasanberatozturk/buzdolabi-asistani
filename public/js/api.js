import { buildMatchQuery } from "./tags.js";

// Tüm fetch çağrıları sadece bu dosyada; diğer dosyalar bu fonksiyonları kullanır.

// Yazma istekleri sunucuda ADMIN_KEY ile korunur. Anahtar koda gömülmez: sunucu 401
// dönünce bir kez sorulur ve bu tarayıcının localStorage'ında saklanır.
const KEY_STORAGE = "adminKey";

function readKey() {
  try {
    return localStorage.getItem(KEY_STORAGE);
  } catch {
    return null;
  }
}

function writeKey(key) {
  try {
    if (key) localStorage.setItem(KEY_STORAGE, key);
    else localStorage.removeItem(KEY_STORAGE);
  } catch {
    // Depolama kapalıysa anahtar her seferinde sorulur
  }
}

async function request(path, options = {}, askedForKey = false) {
  const isWrite = (options.method ?? "GET") !== "GET";
  const headers = { ...options.headers };
  const sentKey = isWrite ? readKey() : null;
  if (sentKey) headers["X-API-Key"] = sentKey;

  let response;
  try {
    response = await fetch(path, { ...options, headers });
  } catch {
    throw new Error("Sunucuya ulaşılamadı. Bağlantını kontrol edip tekrar dene.");
  }

  if (response.status === 401 && isWrite) {
    writeKey(null);
    const wrong = Boolean(sentKey) || askedForKey;
    const key = window.prompt(wrong ? "Anahtar geçersiz. Yönetici anahtarını yeniden gir:" : "Bu işlem için yönetici anahtarı gerekli:");
    if (key && key.trim()) {
      writeKey(key.trim());
      return request(path, options, true);
    }
    throw new Error("Bu işlem için yönetici anahtarı gerekli.");
  }
  if (response.status === 204) return null;

  let body = null;
  try {
    body = await response.json();
  } catch {
    // JSON olmayan yanıt: aşağıda genel hata mesajı verilir
  }
  if (!response.ok) {
    let message = "Bir şeyler ters gitti. Lütfen tekrar dene.";
    if (body && typeof body.detail === "string") message = body.detail;
    else if (response.status === 422) message = "Girdiğin bilgilerde bir sorun var. Alanları kontrol edip tekrar dene.";
    throw new Error(message);
  }
  return body;
}

function sendJson(method, path, data) {
  return request(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

function postJson(path, data) {
  return sendJson("POST", path, data);
}

export function searchIngredients(q) {
  return request(`/api/ingredients?q=${encodeURIComponent(q)}`);
}

export function createIngredient(name) {
  return postJson("/api/ingredients", { name });
}

export function getPantry() {
  return request("/api/pantry");
}

export function addToPantry(ingredientId, expiresOn = null) {
  return postJson("/api/pantry", { ingredient_id: ingredientId, expires_on: expiresOn });
}

// expiresOn: "YYYY-MM-DD" ya da null (tarihi sil)
export function updatePantryItem(itemId, expiresOn) {
  return sendJson("PATCH", `/api/pantry/${itemId}`, { expires_on: expiresOn });
}

export function removeFromPantry(itemId) {
  return request(`/api/pantry/${itemId}`, { method: "DELETE" });
}

export function clearPantry() {
  return request("/api/pantry", { method: "DELETE" });
}

export function getRecipe(id) {
  return request(`/api/recipes/${id}`);
}

export function createRecipe(data) {
  return postJson("/api/recipes", data);
}

export function updateRecipe(id, data) {
  return sendJson("PUT", `/api/recipes/${id}`, data);
}

export function deleteRecipe(id) {
  return request(`/api/recipes/${id}`, { method: "DELETE" });
}

export function getShopping() {
  return request("/api/shopping");
}

// Tarifin eksik malzemelerini listeye ekler; servings verilirse miktarlar o porsiyona göre ölçeklenir.
export function addMissingToShopping(recipeId, servings = null) {
  return postJson("/api/shopping/from-recipe", { recipe_id: recipeId, servings });
}

export function updateShoppingItem(itemId, checked) {
  return sendJson("PATCH", `/api/shopping/${itemId}`, { checked });
}

export function removeShoppingItem(itemId) {
  return request(`/api/shopping/${itemId}`, { method: "DELETE" });
}

export function clearShopping(onlyChecked = false) {
  return request(`/api/shopping?only_checked=${onlyChecked}`, { method: "DELETE" });
}

export function moveShoppingToPantry() {
  return request("/api/shopping/move-to-pantry", { method: "POST" });
}

// filters: { tags: ["kahvaltı"], maxMinutes: 30 } (ikisi de isteğe bağlı; etiketlerin hepsi aranır)
export function matchRecipes(maxMissing, filters = {}) {
  return request(`/api/recipes/match?${buildMatchQuery({ maxMissing, ...filters })}`);
}

export function getTags() {
  return request("/api/tags");
}
