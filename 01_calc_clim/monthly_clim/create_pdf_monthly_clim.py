#!/usr/bin/env python3
"""Generate a single PDF from all PNG figures in a directory."""

import argparse
from pathlib import Path

from fpdf import FPDF
from PIL import Image


def make_pdf(pdf_path, images, two_per_page=False, page_width=210, page_height=297, margin=15, space=10):
    """Create a PDF from an ordered list of image paths."""
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)

    if two_per_page:
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
    else:
        max_w = page_width - 2 * margin
        max_h = page_height - 2 * margin

        for img_path in images:
            pdf.add_page()
            with Image.open(img_path) as img:
                w, h = img.size

            ratio = min(max_w / w, max_h / h)
            pdf_w = w * ratio
            pdf_h = h * ratio
            x = (page_width - pdf_w) / 2
            y = (page_height - pdf_h) / 2
            pdf.image(str(img_path), x=x, y=y, w=pdf_w, h=pdf_h)

    pdf.output(str(pdf_path))


def collect_png_files(base_dir: Path):
    """Collect all PNG files under the input directory."""
    return sorted(base_dir.rglob("*.png"))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a single PDF from all PNG files in a directory."
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
        help="Output directory for generated PDF. Defaults to input directory.",
    )
    parser.add_argument(
        "--outfile",
        help="Output PDF file name. Defaults to all_figures.pdf.",
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

    images = collect_png_files(base_dir)
    if not images:
        raise SystemExit("No PNG files were found in the input directory.")

    pdf_name = args.outfile if args.outfile else "all_figures.pdf"
    pdf_path = out_dir / pdf_name

    print(f"Creating {pdf_path} with {len(images)} images...")
    make_pdf(pdf_path, images, two_per_page=args.two_per_page)
    print("Done.")


if __name__ == "__main__":
    main()
