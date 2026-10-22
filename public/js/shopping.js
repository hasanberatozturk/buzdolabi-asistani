import * as api from "./api.js";
import { clear, el } from "./dom.js";
import { formatQuantity } from "./scale.js";

const list = document.querySelector("#shopping-list");
const status = document.querySelector("#shopping-status");
const summary = document.querySelector("#shopping-summary");
const actions = document.querySelector("#shopping-actions");
const moveButton = document.querySelector("#move-checked");
const clearCheckedButton = document.querySelector("#clear-checked");
const clearAllButton = document.querySelector("#clear-all");

let items = [];
let reloadSeq = 0;

function setStatus(message, isError = false) {
  status.textContent = message;
  status.classList.toggle("error", isError);
}

function itemText(item) {
  const amount = [item.quantity != null ? formatQuantity(item.quantity) : "", item.unit ?? ""].filter(Boolean).join(" ");
  return amount ? `${amount} ${item.ingredient.name}` : item.ingredient.name;
}

function render() {
  clear(list);
  const checkedCount = items.filter((item) => item.checked).length;
  actions.hidden = items.length === 0;
  moveButton.disabled = checkedCount === 0;
  clearCheckedButton.disabled = checkedCount === 0;
  summary.textContent = items.length === 0 ? "" : `${items.length} malzeme, ${checkedCount} tanesi alındı.`;

  if (items.length === 0) {
    list.append(
      el(
        "li",
        { class: "muted" },
        "Alışveriş listen boş. Bir tarifin sayfasından eksik malzemeleri listeye ekleyebilirsin. ",
        el("a", { href: "/" }, "Tariflere git"),
      ),
    );
    return;
  }
  for (const item of items) {
    const checkbox = el("input", { type: "checkbox", "aria-label": `${item.ingredient.name} alındı` });
    checkbox.checked = item.checked;
    checkbox.addEventListener("change", () => toggle(item, checkbox.checked));
    list.append(
      el(
        "li",
        { class: item.checked ? "shopping-row done" : "shopping-row" },
        el("label", { class: "shopping-item" }, checkbox, el("span", {}, itemText(item))),
        el(
          "button",
          {
            type: "button",
            class: "chip-remove",
            "aria-label": `${item.ingredient.name} malzemesini listeden sil`,
            onclick: () => remove(item),
          },
          "×",
        ),
      ),
    );
  }
}

// Hızlı art arda işlemlerde eski yanıt yenisini ezmesin (bkz. pantry.js)
async function reload() {
  const seq = ++reloadSeq;
  const latest = await api.getShopping();
  if (seq !== reloadSeq) return;
  items = latest;
  setStatus("");
  render();
}

async function toggle(item, checked) {
  item.checked = checked; // anında göster; hata olursa geri al
  render();
  try {
    await api.updateShoppingItem(item.id, checked);
    await reload();
  } catch (error) {
    item.checked = !checked;
    render();
    setStatus(error.message, true);
  }
}

async function run(action, successMessage) {
  setStatus("");
  try {
    const result = await action();
    await reload();
    if (successMessage) setStatus(successMessage(result));
  } catch (error) {
    setStatus(error.message, true);
  }
}

function remove(item) {
  return run(() => api.removeShoppingItem(item.id));
}

moveButton.addEventListener("click", () =>
  run(api.moveShoppingToPantry, (result) => `${result.moved} malzeme buzdolabına taşındı.`),
);
clearCheckedButton.addEventListener("click", () => run(() => api.clearShopping(true)));
clearAllButton.addEventListener("click", () => {
  if (confirm("Alışveriş listesindeki tüm malzemeler silinsin mi?")) run(() => api.clearShopping(false));
});

reload().catch((error) => setStatus(error.message, true));
