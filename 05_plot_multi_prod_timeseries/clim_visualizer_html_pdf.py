#!/usr/bin/env python3
import yaml
from pathlib import Path
import argparse
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

# --- ARGUMENTI ---
parser = argparse.ArgumentParser(description="Genera HTML e PDF per le serie di plot di una variabile")
parser.add_argument("-v", "--variable", required=True, help="Nome della variabile (es. ALK, DIC, pCO2, O2O)")
parser.add_argument("-i", "--indirizzo_input", required=True, help="Cartella base degli input (OUTDIR), contenente la sottocartella VAR con le immagini)")
args = parser.parse_args()

# --- CONFIG ---
script_dir = Path(__file__).resolve().parent
yaml_file = script_dir / "html_config.yaml"
var = args.variable
base_input = Path(args.indirizzo_input)
if not base_input.exists():
    raise FileNotFoundError(f"Input directory non trovato: {base_input}")

outdir_input = base_input / var
if not outdir_input.exists():
    outdir_input = base_input

# --- CARICA YAML ---
with open(yaml_file) as f:
    cfg = yaml.safe_load(f)
sottobacini = cfg.get("ordine_sottobacini", [])

# --- RACCOGLIE FIGURE ---
image_items = []
for sb in sottobacini:
    image_path = outdir_input / f"{var}_timeseries_{sb}.png"
    if not image_path.exists():
        alt_path = outdir_input / f"{var}_timeseries_{sb}_subplot.png"
        if alt_path.exists():
            image_path = alt_path

    if image_path.exists():
        image_items.append((sb, image_path))
    else:
        print(f"ATTENZIONE: immagine non trovata per {sb}: {image_path}")

if not image_items:
    raise FileNotFoundError(f"Nessuna immagine trovata in {outdir_input} per variabile {var}")

# --- TEMPLATE HTML ---
html_template = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>Visualizzazione Plot - {var}</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
  h1 {{ text-align: center; margin-bottom: 20px; }}
  .figure-item {{ background: white; margin-bottom: 30px; padding: 15px; border-radius: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.15); }}
  .figure-item h2 {{ margin: 0 0 10px; font-size: 1.1rem; }}
  .figure-item img {{ width: 100%; max-width: 100%; height: auto; display: block; border-radius: 6px; }}
  .caption {{ margin-top: 8px; color: #333; font-size: 0.95rem; }}
</style>
</head>
<body>
<h1>Visualizzazione Plot - {var}</h1>
{figure_items}
</body>
</html>
"""

figure_items = []
for sb, image_path in image_items:
    figure_items.append(
        f'  <div class="figure-item">\n'
        f'    <h2>{sb}</h2>\n'
        f'    <img src="{image_path.name}" alt="{sb} - {var}">\n'
        f'    <div class="caption">Sottobacino: {sb}</div>\n'
        f'  </div>'
    )

html_file = outdir_input / "index.html"
html_content = html_template.format(var=var, figure_items="\n".join(figure_items))
with open(html_file, "w") as f:
    f.write(html_content)
print(f"HTML generato per {var} → {html_file}")

# --- CREA PDF ---
pdf_file = outdir_input / f"{var}.pdf"
with PdfPages(pdf_file) as pdf:
    for sb, image_path in image_items:
        fig = plt.figure(figsize=(11.69, 8.27))  # landscape A4
        ax = fig.add_subplot(111)
        ax.axis("off")
        img = plt.imread(image_path)
        ax.imshow(img)
        ax.set_title(f"{var} - {sb}", fontsize=14, pad=16)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

print(f"PDF generato per {var} → {pdf_file}")
