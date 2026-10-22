#!/usr/bin/env python3
from pathlib import Path
import argparse
import yaml

# --- ARGOMENTI ---
parser = argparse.ArgumentParser(description="Genera HTML per immagini PNG")
parser.add_argument("-v", "--variable", required=True, help="Nome della variabile (es. O2o, N3n)")
parser.add_argument("-i", "--indirizzo_input", required=True, help="Cartella contenente le immagini")
args = parser.parse_args()

# --- CONFIG ---
var = args.variable
outdir_input = Path(args.indirizzo_input)
config_file = Path(__file__).with_name("html_config.yaml")

# --- TEMPLATE HTML ---
html_template = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>Climatologie - {var}</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
  h1 {{ text-align: center; }}
  .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }}
  .grid-item {{ background: white; padding: 10px; border-radius: 8px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }}
  .grid-item img {{ max-width: 100%; height: auto; cursor: pointer; transition: transform 0.2s; }}
  .grid-item img:hover {{ transform: scale(1.05); }}
</style>
</head>
<body>
<h1>Climatologie - {var}</h1>
<div class="grid">
{grid_items}
</div>
</body>
</html>
"""

# --- ORDINE SOTTOBACINI DAL YAML ---
with open(config_file, "r") as f:
  config = yaml.safe_load(f)

subbasins_order = config.get("ordine_sottobacini", [])

# --- CERCA TUTTE LE PNG NELL'ORDINE DELLO YAML ---
images = []
for subbasin in subbasins_order:
  matches = sorted(outdir_input.glob(f"{subbasin}_*.png"))
  images.extend(matches)

# Se ci sono PNG non presenti nello YAML, li aggiungiamo alla fine in ordine alfabetico
known_names = {img.name for img in images}
remaining_images = sorted(
  img for img in outdir_input.glob("*.png") if img.name not in known_names
)
images.extend(remaining_images)

# --- CREA GRID ---
grid_items = "\n".join(
    f'  <div class="grid-item"><a href="{img.name}" target="_blank"><img src="{img.name}" alt="{img.stem}"></a><p>{img.stem}</p></div>'
    for img in images
)

# --- SCRIVE HTML ---
html_file = outdir_input / "index.html"
html_content = html_template.format(var=var, grid_items=grid_items)

with open(html_file, "w") as f:
    f.write(html_content)

print(f"HTML generato per {var} → {html_file}")
print(f"Immagini trovate: {len(images)}")



