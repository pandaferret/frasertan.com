#!/usr/bin/env python3
"""Convert scraped Weebly HTML recipe pages to Astro-compatible Markdown files."""

import os
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Tag

OLD_DIR = Path(__file__).parent.parent / "old"
OUT_DIR = Path(__file__).parent.parent / "src" / "content" / "recipes"

# Pages that are NOT recipes
NON_RECIPE_PAGES = {
    "index", "curriculum-vitae", "personal-projects", "recipes", "archives",
    "kitchen-tips", "soups",
    # Category pages
    "desserts", "main-dishes", "starters", "salads", "soups-and-stews",
    "sauces-and-dips", "side-dishes", "breads-and-baked-goods", "breakfast", "drinks",
    # Tag pages
    "weeknight-meals", "make-ahead", "seasonal-treats",
    # Sub-navigation pages
    "pastas-and-grains", "slow-cooker-goodness",
}

# 8 recipes with no multicol — handle as special prose-style recipes
NO_MULTICOL_RECIPES = {
    "artichokes", "corn-on-the-cob", "homemade-ginger-ale",
    "peggys-blueberry-muffins", "roast-veggie-medley",
    "steel-cut-oatmeal", "tuna-ring-salad", "vanilla-ice-cream",
}

CATEGORIES = [
    "Starters", "Salads", "Soups and Stews", "Main Dishes",
    "Sauces and Dips", "Side Dishes", "Breads and Baked Goods",
    "Desserts", "Breakfast", "Drinks",
]

CATEGORY_SLUGS = {c.lower().replace(" ", "-"): c for c in CATEGORIES}

TAG_PAGES = {
    "weeknight-meals": "Weeknight Meals",
    "make-ahead": "Make Ahead",
    "seasonal-treats": "Seasonal Treats",
}


def clean_text(text):
    """Strip zero-width spaces, BOM, and normalize whitespace."""
    if not text:
        return ""
    text = text.replace("\u200b", "").replace("\ufeff", "").replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = text.strip()
    return text


def extract_text_lines(element):
    """Extract text from an element, preserving line breaks from <br> and <li> tags."""
    if element is None:
        return []

    lines = []
    current_line = []

    def flush():
        line = clean_text("".join(current_line))
        if line:
            lines.append(line)
        current_line.clear()

    def walk(node):
        if isinstance(node, NavigableString):
            text = str(node)
            if text.strip():
                current_line.append(text)
        elif isinstance(node, Tag):
            if node.name == "br":
                flush()
            elif node.name == "li":
                flush()
                for child in node.children:
                    walk(child)
                flush()
            elif node.name in ("ul", "ol"):
                flush()
                for child in node.children:
                    walk(child)
                flush()
            elif node.name in ("strong", "b"):
                # Check if this is a sub-heading (standalone bold text)
                text = clean_text(node.get_text())
                if text and text.endswith(":"):
                    flush()
                    lines.append(f"__SUBHEADING__{text.rstrip(':')}")
                    return
                # Check for "Ingredients" or "Directions" headers
                if text in ("Ingredients", "Directions", "Instructions", "Method", "Ingredients:"):
                    flush()
                    return  # Skip these headers, we add our own
                current_line.append(text)
            elif node.name == "u":
                # Underlined text is often a sub-heading
                text = clean_text(node.get_text())
                if text:
                    flush()
                    lines.append(f"__SUBHEADING__{text.rstrip(':')}")
            elif node.name == "hr":
                flush()
            elif node.name in ("div", "p"):
                flush()
                for child in node.children:
                    walk(child)
                flush()
            else:
                for child in node.children:
                    walk(child)

    walk(element)
    flush()
    return lines


