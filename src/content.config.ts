import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const recipes = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/recipes" }),
  schema: z.object({
    title: z.string().min(1),
    description: z.string().optional(),
    yield: z.string().optional(),
    // Rough times, e.g. "20 min" or "1 hr 15 min". "rest" is hands-off
    // waiting with its own label, e.g. "Chill 2 hr" or "Marinate 4 hr".
    prep: z.string().optional(),
    cook: z.string().optional(),
    rest: z.string().optional(),
    // When the recipe joined the collection (its Notion created date), for
    // the Recently added row on the Recipes page.
    added: z.coerce.date().optional(),
    categories: z.array(z.string()).min(1),
    subcategories: z.array(z.string()).optional(),
    tags: z.array(z.string()).optional(),
    dietary: z.array(z.string()).optional(),
    cover: z.string().optional(),
    quote: z
      .object({
        text: z.string().min(1),
        author: z.string().min(1),
      })
      .optional(),
    source: z
      .object({
        name: z.string().optional(),
        url: z.string().url().optional(),
      })
      .optional(),
  }),
});

export const collections = { recipes };
