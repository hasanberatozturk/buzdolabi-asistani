// Tüm fetch çağrıları sadece bu dosyada; diğer dosyalar bu fonksiyonları kullanır.

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(path, options);
  } catch {
    throw new Error("Sunucuya ulaşılamadı. Bağlantını kontrol edip tekrar dene.");
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

export function addToPantry(ingredientId) {
  return postJson("/api/pantry", { ingredient_id: ingredientId });
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

export function matchRecipes(maxMissing) {
  return request(`/api/recipes/match?max_missing=${maxMissing}`);
}