def extract_instructions_text(element):
    """Extract instructions, preserving paragraph breaks as step separators."""
    if element is None:
        return []

    steps = []
    current_step = []

    def flush():
        text = clean_text(" ".join(current_step))
        if text:
            steps.append(text)
        current_step.clear()

    def walk(node, depth=0):
        if isinstance(node, NavigableString):
            text = str(node).replace("\n", " ")
            if text.strip():
                current_step.append(text.strip())
        elif isinstance(node, Tag):
            if node.name == "br":
                # Double <br> = paragraph break (new step)
                # Single <br> within a step = continuation
                next_sib = node.next_sibling
                if isinstance(next_sib, Tag) and next_sib.name == "br":
                    flush()
                elif isinstance(next_sib, NavigableString) and not next_sib.strip():
                    # Check the sibling after the whitespace
                    ns = next_sib.next_sibling
                    if isinstance(ns, Tag) and ns.name == "br":
                        flush()
                    else:
                        current_step.append(" ")
                else:
                    current_step.append(" ")
            elif node.name == "li":
                flush()
                for child in node.children:
                    walk(child, depth + 1)
                flush()
            elif node.name in ("ul", "ol"):
                flush()
                for child in node.children:
                    walk(child, depth + 1)
            elif node.name in ("strong", "b"):
                text = clean_text(node.get_text())
                if text in ("Ingredients", "Directions", "Instructions", "Method"):
                    return
                if text and (text.endswith(":") or text.endswith(".")):
                    flush()
                    steps.append(f"__SUBHEADING__{text.rstrip(':').rstrip('.')}")
                    return
                current_step.append(text)
            elif node.name == "u":
                text = clean_text(node.get_text())
                if text:
                    flush()
                    steps.append(f"__SUBHEADING__{text.rstrip(':')}")
            elif node.name in ("div", "p"):
                flush()
                for child in node.children:
                    walk(child, depth + 1)
                flush()
            else:
                for child in node.children:
                    walk(child, depth + 1)

    walk(element)
    flush()
    return steps


def format_ingredient_lines(lines):
    """Format ingredient lines for markdown, handling sub-headings."""
    result = []
    for line in lines:
        if line.startswith("__SUBHEADING__"):
            heading = line.replace("__SUBHEADING__", "")
            result.append(f"\n### {heading}\n")
        else:
            result.append(line)
    return "\n".join(result)


def format_instruction_steps(steps):
    """Format instruction steps as paragraphs, handling sub-headings."""
    result = []
    for step in steps:
        if step.startswith("__SUBHEADING__"):
            heading = step.replace("__SUBHEADING__", "")
            result.append(f"### {heading}")
        else:
            result.append(step)
    return "\n\n".join(result)


def parse_source_block(elements_after_hr):
    """Extract source info from content after the second HR."""
    source_name = None
    source_url = None
    notes = []

    text_parts = []
    for el in elements_after_hr:
        if isinstance(el, Tag):
            text = clean_text(el.get_text())
            # Look for links
            links = el.find_all("a")
            for link in links:
                href = link.get("href", "")
                link_text = clean_text(link.get_text())
                if href and href.startswith("http"):
                    if link_text.lower() in ("source", "here", "recipe", "original", "original recipe"):
                        source_url = href
                        if not source_name:
                            # Try to find name from surrounding text
                            parent_text = clean_text(el.get_text())
                            # Patterns: "Adapted from [link]", "From [link]", "Source: [text] [link]"
                            for pattern in [r"(?:from|adapted from|courtesy of|via)\s+(.+?)(?:\s*$)", r"source:\s*(.+?)(?:\s*$)"]:
                                m = re.search(pattern, parent_text, re.IGNORECASE)
                                if m:
                                    name_candidate = m.group(1).strip()
                                    # Remove the link text from the name
                                    name_candidate = name_candidate.replace(link_text, "").strip().rstrip(",").strip()
                                    if name_candidate:
                                        source_name = name_candidate
                    else:
                        source_url = href
                        source_name = link_text

            # Check for "Source: ..." text without links
            if not source_url and text:
                m = re.match(r"(?:source|from|adapted from|courtesy of):\s*(.+)", text, re.IGNORECASE)
                if m:
                    source_name = m.group(1).strip()
                elif re.match(r"(?:from|adapted from|courtesy of|inspired by)\s+.+", text, re.IGNORECASE):
                    m = re.match(r"(?:from|adapted from|courtesy of|inspired by)\s+(.+)", text, re.IGNORECASE)
                    if m:
                        source_name = m.group(1).strip()

            # Check for notes
            note_items = el.find_all("li")
            if note_items:
                for item in note_items:
                    note_text = clean_text(item.get_text())
                    if note_text:
                        notes.append(note_text)
            elif text and not source_url and not source_name:
                # Could be a note
                if text.lower().startswith("note"):
                    text = re.sub(r"^notes?:?\s*", "", text, flags=re.IGNORECASE)
                    if text:
                        notes.append(text)

    return source_name, source_url, notes


