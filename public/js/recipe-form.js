import * as api from "./api.js";
import { clear, el } from "./dom.js";

const SUGGEST_DELAY_MS = 250;

const form = document.querySelector("#recipe-form");
const formTitle = document.querySelector("#form-title");
const status = document.querySelector("#form-status");
const errorBox = document.querySelector("#form-error");
const rows = document.querySelector("#ingredient-rows");
const suggestions = document.querySelector("#ingredient-suggestions");
const submitButton = document.querySelector("#submit");
const cancelLink = document.querySelector("#cancel");

const recipeId = new URLSearchParams(location.search).get("id");
let suggestTimer;
let suggestSeq = 0;

function addRow(row = {}) {
  const name = el("input", {
    type: "text",
    class: "ing-name",
    list: "ingredient-suggestions",
    placeholder: "Malzeme",
    "aria-label": "Malzeme adı",
    maxlength: "100",
    autocomplete: "off",
    required: true,
  });
  name.value = row.name ?? "";
  name.addEventListener("input", () => scheduleSuggest(name.value));

  const quantity = el("input", {
    type: "number",
    class: "ing-quantity",
    placeholder: "Miktar",
    "aria-label": "Miktar",
    min: "0",
    step: "any",
    inputmode: "decimal",
  });
  quantity.value = row.quantity ?? "";

  const unit = el("input", {
    type: "text",
    class: "ing-unit",
    placeholder: "Birim",
    "aria-label": "Birim",
    maxlength: "50",
  });
  unit.value = row.unit ?? "";

  const optional = el("input", { type: "checkbox", class: "ing-optional" });
  optional.checked = Boolean(row.is_optional);

  rows.append(
    el(
      "div",
      { class: "ingredient-row" },
      name,
      quantity,
      unit,
      el("label", { class: "optional-label" }, optional, "İsteğe bağlı"),
      el(
        "button",
        { type: "button", class: "icon-button", "aria-label": "Malzemeyi sil", onclick: (e) => removeRow(e.currentTarget) },
        "×",
      ),
    ),
  );
  return name;
}

function removeRow(button) {
  if (rows.children.length > 1) button.closest(".ingredient-row").remove();
  else button.closest(".ingredient-row").querySelectorAll("input").forEach((input) => {
    if (input.type === "checkbox") input.checked = false;
    else input.value = "";
  });
}

function scheduleSuggest(text) {
  clearTimeout(suggestTimer);
  const query = text.trim();
  if (!query) return;
  suggestTimer = setTimeout(async () => {
    const seq = ++suggestSeq;
    try {
      const found = await api.searchIngredients(query);
      if (seq !== suggestSeq) return;
      clear(suggestions);
      suggestions.append(...found.map((ingredient) => el("option", { value: ingredient.name })));
    } catch {
      // Öneri alınamazsa form yine de çalışır
    }
  }, SUGGEST_DELAY_MS);
}

function numberOrNull(value) {
  return value === "" ? null : Number(value);
}

function collect() {
  const ingredients = [...rows.querySelectorAll(".ingredient-row")]
    .map((row) => ({
      name: row.querySelector(".ing-name").value.trim(),
      quantity: numberOrNull(row.querySelector(".ing-quantity").value),
      unit: row.querySelector(".ing-unit").value.trim() || null,
      is_optional: row.querySelector(".ing-optional").checked,
    }))
    .filter((row) => row.name);

  return {
    title: document.querySelector("#title").value.trim(),
    description: document.querySelector("#description").value.trim() || null,
    prep_minutes: numberOrNull(document.querySelector("#prep-minutes").value),
    servings: numberOrNull(document.querySelector("#servings").value),
    instructions: document.querySelector("#instructions").value.trim(),
    ingredients,
  };
}

function validate(data) {
  if (!data.title) return "Başlık boş olamaz.";
  if (data.ingredients.length === 0) return "En az bir malzeme eklemelisin.";
  if (!data.instructions) return "Yapılış adımlarını yazmalısın.";
  return null;
}

function fill(recipe) {
  document.querySelector("#title").value = recipe.title;
  document.querySelector("#description").value = recipe.description ?? "";
  document.querySelector("#prep-minutes").value = recipe.prep_minutes ?? "";
  document.querySelector("#servings").value = recipe.servings ?? "";
  document.querySelector("#instructions").value = recipe.instructions;
  clear(rows);
  recipe.ingredients.forEach(addRow);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorBox.textContent = "";
  const data = collect();
  const problem = validate(data);
  if (problem) {
    errorBox.textContent = problem;
    return;
  }

  submitButton.disabled = true;
  submitButton.textContent = "Kaydediliyor…";
  try {
    const saved = recipeId ? await api.updateRecipe(recipeId, data) : await api.createRecipe(data);
    location.href = `/recipe.html?id=${saved.id}`;
  } catch (error) {
    errorBox.textContent = error.message;
    submitButton.disabled = false;
    submitButton.textContent = "Kaydet";
  }
});

document.querySelector("#add-ingredient").addEventListener("click", () => addRow().focus());

async function init() {
  if (recipeId === null) {
    addRow();
    form.hidden = false;
    return;
  }
  if (!/^\d+$/.test(recipeId)) {
    status.textContent = "Geçersiz tarif adresi.";
    status.classList.add("error");
    return;
  }

  formTitle.textContent = "Tarifi düzenle";
  cancelLink.href = `/recipe.html?id=${recipeId}`;
  status.textContent = "Yükleniyor…";
  try {
    const recipe = await api.getRecipe(recipeId);
    document.title = `${recipe.title} düzenleniyor · Buzdolabı Asistanı`;
    fill(recipe);
    status.textContent = "";
    form.hidden = false;
  } catch (error) {
    status.textContent = error.message;
    status.classList.add("error");
  }
}

init();
