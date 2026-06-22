# Graveyard Keeper Catalog API

API local en FastAPI para materiales y recetas de *Graveyard Keeper*. Los datos se importan desde la [wiki oficial en Fandom](https://graveyardkeeper.fandom.com/wiki/Graveyard_Keeper_Wiki), que declara licencia CC BY-NC-SA. Conserva la atribución y revisa la licencia antes de publicar o monetizar derivados.

## Ejecutar

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.scraper
uvicorn app.main:app --reload
```

Abre `http://127.0.0.1:8000/docs` para probarla. El importador espera un segundo entre solicitudes y guarda el resultado en `data/catalog.json`.

## Rutas

- `GET /health`
- `GET /recipes?output=bread&ingredient=dough&station=Cooking`
- `GET /recipes/{recipe_id}`
- `GET /materials`
- `GET /meta`

## Ampliar cobertura

El importador ya lee `Cooking`, `Alchemy`, `Furnace` y `Alchemy mill`. Para sumar una página de estación, ejecútalo con sus títulos:

```bash
python -m app.scraper "Carpenter's workbench" "Stone cutter"
```

Las tablas se identifican por sus columnas **Item Produced** y **Materials Required**. Si una página usa otra estructura, añade un adaptador específico en `app/scraper.py` y mantén la URL de la fuente por receta.

## Desplegar gratis en Render

1. Crea un repositorio en GitHub y sube este proyecto, incluido `data/catalog.json`.
2. En [Render](https://render.com), selecciona **New → Blueprint** y conecta el repositorio.
3. Render detectará `render.yaml`. Confirma el servicio gratuito y pulsa **Apply**.
4. Al terminar, Render mostrará una URL como `https://graveyard-keeper-catalog-api.onrender.com`. La documentación estará en `/docs`.

El plan gratuito se suspende después de un periodo sin tráfico, por lo que la primera solicitud posterior puede tardar unos segundos. Para actualizar los datos, ejecuta `python -m app.scraper`, confirma el nuevo `data/catalog.json` en Git y vuelve a subirlo a GitHub; Render desplegará el cambio automáticamente.