def parse_recipe_html(filepath):
    """Parse a single recipe HTML file and return structured data."""
    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    slug = filepath.stem

    # Title
    title_el = soup.find("h2", class_="wsite-content-title")
    if title_el:
        title = clean_text(title_el.get_text())
    else:
        og_title = soup.find("meta", property="og:title")
        title = clean_text(og_title["content"]) if og_title else slug.replace("-", " ").title()

    # Find the main content area
    content = soup.find(id="wsite-content")
    if not content:
        print(f"  WARNING: No wsite-content found in {slug}", file=sys.stderr)
        return None

    section_elements = content.find("div", class_="wsite-section-elements")
    if not section_elements:
        print(f"  WARNING: No section-elements found in {slug}", file=sys.stderr)
        return None

    # Split content by HR dividers
    # Find all HR elements
    hrs = section_elements.find_all("hr", class_="styled-hr")

    # Get all direct children and their parent divs
    all_children = list(section_elements.children)

    # Find multicol elements
    multicols = section_elements.find_all("div", class_="wsite-multicol", recursive=True)

    description = ""
    recipe_yield = ""
    ingredients_lines = []
    instructions_steps = []
    source_name = None
    source_url = None
    notes = []

    if slug in NO_MULTICOL_RECIPES:
        # Special handling: no multicol, prose-style
        # Extract description from og:description
        og_desc = soup.find("meta", property="og:description")
        if og_desc:
            desc_text = clean_text(og_desc.get("content", ""))
            if desc_text:
                description = desc_text

        # Get all paragraphs
        paragraphs = section_elements.find_all("div", class_="paragraph")
        all_text = []
        for p in paragraphs:
            text = clean_text(p.get_text())
            if text:
                all_text.append(text)

        # For these recipes, put everything as instructions
        if all_text:
            instructions_steps = all_text

        return {
            "slug": slug,
            "title": title,
            "description": description,
            "yield": recipe_yield,
            "ingredients": [],
            "instructions": instructions_steps,
            "source_name": source_name,
            "source_url": source_url,
            "notes": notes,
        }

    if len(multicols) == 0:
        print(f"  WARNING: No multicol in {slug} (not in no-multicol list)", file=sys.stderr)
        return None

    # Determine if this is a 1-multicol or 2-multicol recipe
    # 2-multicol: first multicol is description + yield, second is ingredients/instructions
    recipe_multicol = None
    desc_multicol = None

    if len(multicols) >= 2:
        # Check if the first multicol is before the first HR (description multicol)
        first_hr = hrs[0] if hrs else None
        if first_hr:
            # Is the first multicol before the HR?
            mc0_pos = str(section_elements).find(str(multicols[0]))
            hr_pos = str(section_elements).find(str(first_hr))
            if mc0_pos < hr_pos:
                desc_multicol = multicols[0]
                recipe_multicol = multicols[1]
            else:
                recipe_multicol = multicols[0]
        else:
            recipe_multicol = multicols[0]
    else:
        recipe_multicol = multicols[0]

    # Extract description
    if desc_multicol:
        cols = desc_multicol.find_all("td", class_="wsite-multicol-col")
        if cols:
            desc_text = clean_text(cols[0].get_text())
            if desc_text:
                description = desc_text
            if len(cols) > 1:
                yield_text = clean_text(cols[1].get_text())
                if yield_text:
                    recipe_yield = yield_text
    else:
        # Look for description paragraph before HR or before multicol
        # Check og:description first, then look in the HTML
        og_desc = soup.find("meta", property="og:description")
        og_desc_text = clean_text(og_desc.get("content", "")) if og_desc else ""

        # Find paragraphs and blockquotes before the recipe multicol
        desc_parts = []
        for child in section_elements.descendants:
            if child is recipe_multicol or (isinstance(child, Tag) and child.find(class_="wsite-multicol")):
                break
            if isinstance(child, Tag) and child.name in ("div",) and "paragraph" in (child.get("class") or []):
                text = clean_text(child.get_text())
                if text and text != title:
                    desc_parts.append(text)
            elif isinstance(child, Tag) and child.name == "blockquote":
                text = clean_text(child.get_text())
                if text:
                    desc_parts.append(text)

        if desc_parts:
            description = " ".join(desc_parts)
        elif og_desc_text and og_desc_text != title:
            # Only use og:description if it doesn't look like ingredient text
            if not re.match(r"^\d", og_desc_text) and len(og_desc_text) < 300:
                description = og_desc_text

    # Extract ingredients and instructions from recipe multicol
    cols = recipe_multicol.find_all("td", class_="wsite-multicol-col")
    if len(cols) >= 2:
        ingredients_lines = extract_text_lines(cols[0])
        instructions_steps = extract_instructions_text(cols[1])
    elif len(cols) == 1:
        # Single column — treat as combined
        instructions_steps = extract_instructions_text(cols[0])

    # Extract source and notes from content after the last HR
    if len(hrs) >= 2:
        last_hr = hrs[-1]
        # Get parent div of last HR
        hr_parent = last_hr.parent
        if hr_parent:
            # Get siblings after the hr_parent
            after_hr = []
            found_hr_parent = False
            for child in section_elements.find_all(True, recursive=False):
                if found_hr_parent:
                    after_hr.append(child)
                if child is hr_parent or hr_parent in child.descendants:
                    found_hr_parent = True

            if after_hr:
                source_name, source_url, notes = parse_source_block(after_hr)

    # Also check for source links in the description
    if not source_url and description:
        # Check the original HTML for links in description area
        if desc_multicol:
            cols = desc_multicol.find_all("td", class_="wsite-multicol-col")
            if cols:
                for link in cols[0].find_all("a"):
                    href = link.get("href", "")
                    if href.startswith("http"):
                        source_url = href
                        link_text = clean_text(link.get_text())
                        if link_text:
                            source_name = link_text
                        break

    return {
        "slug": slug,
        "title": title,
        "description": description,
        "yield": recipe_yield,
        "ingredients": ingredients_lines,
        "instructions": instructions_steps,
        "source_name": source_name,
        "source_url": source_url,
        "notes": notes,
    }


