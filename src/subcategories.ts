// Subcategories aren't tied to a category in the frontmatter, so a recipe in
// two categories would otherwise carry its chips onto both pages. List the
// chips each category page shows; categories not listed get no chips.
export const SUBCATEGORIES: Record<string, string[]> = {
  "Main Dishes": [
    "Beans",
    "Beef",
    "Fish",
    "Pastas and Grains",
    "Pizzas",
    "Pork",
    "Poultry",
    "Slow Cooker Goodness",
    "Sundries",
    "Vegetarian",
  ],
  "Side Dishes": [
    "Corn",
    "Green Vegetables",
    "More Vegetables",
    "Pastas and Grains",
    "Potatoes",
    "Squash and Zucchini",
  ],
  Desserts: [
    "Cakes and Cupcakes",
    "Cookies",
    "Crumbles, Cobblers, Buckles and Bars",
    "Frostings and Sauces",
    "Pies and Tarts",
    "Sweets and Sundries",
  ],
  "Soups and Stews": ["Slow Cooker Goodness", "Soups"],
};
