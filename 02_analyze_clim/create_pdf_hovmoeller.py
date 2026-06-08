#!/usr/bin/env python3
import argparse


def argument():
    parser = argparse.ArgumentParser(
        description='Collect Hovmoeller PNG figures into a PDF, one page per figure.',
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        '--indir', '-i',
        type=str,
        required=True,
        help='Directory containing the Hovmoeller PNG files.',
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Output PDF file path. Default: <indir>/hovmoeller.pdf',
    )
    parser.add_argument(
        '--dataset', '-d',
        choices=['superfloat', 'coriolis', 'both'],
        default='both',
        help='Which dataset to include (default: both).',
    )
    return parser.parse_args()


args = argument()

from fpdf import FPDF
from pathlib import Path
from PIL import Image

BASE_DIR = Path(args.indir)

# standard basin order as in OGS.Pred (atl excluded)
BASIN_ORDER = ['alb', 'swm1', 'swm2', 'nwm', 'tyr1', 'tyr2',
               'adr1', 'adr2', 'aeg', 'ion1', 'ion2', 'ion3',
               'lev1', 'lev2', 'lev3', 'lev4']

# build ordered list: superfloat then coriolis per basin
all_pngs_map = {p.name: p for p in BASE_DIR.glob('*_hovmoeller.png')}
all_pngs = []
for basin in BASIN_ORDER:
    for dataset in ('superfloat', 'coriolis'):
        key = f'{basin}_{dataset}_hovmoeller.png'
        if key in all_pngs_map:
            all_pngs.append(all_pngs_map[key])
# append any remaining files not matching the pattern
known = set(str(p) for p in all_pngs)
for p in sorted(BASE_DIR.glob('*_hovmoeller.png')):
    if str(p) not in known:
        all_pngs.append(p)

if args.dataset != 'both':
    all_pngs = [p for p in all_pngs if f'_{args.dataset}_' in p.name]

if not all_pngs:
    print(f'No Hovmoeller PNG files found in {BASE_DIR}')
    raise SystemExit(1)

# output path
if args.output is None:
    tag = '' if args.dataset == 'both' else f'_{args.dataset}'
    outfile = BASE_DIR / f'hovmoeller{tag}.pdf'
else:
    outfile = Path(args.output)

# A4 landscape (wider than tall — suits the wide Hovmoeller figures)
PAGE_W = 297
PAGE_H = 210
MARGIN = 10

pdf = FPDF(orientation='L', unit='mm', format='A4')
pdf.set_auto_page_break(auto=False)

MAX_W = PAGE_W - 2 * MARGIN
MAX_H = PAGE_H - 2 * MARGIN

for png in all_pngs:
    print(f'Adding {png.name} ...')
    im = Image.open(png)
    w, h = im.size
    ratio = min(MAX_W / w, MAX_H / h)
    pdf_w = w * ratio
    pdf_h = h * ratio
    x = (PAGE_W - pdf_w) / 2
    y = (PAGE_H - pdf_h) / 2

    pdf.add_page()
    # header: filename as small caption
    pdf.set_font('Helvetica', size=7)
    pdf.set_xy(MARGIN, MARGIN / 2)
    pdf.cell(0, 4, txt=png.stem.replace('_', '  '), ln=0)
    pdf.image(str(png), x=x, y=y, w=pdf_w, h=pdf_h)

pdf.output(str(outfile))
print(f'\nPDF saved → {outfile}')
