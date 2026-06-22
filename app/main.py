from __future__ import annotations

from contextlib import asynccontextmanager

from typing import Optional, Union

from fastapi import FastAPI, HTTPException, Query

from app.models import Catalog, Recipe
from app.storage import load_catalog


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.catalog = load_catalog()
    yield


app = FastAPI(
    title="Graveyard Keeper Catalog API",
    version="0.1.0",
    description="Community-data catalog sourced from the official Fandom wiki.",
    lifespan=lifespan,
)
# Also initialize at import time so command-line consumers and tests can use
# the application without having to manually enter the ASGI lifespan context.
app.state.catalog = load_catalog()


def catalog_or_404() -> Catalog:
    catalog = app.state.catalog
    if catalog is None:
        raise HTTPException(503, "Catalog not imported yet. Run: python -m app.scraper")
    return catalog


@app.get("/health")
def health() -> dict[str, Union[str, int]]:
    catalog = app.state.catalog
    return {"status": "ok", "recipes": len(catalog.recipes) if catalog else 0}


@app.get("/recipes", response_model=list[Recipe])
def list_recipes(
    output: Optional[str] = Query(default=None, description="Case-insensitive output search"),
    ingredient: Optional[str] = Query(default=None, description="Case-insensitive ingredient search"),
    station: Optional[str] = None,
) -> list[Recipe]:
    recipes = catalog_or_404().recipes
    def matches(recipe: Recipe) -> bool:
        return (
            (not output or output.lower() in recipe.output.lower())
            and (not station or (recipe.station and station.lower() in recipe.station.lower()))
            and (not ingredient or any(ingredient.lower() in item.name.lower() for item in recipe.ingredients))
        )
    return [recipe for recipe in recipes if matches(recipe)]


@app.get("/recipes/{recipe_id}", response_model=Recipe)
def get_recipe(recipe_id: str) -> Recipe:
    for recipe in catalog_or_404().recipes:
        if recipe.id == recipe_id:
            return recipe
    raise HTTPException(404, "Recipe not found")


@app.get("/materials")
def list_materials() -> list[str]:
    catalog = catalog_or_404()
    return sorted({material.name for recipe in catalog.recipes for material in recipe.ingredients}, key=str.lower)


@app.get("/meta")
def metadata() -> dict[str, str]:
    catalog = catalog_or_404()
    return {"source": catalog.source, "license": catalog.license, "updated_at": catalog.updated_at.isoformat()}
