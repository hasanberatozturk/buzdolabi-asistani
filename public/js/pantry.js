import * as api from "./api.js";
import { clear, el } from "./dom.js";

const SEARCH_DELAY_MS = 250;

// Sunucudaki normalize() ile aynı kural (app/utils/text.py): İ/I/ı → i, küçük harf, tek boşluk.
const fold = (text) => text.trim().replace(/[İIı]/g, "i").toLowerCase().replace(/\s+/g, " ");

export function initPantry({ onChange }) {
  const input = document.querySelector("#ingredient-search");
  const results = document.querySelector("#search-results");
  const chips = document.querySelector("#pantry-chips");
  const status = document.querySelector("#pantry-status");
  const clearButton = document.querySelector("#clear-pantry");

  let items = [];
  let timer;
  let searchSeq = 0;

  function setStatus(message, isError = false) {
    status.textContent = message;
    status.classList.toggle("error", isError);
  }

  function renderChips() {
    clear(chips);
    clearButton.hidden = items.length === 0;
    if (items.length === 0) {
      chips.append(el("p", { class: "muted" }, "Henüz malzeme eklemedin."));
      return;
    }
    for (const item of items) {
      chips.append(
        el(
          "span",
          { class: "chip" },
          item.ingredient.name,
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
    afterPick();
    try {
      await api.addToPantry(ingredientId);
      await reload();
    } catch (error) {
      setStatus(error.message, true);
    }
  }

  async function createAndAdd(name) {
    afterPick();
    try {
      const ingredient = await api.createIngredient(name);
      await api.addToPantry(ingredient.id);
      await reload();
    } catch (error) {
      setStatus(error.message, true);
    }
  }

  // Seçim yapılır yapılmaz kutuyu temizle; istek sürerken yazmaya devam edilebilsin.
  function afterPick() {
    clearTimeout(timer);
    input.value = "";
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
    if (!event.target.closest(".search")) hideResults();
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
