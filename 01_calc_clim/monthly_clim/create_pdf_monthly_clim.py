#!/usr/bin/env python3
"""Generate one PDF per sub-basin / variable group from monthly climatology PNGs.

The script groups PNG filenames by the prefix before the `_month_XX_` token.
Example:
  tyr1_O2o_month_01_clima_float_emodnet.png
  tyr1_O2o_month_02_clima_float_emodnet.png

These are grouped as `tyr1_O2o` and saved as `tyr1_O2o.pdf`.
"""

import argparse
from pathlib import Path
from collections import defaultdict

from fpdf import FPDF
from PIL import Image


def make_pdf_group(pdf_path, images, page_width=210, page_height=297, margin=15, space=10):
    """Create a PDF from an ordered list of image paths."""
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)

    max_w = (page_width - 2 * margin - space) / 2
    max_h = page_height - 2 * margin

    for i in range(0, len(images), 2):
        pdf.add_page()

        for slot in range(2):
            idx = i + slot
            if idx >= len(images):
                break

            img_path = images[idx]
            with Image.open(img_path) as img:
                w, h = img.size

            ratio = min(max_w / w, max_h / h)
            pdf_w = w * ratio
            pdf_h = h * ratio
            x = margin + slot * (max_w + space)
            y = (page_height - pdf_h) / 2

            pdf.image(str(img_path), x=x, y=y, w=pdf_w, h=pdf_h)

    pdf.output(str(pdf_path))


def collect_png_groups(base_dir: Path):
    """Collect PNGs and group them by prefix before `_month_XX_`."""
    groups = defaultdict(list)
    for path in sorted(base_dir.rglob("*.png")):
        stem = path.name
        if "_month_" not in stem:
            continue
        prefix = stem.split("_month_")[0]
        groups[prefix].append(path)
    return groups


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create one PDF per sub-basin/variable group from monthly climatology PNGs."
    )
    parser.add_argument(
        "-i",
        "--indir",
        required=True,
        help="Input directory containing PNG files (or subdirectories).",
    )
    parser.add_argument(
        "-o",
        "--outdir",
        help="Output directory for generated PDFs. Defaults to input directory.",
    )
    parser.add_argument(
        "--two-per-page",
        action="store_true",
        help="Place two images per page instead of one.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    base_dir = Path(args.indir).expanduser().resolve()
    if not base_dir.exists() or not base_dir.is_dir():
        raise SystemExit(f"Input directory does not exist: {base_dir}")

    out_dir = Path(args.outdir).expanduser().resolve() if args.outdir else base_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    groups = collect_png_groups(base_dir)
    if not groups:
        raise SystemExit("No PNG files matching '*_month_XX_*.png' were found.")

    print(f"Found {len(groups)} groups in {base_dir}")

    for prefix, paths in sorted(groups.items()):
        images = sorted(paths, key=lambda p: p.name)
        pdf_file = out_dir / f"{prefix}.pdf"
        print(f"Creating {pdf_file} with {len(images)} images...")
        make_pdf_group(pdf_file, images)

    print("Done.")


if __name__ == "__main__":
    main()