def parse_category_page(filepath):
    """Parse a category/tag page and return slug -> {subcategories, dietary} mapping."""
    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    content = soup.find(id="wsite-content")
    if not content:
        return {}

    result = {}
    current_subcategory = None

    # Find all list items with recipe links
    for li in content.find_all("li"):
        link = li.find("a")
        if not link:
            continue

        href = link.get("href", "")
        if not href or not href.endswith(".html"):
            continue

        # Extract slug from href
        recipe_slug = href.strip("/").replace(".html", "")

        # Extract dietary annotations from text after the link
        li_text = clean_text(li.get_text())
        link_text = clean_text(link.get_text())
        after_link = li_text[len(link_text):].strip() if len(li_text) > len(link_text) else ""

        dietary = []
        diet_match = re.search(r"\(([^)]+)\)", after_link)
        if diet_match:
            codes = diet_match.group(1)
            for code in re.split(r"[,\s]+", codes):
                code = code.strip()
                if code and code.upper() in ("GF", "DF", "EF", "V", "VEG", "V*", "VEG*", "GF*", "DF*", "EF*"):
                    dietary.append(code.upper())

        result[recipe_slug] = {
            "dietary": dietary,
        }

    # Now find subcategories — look for bold or strong text before lists
    # Walk through the content looking for strong text followed by lists
    for strong in content.find_all(["strong", "b"]):
        text = clean_text(strong.get_text())
        if not text:
            continue
        # This is a subcategory heading. Find the next ul after it.
        next_el = strong.find_next("ul")
        if next_el:
            for li in next_el.find_all("li", recursive=False):
                link = li.find("a")
                if link:
                    href = link.get("href", "")
                    if href and href.endswith(".html"):
                        recipe_slug = href.strip("/").replace(".html", "")
                        if recipe_slug in result:
                            result[recipe_slug]["subcategory"] = text

    return result


def build_metadata():
    """Build slug -> metadata mapping from all category and tag pages."""
    metadata = {}  # slug -> {categories: [], subcategories: [], tags: [], dietary: []}

    # Parse category pages
    for cat_slug, cat_name in CATEGORY_SLUGS.items():
        filepath = OLD_DIR / f"{cat_slug}.html"
        if not filepath.exists():
            print(f"  Category page not found: {cat_slug}", file=sys.stderr)
            continue

        recipes_in_cat = parse_category_page(filepath)
        for recipe_slug, info in recipes_in_cat.items():
            if recipe_slug not in metadata:
                metadata[recipe_slug] = {
                    "categories": [],
                    "subcategories": [],
                    "tags": [],
                    "dietary": [],
                }
            if cat_name not in metadata[recipe_slug]["categories"]:
                metadata[recipe_slug]["categories"].append(cat_name)
            if "subcategory" in info and info["subcategory"]:
                sub = info["subcategory"]
                if sub not in metadata[recipe_slug]["subcategories"]:
                    metadata[recipe_slug]["subcategories"].append(sub)
            for d in info.get("dietary", []):
                if d not in metadata[recipe_slug]["dietary"]:
                    metadata[recipe_slug]["dietary"].append(d)

    # Parse tag pages
    for tag_slug, tag_name in TAG_PAGES.items():
        filepath = OLD_DIR / f"{tag_slug}.html"
        if not filepath.exists():
            continue

        recipes_in_tag = parse_category_page(filepath)
        for recipe_slug, info in recipes_in_tag.items():
            if recipe_slug not in metadata:
                metadata[recipe_slug] = {
                    "categories": [],
                    "subcategories": [],
                    "tags": [],
                    "dietary": [],
                }
            if tag_name not in metadata[recipe_slug]["tags"]:
                metadata[recipe_slug]["tags"].append(tag_name)
            for d in info.get("dietary", []):
                if d not in metadata[recipe_slug]["dietary"]:
                    metadata[recipe_slug]["dietary"].append(d)

    return metadata


