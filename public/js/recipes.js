import * as api from "./api.js";
import { clear, el, image } from "./dom.js";
import { hasActiveFilters } from "./tags.js";

const PAGE_SIZE = 12; // "Tüm tarifler" görünümünde her seferinde getirilen tarif sayısı

// İki görünüm: "match" (buzdolabına göre öneriler) ve "all" (tüm tarifler, sayfalı).
export function initRecipes({ filters: initialFilters = { tags: [], maxMinutes: null, view: "match" } } = {}) {
  const list = document.querySelector("#recipe-list");
  const status = document.querySelector("#recipe-status");
  const onlyReady = document.querySelector("#only-ready");
  const title = document.querySelector("#recipes-title");
  const more = document.querySelector("#recipe-more");

  let pantryCount = 0;
  let filters = initialFilters;
  let seq = 0;
  let shown = []; // "Tüm tarifler" görünümünde şimdiye kadar getirilenler
  let total = 0;

  const isAll = () => filters.view === "all";

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
    // CSP (style-src 'self') satır içi style özniteliğini engeller; CSSOM ile ayarlanır.
    const fill = el("div", { class: "bar-fill" });
    fill.style.width = `${percent}%`;
    return el(
      "article",
      { class: match.expiring.length ? "card has-expiring" : "card" },
      match.image_url && image(match.image_url, match.title, "card-image"),
      el("h3", {}, el("a", { href: `/recipe.html?id=${match.recipe_id}` }, match.title)),
      match.prep_minutes != null && el("p", { class: "muted" }, `⏱ ${match.prep_minutes} dk`),
      match.tags.length > 0 && el("p", { class: "muted card-tags" }, match.tags.join(" · ")),
      el(
        "div",
        { class: "bar", role: "img", "aria-label": `%${percent} eşleşme` },
        fill,
      ),
      match.expiring.length > 0 && el("p", { class: "expiring" }, `⏰ Yakında bozulacak: ${match.expiring.join(", ")}`),
      el(
        "p",
        { class: match.missing.length ? "missing" : "ready" },
        match.missing.length ? `%${percent} eşleşme · Eksik: ${match.missing.join(", ")}` : "Tüm malzemeler hazır ✅",
      ),
    );
  }

  function renderListCard(item) {
    const meta = [item.prep_minutes != null && `⏱ ${item.prep_minutes} dk`, item.servings != null && `🍽 ${item.servings} porsiyon`]
      .filter(Boolean)
      .join(" · ");
    return el(
      "article",
      { class: "card" },
      item.image_url && image(item.image_url, item.title, "card-image"),
      el("h3", {}, el("a", { href: `/recipe.html?id=${item.id}` }, item.title)),
      meta && el("p", { class: "muted" }, meta),
      item.tags.length > 0 && el("p", { class: "muted card-tags" }, item.tags.join(" · ")),
      item.description && el("p", { class: "card-desc" }, item.description),
    );
  }

  // --- Tüm tarifler görünümü ---------------------------------------------------------------

  function renderMore(loading = false) {
    clear(more);
    more.hidden = shown.length === 0;
    if (shown.length === 0) return;
    more.append(el("p", { class: "muted" }, `${shown.length} / ${total} tarif`));
    if (shown.length < total) {
      const button = el("button", { type: "button", class: "secondary" }, loading ? "Yükleniyor…" : "Daha fazla göster");
      button.disabled = loading;
      button.addEventListener("click", () => loadAll(seq, false));
      more.append(button);
    }
  }

  function renderAll() {
    clear(list);
    if (shown.length === 0) {
      setStatus(
        hasActiveFilters(filters)
          ? "Bu filtrelere uyan tarif yok. Filtreleri değiştirmeyi dene."
          : "Henüz tarif yok. İlk tarifini ekleyebilirsin.",
      );
    }
    list.append(...shown.map(renderListCard));
    renderMore();
  }

  async function loadAll(current, reset) {
    if (reset) {
      shown = [];
      total = 0;
      renderSkeleton();
    } else {
      renderMore(true);
    }
    try {
      const page = await api.getRecipes({
        limit: PAGE_SIZE,
        offset: shown.length,
        tags: filters.tags,
        maxMinutes: filters.maxMinutes,
      });
      if (current !== seq) return; // filtre değişti, bu yanıt eski
      shown = [...shown, ...page.items];
      total = page.total;
      renderAll();
    } catch (error) {
      if (current !== seq) return;
      if (reset) clear(list);
      else renderMore();
      setStatus(error.message, true);
    }
  }

  // --- Buzdolabına göre öneriler -----------------------------------------------------------

  async function loadMatches(current) {
    if (pantryCount === 0) {
      clear(list);
      setStatus("Buzdolabına malzeme ekleyince tarif önerileri burada görünecek.");
      return;
    }
    renderSkeleton();
    try {
      const matches = await api.matchRecipes(onlyReady.checked ? 0 : 2, filters);
      if (current !== seq) return;
      clear(list);
      if (matches.length === 0) {
        setStatus(
          hasActiveFilters(filters)
            ? "Bu malzemeler ve seçtiğin filtrelerle yapılabilecek tarif bulunamadı. Filtreleri değiştirmeyi dene."
            : "Bu malzemelerle yapılabilecek tarif bulunamadı. Biraz daha malzeme eklemeyi dene.",
        );
        return;
      }
      list.append(...matches.map(renderCard));
    } catch (error) {
      if (current !== seq) return;
      clear(list);
      setStatus(error.message, true);
    }
  }

  async function refresh() {
    const current = ++seq;
    setStatus("");
    clear(more);
    more.hidden = true;
    title.textContent = isAll() ? "Tüm tarifler" : "Önerilen tarifler";
    onlyReady.closest("label").hidden = isAll(); // "hemen yapılabilenler" yalnızca önerilerde anlamlı
    return isAll() ? loadAll(current, true) : loadMatches(current);
  }

  onlyReady.addEventListener("change", refresh);

  // Sayfa doğrudan "Tüm tarifler" görünümüyle açıldıysa buzdolabını beklemeden listeyi yükle;
  // öneri görünümü buzdolabı yüklenince update() ile ilk kez yenilenir.
  if (isAll()) refresh();

  return {
    update(count) {
      pantryCount = count;
      // Buzdolabı "Tüm tarifler" görünümünü etkilemez; gereksiz istek atma
      return isAll() ? Promise.resolve() : refresh();
    },
    setFilters(next) {
      filters = next;
      return refresh();
    },
  };
}
