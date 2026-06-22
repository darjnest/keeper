"""Polite, table-oriented importer for the official Graveyard Keeper Fandom wiki."""
from __future__ import annotations

import argparse
import re
import time
from datetime import datetime, timezone
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup, Tag

from app.models import Catalog, Material, Recipe
from app.storage import save_catalog

WIKI = "https://graveyardkeeper.fandom.com/wiki/"
API = "https://graveyardkeeper.fandom.com/api.php"
# Add station pages here as coverage grows. Each page is independently parsed.
DEFAULT_PAGES = ["Cooking", "Alchemy", "Furnace", "Alchemy_mill"]
USER_AGENT = "GraveyardKeeperCatalog/0.1 (personal educational catalog; contact: local)"


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value


def extract_quantity_and_name(value: str) -> tuple[float, str]:
    value = clean(value)
    match = re.match(r"(?:(\d+(?:\.\d+)?)\s*[×x])?\s*(.+)", value, re.I)
    if not match:
        return 1, value
    return float(match.group(1) or 1), clean(match.group(2))


def cell_items(cell: Tag) -> list[Material]:
    """Read wiki cells such as '5× Dough 1× Honey' without relying on CSS classes."""
    text = clean(cell.get_text(" ", strip=True))
    matches = list(re.finditer(r"(\d+(?:\.\d+)?)\s*[×x]\s*(.*?)(?=\s+\d+(?:\.\d+)?\s*[×x]|$)", text, re.I))
    if matches:
        return [Material(name=clean(m.group(2)), quantity=float(m.group(1))) for m in matches if clean(m.group(2))]

    links = [clean(link.get_text(" ", strip=True)) for link in cell.select("a")]
    # Links are better than a cell's surrounding labels/images, and duplicates are noise.
    unique = list(dict.fromkeys(link for link in links if link and not link.startswith("Image:")))
    return [Material(name=name, quantity=1) for name in unique]


def table_recipes(table: Tag, source_url: str, station: str | None) -> list[Recipe]:
    rows = table.select("tr")
    if not rows:
        return []
    # Fandom commonly inserts a tab/image row above the actual table headings.
    header_row_index = next(
        (i for i, row in enumerate(rows) if "item produced" in clean(row.get_text(" ", strip=True)).lower()),
        None,
    )
    if header_row_index is None:
        return []
    headers = [clean(c.get_text(" ", strip=True)).lower() for c in rows[header_row_index].select("th, td")]
    output_index = next((i for i, h in enumerate(headers) if "item produced" in h or h == "output"), None)
    material_index = next((i for i, h in enumerate(headers) if "material" in h or "ingredient" in h), None)
    if output_index is None or material_index is None:
        return []

    recipes: list[Recipe] = []
    for row in rows[header_row_index + 1:]:
        cells = row.select(":scope > td, :scope > th")
        if len(cells) <= max(output_index, material_index):
            continue
        output_qty, output = extract_quantity_and_name(cells[output_index].get_text(" ", strip=True))
        ingredients = cell_items(cells[material_index])
        if not output or not ingredients:
            continue
        extras = {headers[i]: clean(cell.get_text(" ", strip=True)) for i, cell in enumerate(cells) if i < len(headers)}
        recipe = Recipe(
            id=slug(f"{station or 'crafting'}-{output}"), output=output,
            output_quantity=output_qty, ingredients=ingredients, station=station,
            fuel=try_number(extras.get("fuel")), time=extras.get("time"),
            energy=extras.get("energy"), notes=extras.get("notes"), source_url=source_url,
        )
        recipes.append(recipe)
    return recipes


def try_number(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"\d+(?:\.\d+)?", value)
    return float(match.group()) if match else None


def parse_page(html: str, source_url: str, station: str | None) -> list[Recipe]:
    soup = BeautifulSoup(html, "html.parser")
    recipes: list[Recipe] = []
    for table in soup.select("table"):
        recipes.extend(table_recipes(table, source_url, station))
    return recipes


def import_catalog(pages: list[str], delay: float = 1.0) -> Catalog:
    recipes: dict[str, Recipe] = {}
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30, follow_redirects=True) as client:
        for index, page in enumerate(pages):
            if index:
                time.sleep(delay)
            title = page.replace(" ", "_")
            url = WIKI + quote(title, safe="_()")
            # Fandom blocks direct HTML requests from scripts (403), but its
            # read-only MediaWiki API returns the same rendered wiki tables.
            response = client.get(API, params={
                "action": "parse", "page": title, "prop": "text", "format": "json", "origin": "*",
            })
            response.raise_for_status()
            payload = response.json()
            if "error" in payload:
                raise RuntimeError(f"Wiki page {page!r}: {payload['error'].get('info', 'unknown error')}")
            html = payload["parse"]["text"]["*"]
            for recipe in parse_page(html, url, page.replace("_", " ")):
                recipes[recipe.id] = recipe
    return Catalog(
        source="Official Graveyard Keeper Wiki (Fandom)",
        license="CC BY-NC-SA; preserve attribution and verify intended use.",
        updated_at=datetime.now(timezone.utc), recipes=sorted(recipes.values(), key=lambda r: r.id),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Graveyard Keeper recipes from the official wiki.")
    parser.add_argument("pages", nargs="*", default=DEFAULT_PAGES, help="Wiki page titles to import")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between requests")
    args = parser.parse_args()
    catalog = import_catalog(args.pages, args.delay)
    save_catalog(catalog)
    print(f"Saved {len(catalog.recipes)} recipes to data/catalog.json")


if __name__ == "__main__":
    main()
