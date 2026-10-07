// Wraps each "## Heading" block of a recipe in a <section> so the recipe
// layout can place Ingredients beside Directions, with Notes below.
const SECTION_CLASSES = {
  ingredients: "ingredients",
  equipment: "equipment",
  directions: "directions",
  instructions: "directions",
  notes: "notes",
};

function textOf(node) {
  if (node.type === "text") return node.value;
  return (node.children || []).map(textOf).join("");
}

// A short paragraph ending in a colon ("Filling:", "For the crust:") is a
// sub-header inside Directions, as opposed to a prose aside.
function isSubheading(node) {
  if (node.type !== "element" || node.tagName !== "p") return false;
  const text = textOf(node).trim();
  return text.endsWith(":") && text.length <= 60;
}

export default function rehypeRecipeSections() {
  return (tree, file) => {
    if (!file.path?.includes("/content/recipes/")) return;

    const children = [];
    let section = null;
    for (const node of tree.children) {
      if (node.type === "element" && node.tagName === "h2") {
        const name = textOf(node).trim().toLowerCase();
        section = {
          type: "element",
          tagName: "section",
          properties: { className: [SECTION_CLASSES[name] || "other"] },
          children: [node],
        };
        children.push(section);
      } else if (section) {
        if (
          section.properties.className[0] === "directions" &&
          isSubheading(node)
        ) {
          node.properties = { ...node.properties, className: ["subheading"] };
        }
        section.children.push(node);
      } else {
        children.push(node);
      }
    }
    tree.children = children;
  };
}
