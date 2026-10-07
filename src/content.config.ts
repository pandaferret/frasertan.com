import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const recipes = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/recipes" }),
  schema: z.object({
    title: z.string().min(1),
    description: z.string().optional(),
    yield: z.string().optional(),
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
