#!/usr/bin/env python3
import yaml
from pathlib import Path
import argparse

# --- ARGUMENTI ---
parser = argparse.ArgumentParser(description="Genera HTML per climatologie")
parser.add_argument("-v", "--variable", required=True, help="Nome della variabile (es. N1p, N3n)")
parser.add_argument("-i", "--indirizzo_input", required=True, help="Cartella base degli input (OUTDIR)")
args = parser.parse_args()

# --- CONFIG ---
yaml_file = "html_config.yaml"
var = args.variable
outdir_input = Path(args.indirizzo_input) / var  # Cartella con le immagini
outdir_input.mkdir(parents=True, exist_ok=True)  # crea cartella se non esiste

# --- CARICA YAML ---
with open(yaml_file) as f:
    cfg = yaml.safe_load(f)
sottobacini = cfg["ordine_sottobacini"]

# --- TEMPLATE HTML ---
html_template = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>Visualizzazione Climatologie - {var}</title>
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
<h1>Visualizzazione Climatologie Mediterraneo - {var}</h1>
<div class="grid">
{grid_items}
</div>
</body>
</html>
"""

# --- CREA HTML ---
grid_items = "\n".join(
    f'  <div class="grid-item"><img src="{sb}_{var}_clima_float_emodnet.png" alt="{sb}"><p>{sb}</p></div>'
    for sb in sottobacini
    if (outdir_input / f"{sb}_{var}_clima_float_emodnet.png").exists()
)

html_file = outdir_input / "index.html"
html_content = html_template.format(var=var, grid_items=grid_items)

with open(html_file, "w") as f:
    f.write(html_content)

print(f"HTML generato per {var} → {html_file}")
