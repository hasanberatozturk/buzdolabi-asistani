import { initPantry } from "/js/pantry.js";
import { initRecipes } from "/js/recipes.js";

const recipes = initRecipes();
const pantry = initPantry({ onChange: (items) => recipes.update(items.length) });
pantry.load();
