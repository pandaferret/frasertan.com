import type { CollectionEntry } from "astro:content";

// schema.org Recipe data for a recipe page, which Google reads to show the
// recipe with its photo, time and servings in search results. Ingredients
// and steps are pulled from the Markdown body.

const DIETS: Record<string, string> = {
  GF: "https://schema.org/GlutenFreeDiet",
  V: "https://schema.org/VeganDiet",
  VEG: "https://schema.org/VegetarianDiet",
};

// "1 hr 15 min" -> "PT1H15M". Anything else (e.g. "4 hr to overnight")
// isn't a single duration, so it's left out.
function isoDuration(text?: string): string | undefined {
  const match = text
    ?.replace(/\s*\(.*\)$/, "")
    .match(/^(?:(\d+) hr)?\s*(?:(\d+) min)?$/);
  if (!match || (!match[1] && !match[2])) return undefined;
  return `PT${match[1] ? `${match[1]}H` : ""}${match[2] ? `${match[2]}M` : ""}`;
}

function minutes(iso?: string): number {
  const m = iso?.match(/^PT(?:(\d+)H)?(?:(\d+)M)?$/);
  return m ? Number(m[1] ?? 0) * 60 + Number(m[2] ?? 0) : 0;
}

const fromMinutes = (total: number) =>
  `PT${total >= 60 ? `${Math.floor(total / 60)}H` : ""}${total % 60 ? `${total % 60}M` : ""}`;

// Markdown to plain text: drop links, emphasis and escapes.
const plain = (s: string) =>
  s
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/[*_`]+/g, "")
    .replace(/\\(.)/g, "$1")
    .trim();

// The list items under one "## Heading" of the body.
function listUnder(body: string, headings: string[]): string[] {
  const items: string[] = [];
  let inside = false;
  for (const line of body.split("\n")) {
    const heading = /^##\s+(.*)$/.exec(line);
    if (heading) {
      inside = headings.includes(heading[1].trim().toLowerCase());
      continue;
    }
    const item = inside && /^(?:[-*]|\d+\.)\s+(.*)$/.exec(line);
    if (item && !/^#/.test(item[1])) items.push(plain(item[1]));
  }
  return items.filter(Boolean);
}

export function recipeSchema(
  recipe: CollectionEntry<"recipes">,
  site: URL,
): Record<string, unknown> {
  const { data } = recipe;
  const prepTime = isoDuration(data.prep);
  const cookTime = isoDuration(data.cook);
  // Only give a total when the times cover everything; a marinade or rise
  // ("rest") would make prep plus cook misleading.
  const total = !data.rest && minutes(prepTime) + minutes(cookTime);
  const diets = (data.dietary ?? []).map((c) => DIETS[c]).filter(Boolean);

  const ingredients = listUnder(recipe.body ?? "", ["ingredients"]);
  const steps = listUnder(recipe.body ?? "", ["directions", "instructions"]);

  return {
    "@context": "https://schema.org",
    "@type": "Recipe",
    name: data.title,
    url: new URL(`/recipes/${recipe.id}/`, site).href,
    ...(data.description && { description: plain(data.description) }),
    ...(data.cover && { image: new URL(data.cover, site).href }),
    ...(data.source?.url
      ? { isBasedOn: data.source.url }
      : !data.source?.name && {
          author: { "@type": "Person", name: "Fraser Elisabeth Tan" },
        }),
    ...(data.added && {
      datePublished: data.added.toISOString().slice(0, 10),
    }),
    ...(data.yield && { recipeYield: data.yield }),
    ...(prepTime && { prepTime }),
    ...(cookTime && { cookTime }),
    ...(total && { totalTime: fromMinutes(total) }),
    recipeCategory: data.categories[0],
    ...(data.tags?.length && { keywords: data.tags.join(", ") }),
    ...(diets.length && { suitableForDiet: diets }),
    ...(ingredients.length && { recipeIngredient: ingredients }),
    ...(steps.length && {
      recipeInstructions: steps.map((text) => ({ "@type": "HowToStep", text })),
    }),
  };
}