def yaml_escape(s):
    """Escape a string for YAML frontmatter."""
    if not s:
        return '""'
    # Quote strings that contain special YAML characters
    if any(c in s for c in ":{}[]&*?|>'\",#!%@`\\") or s.startswith("-") or s.startswith(" "):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return f'"{s}"'


def generate_markdown(recipe_data, metadata):
    """Generate a markdown file from parsed recipe data."""
    slug = recipe_data["slug"]
    meta = metadata.get(slug, {"categories": [], "subcategories": [], "tags": [], "dietary": []})

    # Ensure at least one category
    categories = meta["categories"]
    if not categories:
        categories = ["Main Dishes"]  # Default

    lines = ["---"]
    lines.append(f"title: {yaml_escape(recipe_data['title'])}")

    if recipe_data["description"]:
        lines.append(f"description: {yaml_escape(recipe_data['description'])}")

    if recipe_data["yield"]:
        lines.append(f"yield: {yaml_escape(recipe_data['yield'])}")

    lines.append("categories:")
    for cat in categories:
        lines.append(f"  - {cat}")

    if meta["subcategories"]:
        lines.append("subcategories:")
        for sub in meta["subcategories"]:
            lines.append(f"  - {sub}")

    if meta["tags"]:
        lines.append("tags:")
        for tag in meta["tags"]:
            lines.append(f"  - {tag}")

    dietary = meta["dietary"]
    if dietary:
        lines.append("dietary:")
        for d in dietary:
            lines.append(f"  - {d}")

    if recipe_data["source_name"] or recipe_data["source_url"]:
        lines.append("source:")
        if recipe_data["source_name"]:
            lines.append(f"  name: {yaml_escape(recipe_data['source_name'])}")
        if recipe_data["source_url"]:
            lines.append(f"  url: {yaml_escape(recipe_data['source_url'])}")

    lines.append("---")
    lines.append("")

    # Body
    if recipe_data["ingredients"]:
        lines.append("## Ingredients")
        lines.append("")
        lines.append(format_ingredient_lines(recipe_data["ingredients"]))
        lines.append("")

    if recipe_data["instructions"]:
        lines.append("## Instructions")
        lines.append("")
        lines.append(format_instruction_steps(recipe_data["instructions"]))
        lines.append("")

    if recipe_data["notes"]:
        lines.append("## Notes")
        lines.append("")
        for note in recipe_data["notes"]:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)


def main():
    print("Building metadata from category and tag pages...")
    metadata = build_metadata()
    print(f"  Found metadata for {len(metadata)} recipe slugs")

    # Find all recipe HTML files
    html_files = sorted(OLD_DIR.glob("*.html"))
    recipe_files = [
        f for f in html_files
        if f.stem not in NON_RECIPE_PAGES
    ]
    print(f"  Found {len(recipe_files)} potential recipe files")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Remove existing test recipes so we regenerate cleanly
    for existing in OUT_DIR.glob("*.md"):
        existing.unlink()

    success = 0
    errors = 0

    for filepath in recipe_files:
        slug = filepath.stem
        try:
            recipe_data = parse_recipe_html(filepath)
            if recipe_data is None:
                errors += 1
                continue

            md = generate_markdown(recipe_data, metadata)
            out_path = OUT_DIR / f"{slug}.md"
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(md)
            success += 1
        except Exception as e:
            print(f"  ERROR processing {slug}: {e}", file=sys.stderr)
            errors += 1

    print(f"\nDone: {success} recipes converted, {errors} errors")

    # Report recipes not found in any category
    uncategorized = []
    for filepath in recipe_files:
        slug = filepath.stem
        if slug not in metadata:
            uncategorized.append(slug)
    if uncategorized:
        print(f"\n{len(uncategorized)} recipes not found in any category page:")
        for slug in sorted(uncategorized)[:20]:
            print(f"  - {slug}")
        if len(uncategorized) > 20:
            print(f"  ... and {len(uncategorized) - 20} more")


if __name__ == "__main__":
    main()
