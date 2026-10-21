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
    const detail = body && typeof body.detail === "string" ? body.detail : null;
    throw new Error(detail ?? "Bir şeyler ters gitti. Lütfen tekrar dene.");
  }
  return body;
}

function postJson(path, data) {
  return request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
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

export function matchRecipes(maxMissing) {
  return request(`/api/recipes/match?max_missing=${maxMissing}`);
}
