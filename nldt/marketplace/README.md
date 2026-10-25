# EDIC Marketplace (static)

Catalogue UI for nLDT / LDT CitiVERSE EDIC recipes from the local `catalog.json`.

## Run locally

From this directory (or serve `nldt/` and open `/marketplace/`):

```bash
cd nldt/marketplace
python3 -m http.server 8765
```

Open [http://localhost:8765/](http://localhost:8765/).

## Deploy on Fly.io

```bash
cd nldt/marketplace
fly auth login
fly apps create edic-marketplace
fly deploy
```

Live: **https://edic-marketplace.fly.dev** (`fly.toml`, region `ams`, nginx on 8080).

Basic auth: user `edic` / password `barcelona2026`.

## Features

- **NL / EN** toggle (stored in `localStorage`)
- Theme filters + search
- Recipe detail: application blurb, processes, EDIC metadata
- Local catalogue only (`data/catalog.json` + `data/recipes/`)

## Refresh catalogue data

After editing recipes or `recipes/edic-asset-map.json`:

```bash
cd nldt && .venv/bin/python scripts/build_marketplace_catalog.py
```

This refreshes `data/catalog.json` and copies recipe JSON into `data/recipes/` (links in the UI point there). Owners are shown as **LDT EDIC** (CitiVERSE spatial) or **EuropAI** (HCS / IMPACTS).