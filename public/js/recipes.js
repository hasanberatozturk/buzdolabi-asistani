import * as api from "./api.js";
import { clear, el } from "./dom.js";

export function initRecipes() {
  const list = document.querySelector("#recipe-list");
  const status = document.querySelector("#recipe-status");
  const onlyReady = document.querySelector("#only-ready");

  let pantryCount = 0;
  let seq = 0;

  function setStatus(message, isError = false) {
    status.textContent = message;
    status.classList.toggle("error", isError);
  }

  function renderSkeleton() {
    clear(list);
    for (let i = 0; i < 3; i++) list.append(el("div", { class: "card skeleton", "aria-hidden": "true" }));
  }

  function renderCard(match) {
    const percent = Math.round(match.match_ratio * 100);
    return el(
      "article",
      { class: "card" },
      el("h3", {}, el("a", { href: `/recipe.html?id=${match.recipe_id}` }, match.title)),
      match.prep_minutes != null && el("p", { class: "muted" }, `⏱ ${match.prep_minutes} dk`),
      el(
        "div",
        { class: "bar", role: "img", "aria-label": `%${percent} eşleşme` },
        el("div", { class: "bar-fill", style: `width: ${percent}%` }),
      ),
      el(
        "p",
        { class: match.missing.length ? "missing" : "ready" },
        match.missing.length ? `%${percent} eşleşme · Eksik: ${match.missing.join(", ")}` : "Tüm malzemeler hazır ✅",
      ),
    );
  }

  async function refresh() {
    const current = ++seq;
    setStatus("");
    if (pantryCount === 0) {
      clear(list);
      setStatus("Buzdolabına malzeme ekleyince tarif önerileri burada görünecek.");
      return;
    }
    renderSkeleton();
    try {
      const matches = await api.matchRecipes(onlyReady.checked ? 0 : 2);
      if (current !== seq) return;
      clear(list);
      if (matches.length === 0) {
        setStatus("Bu malzemelerle yapılabilecek tarif bulunamadı. Biraz daha malzeme eklemeyi dene.");
        return;
      }
      list.append(...matches.map(renderCard));
    } catch (error) {
      if (current !== seq) return;
      clear(list);
      setStatus(error.message, true);
    }
  }

  onlyReady.addEventListener("change", refresh);

  return {
    update(count) {
      pantryCount = count;
      return refresh();
    },
  };
}
