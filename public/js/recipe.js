import * as api from "./api.js";
import { clear, el } from "./dom.js";
import {
  MAX_SERVINGS,
  MIN_SERVINGS,
  clampServings,
  formatQuantity,
  parseServings,
  scaleQuantity,
} from "./scale.js";

const root = document.querySelector("#recipe");

function showMessage(message, isError = false) {
  clear(root);
  root.append(el("p", { class: isError ? "status error" : "status", role: "alert" }, message));
}

// base: tarifin kayıtlı porsiyonu (yoksa null), target: ekranda seçili porsiyon
function formatAmount(row, base, target) {
  const parts = [];
  if (row.quantity != null) {
    const quantity = base ? scaleQuantity(row.quantity, base, target) : row.quantity;
    parts.push(formatQuantity(quantity));
  }
  if (row.unit) parts.push(row.unit);
  return parts.join(" ");
}

function renderIngredient(row, base, target) {
  const amount = formatAmount(row, base, target);
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

// Porsiyon seçici: −/+ düğmeleri ve sayı alanı. Geçerli bir değer oluştukça onChange(porsiyon) çağrılır.
function servingsControl(base, onChange) {
  let current = base;

  const input = el("input", {
    type: "number",
    id: "servings-input",
    min: String(MIN_SERVINGS),
    max: String(MAX_SERVINGS),
    step: "1",
    inputmode: "numeric",
    "aria-label": "Porsiyon sayısı",
  });
  const decrease = el("button", { type: "button", class: "icon-button", "aria-label": "Porsiyonu azalt" }, "−");
  const increase = el("button", { type: "button", class: "icon-button", "aria-label": "Porsiyonu artır" }, "+");
  const reset = el("button", { type: "button", class: "link-button", hidden: true }, `Orijinale dön (${base})`);
  const note = el("p", { class: "muted servings-note", "aria-live": "polite" });

  function apply(next, rewriteInput) {
    current = next;
    if (rewriteInput) input.value = String(next);
    decrease.disabled = next <= MIN_SERVINGS;
    increase.disabled = next >= MAX_SERVINGS;
    reset.hidden = next === base;
    note.textContent = next === base ? "" : `Miktarlar ${next} porsiyon için hesaplandı (×${formatQuantity(next / base)}).`;
    onChange(next);
  }

  decrease.addEventListener("click", () => apply(clampServings(current - 1), true));
  increase.addEventListener("click", () => apply(clampServings(current + 1), true));
  reset.addEventListener("click", () => apply(base, true));
  input.addEventListener("input", () => {
    const parsed = parseServings(input.value);
    if (parsed !== null) apply(parsed, false); // yazarken alanı elle düzeltme
  });
  // Geçersiz/boş bırakılırsa son geçerli değere dön
  input.addEventListener("change", () => {
    input.value = String(current);
  });

  input.value = String(base);
  apply(base, true);

  return el(
    "div",
    { class: "servings" },
    el(
      "div",
      { class: "servings-row", role: "group", "aria-label": "Porsiyon sayısı" },
      el("label", { for: "servings-input" }, "Porsiyon"),
      decrease,
      input,
      increase,
      reset,
    ),
    note,
  );
}

// Eksik malzemeleri (seçili porsiyona göre ölçeklenmiş miktarlarla) alışveriş listesine ekler.
function shoppingButton(recipe, getServings) {
  const message = el("p", { class: "status", role: "status", "aria-live": "polite" });
  const button = el("button", { type: "button", class: "secondary" }, "🛒 Eksik malzemeleri alışveriş listesine ekle");

  button.addEventListener("click", async () => {
    button.disabled = true;
    message.classList.remove("error");
    message.replaceChildren();
    try {
      const result = await api.addMissingToShopping(recipe.id, getServings());
      let text;
      if (result.nothing_missing) text = "Eksik malzeme yok.";
      else if (result.added === 0) text = "Eksik malzemelerin hepsi zaten listede.";
      else {
        text = `${result.added} malzeme listeye eklendi.`;
        if (result.already_listed > 0) text += ` ${result.already_listed} tanesi zaten listedeydi.`;
      }
      message.append(`${text} `, el("a", { href: "/shopping.html" }, "Listeyi gör"));
    } catch (error) {
      message.classList.add("error");
      message.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });

  return el("div", { class: "shopping-add" }, button, message);
}

function renderRecipe(recipe) {
  document.title = `${recipe.title} · Buzdolabı Asistanı`;
  const lacking = recipe.ingredients.filter((row) => !row.is_optional && !row.in_pantry).length;
  const steps = recipe.instructions
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  const base = recipe.servings; // kayıtlı porsiyon yoksa ölçekleme yapılmaz
  let selectedServings = base;
  const ingredientList = el("ul", { class: "ingredient-list" });
  const stepsNote = el("p", { class: "muted", hidden: true });
  const refresh = (target) => {
    selectedServings = target;
    ingredientList.replaceChildren(...recipe.ingredients.map((row) => renderIngredient(row, base, target)));
    stepsNote.hidden = !base || target === base;
    stepsNote.textContent = `Not: Adımlarda yazan miktarlar tarifin orijinal (${base} porsiyon) hâline göredir.`;
  };
  const control = base ? servingsControl(base, refresh) : null;
  if (!control) refresh(base);

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
    ...(recipe.description ? [el("p", {}, recipe.description)] : []),

    el("h3", {}, "Malzemeler"),
    el(
      "p",
      { class: lacking ? "missing" : "ready" },
      lacking ? `${lacking} zorunlu malzeme eksik.` : "Tüm zorunlu malzemeler hazır ✅",
    ),
    ...(control ? [control] : []),
    ingredientList,
    ...(lacking > 0 ? [shoppingButton(recipe, () => selectedServings)] : []),

    el("h3", {}, "Yapılışı"),
    stepsNote,
    el("ol", { class: "steps" }, steps.map((step) => el("li", {}, step))),

    el(
      "div",
      { class: "actions" },
      el("a", { class: "button secondary", href: `/recipe-form.html?id=${recipe.id}` }, "Düzenle"),
      el("button", { type: "button", class: "danger", onclick: (e) => remove(recipe, e.currentTarget) }, "Sil"),
    ),
    el("p", { id: "action-error", class: "status error", role: "alert" }),
  );
}

async function remove(recipe, button) {
  if (!confirm(`“${recipe.title}” tarifini silmek istediğine emin misin? Bu işlem geri alınamaz.`)) return;
  const errorBox = document.querySelector("#action-error");
  errorBox.textContent = "";
  button.disabled = true;
  try {
    await api.deleteRecipe(recipe.id);
    location.href = "/";
  } catch (error) {
    errorBox.textContent = error.message;
    button.disabled = false;
  }
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
