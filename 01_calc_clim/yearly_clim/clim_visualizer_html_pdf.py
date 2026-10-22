#!/usr/bin/env python3
from pathlib import Path
import argparse
import html
import re

parser = argparse.ArgumentParser(description="Genera HTML per le climatologie")
parser.add_argument("-i", "--indirizzo_input", required=True, help="Cartella CLIMA_FLOAT_NEW")
parser.add_argument("-v", "--variable", required=True, help="Nome della variabile, es. N3n, O2o, P_l")
args = parser.parse_args()

base_dir = Path(args.indirizzo_input)
var = args.variable
outdir = base_dir / var
config_path = Path(__file__).with_name("html_config.yaml")

if not outdir.is_dir():
    raise FileNotFoundError(f"Cartella non trovata: {outdir}")

png_files = sorted(outdir.glob("*.png"))

if not png_files:
    raise FileNotFoundError(f"Nessun PNG trovato in {outdir}")


def read_basin_order(config_file: Path) -> list[str]:
    order: list[str] = []
    in_order_block = False

    with open(config_file, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("ordine_sottobacini:"):
                in_order_block = True
                continue
            if in_order_block:
                match = re.match(r"^-\s*(\S+)", line)
                if match:
                    order.append(match.group(1))
                elif not line.startswith("-"):
                    break

    return order


basin_order = read_basin_order(config_path)
basin_rank = {name: rank for rank, name in enumerate(basin_order)}


def png_sort_key(png_path: Path) -> tuple[int, str]:
    basin_name = png_path.stem.split("_", 1)[0]
    return (basin_rank.get(basin_name, len(basin_rank)), png_path.stem)


png_files = sorted(png_files, key=png_sort_key)

html_template = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Climatologie - {var}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
h1 {{ text-align: center; }}
.grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }}
.grid-item {{ background: white; padding: 10px; border-radius: 8px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }}
.grid-item img {{ max-width: 100%; height: auto; cursor: pointer; transition: transform 0.2s; }}
.grid-item img:hover {{ transform: scale(1.05); }}
.grid-item p {{ margin: 8px 0 0; font-weight: bold; }}
a {{ text-decoration: none; color: inherit; }}
@media (max-width: 1200px) {{ .grid {{ grid-template-columns: repeat(3, 1fr); }} }}
@media (max-width: 800px) {{ .grid {{ grid-template-columns: repeat(2, 1fr); }} }}
@media (max-width: 500px) {{ .grid {{ grid-template-columns: 1fr; }} }}
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

grid_items = "\n".join(
    f'''  <div class="grid-item">
    <a href="{html.escape(png.name)}" target="_blank">
      <img src="{html.escape(png.name)}" alt="{html.escape(png.stem)}">
      <p>{html.escape(png.stem)}</p>
    </a>
  </div>'''
    for png in png_files
)

html_content = html_template.format(
    var=html.escape(var),
    grid_items=grid_items
)

html_file = outdir / "index.html"

with open(html_file, "w") as f:
    f.write(html_content)

print(f"HTML generato: {html_file}")
print(f"PNG trovati: {len(png_files)}")

