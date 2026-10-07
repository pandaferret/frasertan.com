import { defineConfig } from "astro/config";
import pagefind from "astro-pagefind";
import { redirects } from "./src/redirects.js";
import rehypeRecipeSections from "./src/plugins/rehype-recipe-sections.mjs";

export default defineConfig({
  site: "https://frasertan.com",
  output: "static",
  build: {
    format: "directory",
  },
  redirects,
  markdown: {
    rehypePlugins: [rehypeRecipeSections],
  },
  integrations: [pagefind()],
});
