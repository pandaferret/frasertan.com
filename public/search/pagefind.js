// Pagefind with whole-word matching. Pagefind matches every search term as a
// prefix, so "pie" also finds recipes that only mention "pieces" and "corn"
// finds ones that only use "cornstarch". This wraps the generated bundle and
// drops those results, keeping a word only when it is the search term itself
// or the term plus a simple ending: "pie" matches "pie", "pies" and "pie's";
// "bake" matches "baked" and "baking". Both the recipe search page (through
// PagefindUI's bundlePath) and the category and tag pages load this module.
export * from "../pagefind/pagefind.js";
import * as pagefind from "../pagefind/pagefind.js";

// Endings a word may add to a search term (or to its base, below).
const ENDINGS = new Set(["", "s", "es", "e", "d", "ed", "ing"]);

const fold = (text) =>
  text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/['’]s\b/g, "")
    .replace(/['’]/g, "");

// "baking" -> "bak", "tomatoes" -> "tomato", "pies" -> "pie".
const baseOf = (term) => {
  for (const ending of ["ing", "ed", "es", "s"])
    if (term.endsWith(ending) && term.length - ending.length >= 3)
      return term.slice(0, -ending.length);
  return term;
};

// Whether a word Pagefind matched for this term is a whole-word match. Words
// that don't begin with the base came from Pagefind's stemming ("berries"
// for "berry"), so they count as long as the start of the word agrees.
const matchesWord = (base, word) =>
  word.startsWith(base)
    ? ENDINGS.has(word.slice(base.length))
    : word.slice(0, 3) === base.slice(0, 3);

// Terms shorter than this stay prefix matches, so the first letters typed
// still show something.
const MIN_LENGTH = 3;

export const searchTerms = (query) =>
  fold(query)
    .split(/[^a-z0-9]+/)
    .filter((t) => t.length >= MIN_LENGTH)
    .map(baseOf);

// Whether a result's matched words (Pagefind's fragment content and the
// locations of the words it matched) contain every term as a whole word.
export const matchesWholeWords = (terms, content, locations) => {
  if (locations.length === 0) return true;
  const words = content.split(/\s+/);
  const matched = locations.flatMap((n) => {
    const word = fold(words[n] ?? "");
    // Hyphenated words are indexed whole and in parts.
    return [word.replace(/[^a-z0-9]/g, ""), ...word.split(/[^a-z0-9]+/)];
  });
  return terms.every((base) => matched.some((w) => matchesWord(base, w)));
};

const isWholeWordMatch = async (terms, result) => {
  const { content, locations } = await result.data();
  return matchesWholeWords(terms, content, locations);
};

// Whether some recipe, in any category, has these terms as whole words. If
// none does, the query is most likely a word still being typed ("choc").
const isKnownWord = async (query, terms, options) => {
  if (!options?.filters || Object.keys(options.filters).length === 0)
    return false; // The caller already searched every recipe.
  const { results } = await pagefind.search(query);
  for (let n = 0; n < results.length; n += 20) {
    const batch = results.slice(n, n + 20);
    const found = await Promise.all(
      batch.map((r) => isWholeWordMatch(terms, r)),
    );
    if (found.includes(true)) return true;
  }
  return false;
};

export const search = async (query, options) => {
  const response = await pagefind.search(query, options);
  if (!response?.results?.length) return response;
  const terms = searchTerms(query ?? "");
  if (terms.length === 0) return response;

  const keep = await Promise.all(
    response.results.map((r) => isWholeWordMatch(terms, r)),
  );
  const results = response.results.filter((_, n) => keep[n]);
  // A word still being typed matches nothing whole, so show Pagefind's
  // prefix matches for it instead.
  if (results.length === 0 && !(await isKnownWord(query, terms, options)))
    return response;
  return { ...response, results };
};
