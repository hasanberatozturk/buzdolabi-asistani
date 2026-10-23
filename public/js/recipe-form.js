import * as api from "./api.js";
import { clear, el } from "./dom.js";
import { MAX_TAG_LENGTH, MAX_TAGS, hasTag, parseTags, toggleTag } from "./tags.js";
import { imageUrlProblem, normalizeImageUrl } from "./url.js";

const SUGGEST_DELAY_MS = 250;

const form = document.querySelector("#recipe-form");
const formTitle = document.querySelector("#form-title");
const status = document.querySelector("#form-status");
const errorBox = document.querySelector("#form-error");
const rows = document.querySelector("#ingredient-rows");
const suggestions = document.querySelector("#ingredient-suggestions");
const submitButton = document.querySelector("#submit");
const cancelLink = document.querySelector("#cancel");
const tagsInput = document.querySelector("#tags");
const imageInput = document.querySelector("#image-url");
const imageStatus = document.querySelector("#image-status");
const imagePreview = document.querySelector("#image-preview");
const tagSuggestions = document.querySelector("#tag-suggestions");

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

// Adı boş ama başka alanı dolu (miktar, birim, "isteğe bağlı") ilk satırı döndürür.
// Böyle bir satır sessizce atılırsa tarif o malzeme olmadan kaydedilirdi.
function findNamelessRow() {
  return [...rows.querySelectorAll(".ingredient-row")].find((row) => {
    const hasName = row.querySelector(".ing-name").value.trim() !== "";
    const hasOther =
      row.querySelector(".ing-quantity").value !== "" ||
      row.querySelector(".ing-unit").value.trim() !== "" ||
      row.querySelector(".ing-optional").checked;
    return !hasName && hasOther;
  });
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
    tags: parseTags(tagsInput.value),
    image_url: normalizeImageUrl(imageInput.value),
  };
}

function validate(data) {
  if (!data.title) return "Başlık boş olamaz.";
  if (data.ingredients.length === 0) return "En az bir malzeme eklemelisin.";
  if (!data.instructions) return "Yapılış adımlarını yazmalısın.";
  const imageProblem = imageUrlProblem(imageInput.value);
  if (imageProblem) return imageProblem;
  if (data.tags.length > MAX_TAGS) return `En çok ${MAX_TAGS} etiket ekleyebilirsin.`;
  if (data.tags.some((tag) => tag.length > MAX_TAG_LENGTH)) return `Her etiket en çok ${MAX_TAG_LENGTH} karakter olabilir.`;
  return null;
}

function fill(recipe) {
  document.querySelector("#title").value = recipe.title;
  document.querySelector("#description").value = recipe.description ?? "";
  document.querySelector("#prep-minutes").value = recipe.prep_minutes ?? "";
  document.querySelector("#servings").value = recipe.servings ?? "";
  document.querySelector("#instructions").value = recipe.instructions;
  tagsInput.value = recipe.tags.join(", ");
  updateSuggestionStates();
  imageInput.value = recipe.image_url ?? "";
  updateImagePreview();
  clear(rows);
  recipe.ingredients.forEach(addRow);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorBox.textContent = "";
  const nameless = findNamelessRow();
  if (nameless) {
    errorBox.textContent = "Miktar, birim veya “isteğe bağlı” işaretlediğin bir satırın malzeme adı boş.";
    nameless.querySelector(".ing-name").focus();
    return;
  }
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

// Mevcut etiketleri tek tıkla ekleyip çıkarmak için düğmeler (yazı alanı ile eşzamanlı tutulur)
function updateSuggestionStates() {
  const current = parseTags(tagsInput.value);
  for (const button of tagSuggestions.querySelectorAll("button")) {
    button.setAttribute("aria-pressed", String(hasTag(current, button.dataset.tag)));
  }
}

async function loadTagSuggestions() {
  try {
    const tags = await api.getTags();
    if (tags.length === 0) return;
    for (const tag of tags) {
      const button = el(
        "button",
        {
          type: "button",
          class: "filter-chip",
          "data-tag": tag.name,
          onclick: () => {
            tagsInput.value = toggleTag(parseTags(tagsInput.value), tag.name).join(", ");
            updateSuggestionStates();
          },
        },
        tag.name,
      );
      tagSuggestions.append(button);
    }
    tagSuggestions.hidden = false;
    updateSuggestionStates();
  } catch {
    // Öneriler alınamazsa etiketler yine elle yazılabilir
  }
}

tagsInput.addEventListener("input", updateSuggestionStates);

// Görsel önizlemesi: adres geçerliyse gösterilir; yüklenemezse bilgi verilir (kaydetmeyi engellemez)
function showImageStatus(message) {
  imageStatus.textContent = message;
  imageStatus.hidden = !message;
}

function updateImagePreview() {
  showImageStatus("");
  imagePreview.hidden = true;
  const problem = imageUrlProblem(imageInput.value);
  if (problem) {
    showImageStatus(problem);
    return;
  }
  const url = normalizeImageUrl(imageInput.value);
  if (url) imagePreview.src = url;
}

imagePreview.addEventListener("load", () => {
  imagePreview.hidden = false;
  showImageStatus("");
});
imagePreview.addEventListener("error", () => {
  imagePreview.hidden = true;
  showImageStatus("Görsel yüklenemedi: adres yanlış olabilir ya da görsel herkese açık değil. Yine de kaydedebilirsin.");
});
imageInput.addEventListener("change", updateImagePreview);

loadTagSuggestions();
init();
