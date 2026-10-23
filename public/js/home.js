import { initFilterBar } from "/js/filter-bar.js";
import { initPantry } from "/js/pantry.js";
import { initRecipes } from "/js/recipes.js";
import { parseFilterParams } from "/js/tags.js";

// Filtreler sayfa adresinden gelebilir (örn. tarif sayfasındaki etiket bağlantısı: /?tag=kahvaltı)
const filters = parseFilterParams(location.search);
const recipes = initRecipes({ filters });
initFilterBar({ initial: filters, onChange: (next) => recipes.setFilters(next) });
const pantry = initPantry({ onChange: (items) => recipes.update(items.length) });
pantry.load();
