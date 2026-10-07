import type { CollectionEntry } from "astro:content";

// Buttons on the Special Diets tag page, in order. Drawn from each recipe's
// dietary badges (GF, DF, EF, V; a trailing * means "with a swap"), which
// mirror the Diet field in Fraser's Notion recipe database, plus the
// Vegetarian and Vegan tags.
export const DIETS = [
  "Vegetarian",
  "Vegan",
  "Gluten-Free",
  "Can Be Gluten-Free",
  "Dairy-Free",
  "Egg-Free",
];

const byCode: Record<string, string> = {
  V: "Vegetarian",
  GF: "Gluten-Free",
  "GF*": "Can Be Gluten-Free",
  DF: "Dairy-Free",
  EF: "Egg-Free",
};

export function dietsOf(recipe: CollectionEntry<"recipes">): string[] {
  const diets = new Set(
    (recipe.data.dietary ?? []).map((code) => byCode[code]).filter(Boolean),
  );
  for (const tag of ["Vegetarian", "Vegan"])
    if (recipe.data.tags?.includes(tag)) diets.add(tag);
  // Anything vegan is vegetarian too.
  if (diets.has("Vegan")) diets.add("Vegetarian");
  return DIETS.filter((d) => diets.has(d));
}
