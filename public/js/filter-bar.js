import * as api from "./api.js";
import { clear, el } from "./dom.js";
import { QUICK_MINUTES, filtersToSearch, hasActiveFilters, hasTag, toggleTag } from "./tags.js";

// Ana sayfadaki filtre çubuğu: "30 dk altı" + her etiket için bir düğme (seçilenlerin hepsine sahip tarifler).
// Seçim sayfa adresine yazılır (?tag=kahvaltı&max_minutes=30), böylece bağlantı paylaşılabilir.
export function initFilterBar({ initial, onChange }) {
  const bar = document.querySelector("#filter-bar");
  const viewSwitch = document.querySelector("#view-switch");
  let filters = { tags: [...initial.tags], maxMinutes: initial.maxMinutes, view: initial.view };
  let available = []; // [{ name, count }]

  function chip(label, pressed, onClick) {
    return el("button", { type: "button", class: "filter-chip", "aria-pressed": String(pressed), onclick: onClick }, label);
  }

  function renderViewSwitch() {
    clear(viewSwitch);
    viewSwitch.append(
      chip("Buzdolabıma göre", filters.view !== "all", () => apply({ ...filters, view: "match" })),
      chip("Tüm tarifler", filters.view === "all", () => apply({ ...filters, view: "all" })),
    );
  }

  function render() {
    renderViewSwitch();
    clear(bar);
    const minutes = filters.maxMinutes;
    bar.append(
      chip(`⏱ ${minutes ?? QUICK_MINUTES} dk altı`, minutes != null, () =>
        apply({ ...filters, maxMinutes: minutes != null ? null : QUICK_MINUTES }),
      ),
    );
    // Adresten gelen ama listede olmayan etiketler de görünür (kullanıcı kaldırabilsin)
    const extra = filters.tags.filter((name) => !available.some((tag) => hasTag([tag.name], name)));
    for (const tag of [...available, ...extra.map((name) => ({ name, count: null }))]) {
      const label = tag.count != null ? `${tag.name} (${tag.count})` : tag.name;
      bar.append(chip(label, hasTag(filters.tags, tag.name), () => apply({ ...filters, tags: toggleTag(filters.tags, tag.name) })));
    }
    if (hasActiveFilters(filters)) {
      bar.append(el("button", { type: "button", class: "link-button", onclick: () => apply({ tags: [], maxMinutes: null, view: filters.view }) }, "Filtreleri temizle"));
    }
  }

  function apply(next) {
    filters = next;
    history.replaceState(null, "", `${location.pathname}${filtersToSearch(filters)}`);
    render();
    onChange(filters);
  }

  render();
  api
    .getTags()
    .then((tags) => {
      available = tags;
      render();
    })
    .catch(() => {
      // Etiketler alınamazsa yalnızca süre filtresi görünür; öneriler yine çalışır
    });
}
