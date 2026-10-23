import * as api from "./api.js";
import { clear, el } from "./dom.js";
import { fold } from "./text.js";

const SEARCH_DELAY_MS = 250;
const EXPIRY_SOON_DAYS = 3; // sunucudaki app/services/expiry.py::EXPIRY_SOON_DAYS ile aynı olmalı


export function initPantry({ onChange }) {
  const input = document.querySelector("#ingredient-search");
  const results = document.querySelector("#search-results");
  const chips = document.querySelector("#pantry-chips");
  const status = document.querySelector("#pantry-status");
  const clearButton = document.querySelector("#clear-pantry");
  const expiryInput = document.querySelector("#add-expiry");

  let items = [];
  let editingId = null; // tarihi o an düzenlenen buzdolabı kaydı
  let timer;
  let searchSeq = 0;

  function setStatus(message, isError = false) {
    status.textContent = message;
    status.classList.toggle("error", isError);
  }

  // Tarihi olanlar önce, en yakın bitenden başlayarak; tarihsizler eklenme sırasıyla sonda.
  function sortedItems() {
    const dated = items.filter((item) => item.days_left != null).sort((a, b) => a.days_left - b.days_left);
    return [...dated, ...items.filter((item) => item.days_left == null)];
  }

  function expiryLabel(item) {
    const days = item.days_left;
    if (days == null) return "📅 tarih ekle";
    if (days < 0) return `${-days} gün önce bitti`;
    if (days === 0) return "bugün bitiyor";
    if (days === 1) return "yarın bitiyor";
    return `${days} gün kaldı`;
  }

  function expiryClass(item) {
    const days = item.days_left;
    if (days == null) return "";
    if (days < 0) return " expired";
    return days <= EXPIRY_SOON_DAYS ? " soon" : "";
  }

  function expiryControl(item) {
    if (item.id !== editingId) {
      return el(
        "button",
        {
          type: "button",
          class: "chip-date",
          title: item.expires_on ? `Son kullanma: ${item.expires_on}` : "Son kullanma tarihi ekle",
          "aria-label": `${item.ingredient.name} son kullanma tarihini değiştir`,
          onclick: () => {
            editingId = item.id;
            renderChips();
            chips.querySelector(".chip-date-input")?.focus();
          },
        },
        expiryLabel(item),
      );
    }
    const dateInput = el("input", {
      type: "date",
      class: "chip-date-input",
      min: "2000-01-01",
      max: "2100-12-31",
      "aria-label": `${item.ingredient.name} son kullanma tarihi (silmek için alanı boşalt)`,
    });
    dateInput.value = item.expires_on ?? "";
    dateInput.addEventListener("change", () => saveExpiry(item, dateInput.value || null));
    // Seçim yapılmadan odak kaybolursa düzenlemeyi bırak (tarih seçici açılırken odak kısa süre oynayabilir)
    dateInput.addEventListener("blur", () => {
      setTimeout(() => {
        if (editingId === item.id) {
          editingId = null;
          renderChips();
        }
      }, 250);
    });
    return dateInput;
  }

  function renderChips() {
    clear(chips);
    clearButton.hidden = items.length === 0;
    if (items.length === 0) {
      chips.append(el("p", { class: "muted" }, "Henüz malzeme eklemedin."));
      return;
    }
    for (const item of sortedItems()) {
      chips.append(
        el(
          "span",
          { class: `chip${expiryClass(item)}` },
          item.ingredient.name,
          expiryControl(item),
          el(
            "button",
            {
              type: "button",
              class: "chip-remove",
              "aria-label": `${item.ingredient.name} malzemesini çıkar`,
              onclick: () => remove(item),
            },
            "×",
          ),
        ),
      );
    }
  }

  async function saveExpiry(item, expiresOn) {
    editingId = null;
    try {
      await api.updatePantryItem(item.id, expiresOn);
      await reload();
    } catch (error) {
      renderChips();
      setStatus(error.message, true);
    }
  }

  function hideResults() {
    searchSeq++;
    clear(results);
    results.hidden = true;
  }

  function showResults(options) {
    clear(results);
    results.hidden = false;
    if (options.length === 0) {
      results.append(el("li", { class: "muted result-empty" }, "Sonuç bulunamadı."));
      return;
    }
    for (const option of options) {
      results.append(
        el("li", {}, el("button", { type: "button", class: "result", onclick: option.action }, option.label)),
      );
    }
  }

  async function search() {
    const query = input.value.trim();
    if (!query) {
      hideResults();
      return;
    }
    const seq = ++searchSeq;
    try {
      const found = await api.searchIngredients(query);
      if (seq !== searchSeq) return; // eski yanıt, yenisi geldi
      const inPantry = new Set(items.map((item) => item.ingredient.id));
      const options = found
        .filter((ingredient) => !inPantry.has(ingredient.id))
        .map((ingredient) => ({ label: ingredient.name, action: () => add(ingredient.id) }));
      const key = fold(query);
      if (!found.some((ingredient) => fold(ingredient.name) === key)) {
        options.push({ label: `➕ “${query}” malzemesini yeni ekle`, action: () => createAndAdd(query) });
      }
      showResults(options);
    } catch (error) {
      if (seq !== searchSeq) return;
      hideResults();
      setStatus(error.message, true);
    }
  }

  async function add(ingredientId) {
    const expiresOn = expiryInput.value || null;
    afterPick();
    try {
      await api.addToPantry(ingredientId, expiresOn);
      await reload();
    } catch (error) {
      setStatus(error.message, true);
    }
  }

  async function createAndAdd(name) {
    const expiresOn = expiryInput.value || null;
    afterPick();
    try {
      const ingredient = await api.createIngredient(name);
      await api.addToPantry(ingredient.id, expiresOn);
      await reload();
    } catch (error) {
      setStatus(error.message, true);
    }
  }

  // Seçim yapılır yapılmaz kutuları temizle; istek sürerken yazmaya devam edilebilsin.
  function afterPick() {
    clearTimeout(timer);
    input.value = "";
    expiryInput.value = "";
    hideResults();
    input.focus();
  }

  async function remove(item) {
    try {
      await api.removeFromPantry(item.id);
      await reload();
    } catch (error) {
      setStatus(error.message, true);
    }
  }

  // Hızlı art arda eklemede iki yükleme yarışır; yavaş dönen eski yanıt yenisini ezmesin.
  let reloadSeq = 0;
  async function reload() {
    const seq = ++reloadSeq;
    setStatus("");
    const latest = await api.getPantry();
    if (seq !== reloadSeq) return;
    items = latest;
    renderChips();
    onChange(items);
  }

  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(search, SEARCH_DELAY_MS);
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "Escape") hideResults();
    if (event.key === "Enter") {
      event.preventDefault();
      clearTimeout(timer);
      const first = results.querySelector("button.result");
      if (first && !results.hidden) first.click();
      else search();
    }
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".search, .expiry-field")) hideResults();
  });
  clearButton.addEventListener("click", async () => {
    try {
      await api.clearPantry();
      await reload();
    } catch (error) {
      setStatus(error.message, true);
    }
  });

  return {
    async load() {
      setStatus("Yükleniyor…");
      try {
        await reload();
      } catch (error) {
        chips.replaceChildren();
        setStatus(error.message, true);
      }
    },
  };
}
