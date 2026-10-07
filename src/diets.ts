import type { CollectionEntry } from "astro:content";

// Buttons on the Special Diets tag page, in order. Drawn from each recipe's
// dietary badges (GF, DF, EF, V for vegan, VEG for vegetarian; a trailing *
// means "with a swap or two"), which mirror the Diet field in Fraser's Notion
// recipe database, plus the Vegetarian tag.
export const DIETS = [
  "Vegetarian",
  "Vegan",
  "Gluten-Free",
  "Can Be Gluten-Free",
  "Dairy-Free",
  "Egg-Free",
];

const byCode: Record<string, string> = {
  V: "Vegan",
  "V*": "Vegan",
  VEG: "Vegetarian",
  GF: "Gluten-Free",
  "GF*": "Can Be Gluten-Free",
  DF: "Dairy-Free",
  EF: "Egg-Free",
};

export function dietsOf(recipe: CollectionEntry<"recipes">): string[] {
  const diets = new Set(
    (recipe.data.dietary ?? []).map((code) => byCode[code]).filter(Boolean),
  );
  if (recipe.data.tags?.includes("Vegetarian")) diets.add("Vegetarian");
  // Anything vegan, even with a swap, is vegetarian as it stands.
  if (diets.has("Vegan")) diets.add("Vegetarian");
  return DIETS.filter((d) => diets.has(d));
}
