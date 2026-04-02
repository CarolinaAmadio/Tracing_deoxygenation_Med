#!/usr/bin/env python3
import argparse
def argument():
    parser = argparse.ArgumentParser(description = '''
    counts the available BGC-Argo float profiles per basin and plots their monthly distribution.
    ''', formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(   '--indir','-i',
                                type = str,
                                required = True,
                                help = ' *png')
    return parser.parse_args()


args = argument()

from fpdf import FPDF
from pathlib import Path
from PIL import Image

BASE_DIR = Path(args.indir)
OUTPUT_DIR = BASE_DIR  # salva PDF nella stessa cartella

# dimensioni pagina A4 in mm
PAGE_WIDTH = 210
PAGE_HEIGHT = 297
MARGIN = 15  # margine alto, basso e laterale
SPACE_BETWEEN = 10  # spazio tra le due immagini

# dimensioni massime per ciascuna immagine
MAX_W = (PAGE_WIDTH - 2*MARGIN - SPACE_BETWEEN) / 2
MAX_H = PAGE_HEIGHT - 2*MARGIN

for var_folder in sorted(BASE_DIR.iterdir()):
    if not var_folder.is_dir():
        continue
    print(f"Processing {var_folder.name} ...")

    # crea un nuovo PDF per ogni sottocartella
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=False)

    images = sorted(var_folder.glob("*.png"))
    i = 0
    while i < len(images):
        pdf.add_page()
        # prima immagine a sinistra
        im1 = Image.open(images[i])
        w, h = im1.size
        ratio = min(MAX_W / w, MAX_H / h)
        pdf_w, pdf_h = w*ratio, h*ratio
        x1 = MARGIN
        y1 = (PAGE_HEIGHT - pdf_h) / 2
        pdf.image(str(images[i]), x=x1, y=y1, w=pdf_w, h=pdf_h)

        # seconda immagine a destra (se c'è)
        if i+1 < len(images):
            im2 = Image.open(images[i+1])
            w, h = im2.size
            ratio = min(MAX_W / w, MAX_H / h)
            pdf_w, pdf_h = w*ratio, h*ratio
            x2 = MARGIN + MAX_W + SPACE_BETWEEN
            y2 = (PAGE_HEIGHT - pdf_h) / 2
            pdf.image(str(images[i+1]), x=x2, y=y2, w=pdf_w, h=pdf_h)

        i += 2  # due immagini per pagina

    pdf_file = OUTPUT_DIR / f"{var_folder.name}.pdf"
    pdf.output(str(pdf_file))
    print(f"PDF generato → {pdf_file}")

print("Tutti i PDF generati!")
