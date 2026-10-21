import * as api from "./api.js";
import { clear, el } from "./dom.js";

const root = document.querySelector("#recipe");

function showMessage(message, isError = false) {
  clear(root);
  root.append(el("p", { class: isError ? "status error" : "status", role: "alert" }, message));
}

function formatAmount(row) {
  const parts = [];
  if (row.quantity != null) parts.push(row.quantity.toLocaleString("tr-TR"));
  if (row.unit) parts.push(row.unit);
  return parts.join(" ");
}

function renderIngredient(row) {
  const amount = formatAmount(row);
  return el(
    "li",
    { class: row.in_pantry ? "have" : "lack" },
    el("span", { class: "mark", role: "img", "aria-label": row.in_pantry ? "Var" : "Eksik" }, row.in_pantry ? "✅" : "❌"),
    el(
      "span",
      {},
      amount && el("strong", {}, `${amount} `),
      row.name,
      row.is_optional && el("span", { class: "muted" }, " (isteğe bağlı)"),
    ),
  );
}

function renderRecipe(recipe) {
  document.title = `${recipe.title} · Buzdolabı Asistanı`;
  const lacking = recipe.ingredients.filter((row) => !row.is_optional && !row.in_pantry).length;
  const steps = recipe.instructions
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  clear(root);
  root.append(
    el("h2", { class: "recipe-title" }, recipe.title),
    el(
      "p",
      { class: "muted" },
      [
        recipe.prep_minutes != null && `⏱ ${recipe.prep_minutes} dk`,
        recipe.servings != null && `🍽 ${recipe.servings} porsiyon`,
      ]
        .filter(Boolean)
        .join(" · "),
    ),
    recipe.description && el("p", {}, recipe.description),

    el("h3", {}, "Malzemeler"),
    el(
      "p",
      { class: lacking ? "missing" : "ready" },
      lacking ? `${lacking} zorunlu malzeme eksik.` : "Tüm zorunlu malzemeler hazır ✅",
    ),
    el("ul", { class: "ingredient-list" }, recipe.ingredients.map(renderIngredient)),

    el("h3", {}, "Yapılışı"),
    el("ol", { class: "steps" }, steps.map((step) => el("li", {}, step))),
  );
}

async function load() {
  const id = new URLSearchParams(location.search).get("id");
  if (!/^\d+$/.test(id ?? "")) {
    showMessage("Geçersiz tarif adresi.", true);
    return;
  }
  clear(root);
  root.append(el("div", { class: "card skeleton", "aria-hidden": "true" }));
  try {
    renderRecipe(await api.getRecipe(id));
  } catch (error) {
    showMessage(error.message, true);
  }
}

load();
