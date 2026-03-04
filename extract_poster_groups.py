#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "PyMuPDF>=1.24.0",
# ]
# ///

"""Extract grouped collection panels from a layered Hot Wheels poster PDF.

Workflow:
1) Opens the source PDF.
2) Disables background-like Optional Content Groups (layers), when present.
3) Finds panel anchors using occurrences of "MINI COLLECTION" text.
4) Builds a 3x4 crop grid from anchor midpoints.
5) Exports each crop to its own PDF page in an output folder.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Sequence, Tuple

import fitz  # PyMuPDF



def cluster_positions(values: Sequence[float], tolerance: float = 30.0) -> List[float]:
    """Cluster nearly-equal coordinates and return sorted cluster centers."""
    if not values:
        return []

    sorted_values = sorted(values)
    clusters: List[List[float]] = [[sorted_values[0]]]

    for value in sorted_values[1:]:
        if abs(value - clusters[-1][-1]) <= tolerance:
            clusters[-1].append(value)
        else:
            clusters.append([value])

    return [sum(cluster) / len(cluster) for cluster in clusters]


def symmetric_bounds(centers: Sequence[float], limit_min: float, limit_max: float) -> List[Tuple[float, float]]:
    """Convert sorted centers to non-overlapping, midpoint-based bands."""
    if not centers:
        return []

    centers = sorted(centers)
    mids = [(a + b) / 2 for a, b in zip(centers, centers[1:])]

    first = max(limit_min, centers[0] - (mids[0] - centers[0])) if mids else limit_min
    last = min(limit_max, centers[-1] + (centers[-1] - mids[-1])) if mids else limit_max

    edges = [first, *mids, last]
    return list(zip(edges, edges[1:]))


def nearest_index(centers: Sequence[float], value: float) -> int:
    return min(range(len(centers)), key=lambda i: abs(centers[i] - value))


def disable_background_layers(doc: fitz.Document) -> List[str]:
    """Disable likely background/crop layers by OCG name and return disabled names."""
    ocgs = doc.get_ocgs() or {}
    if not ocgs:
        return []

    off_xrefs = []
    disabled = []
    for xref, info in ocgs.items():
        name = (info.get("name") or "").strip().lower()
        if any(token in name for token in ("background", "bg", "cropmark", "crop")):
            off_xrefs.append(xref)
            disabled.append(info.get("name", str(xref)))

    if off_xrefs:
        doc.set_layer(-1, off=off_xrefs)

    return disabled


def build_crop_rects(page: fitz.Page, anchor_phrase: str, expected_count: int) -> List[Tuple[int, int, fitz.Rect]]:
    anchors = page.search_for(anchor_phrase)
    if len(anchors) != expected_count:
        raise RuntimeError(
            f"Expected {expected_count} '{anchor_phrase}' anchors, found {len(anchors)}. "
            "Try a different anchor phrase or expected count."
        )

    centers = [((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2) for r in anchors]
    x_clusters = cluster_positions([x for x, _ in centers])
    y_clusters = cluster_positions([y for _, y in centers])

    if len(x_clusters) != 3 or len(y_clusters) != 4:
        raise RuntimeError(
            f"Detected {len(x_clusters)} columns and {len(y_clusters)} rows; expected 3 columns x 4 rows."
        )

    x_bands = symmetric_bounds(x_clusters, page.rect.x0, page.rect.x1)
    y_bands = symmetric_bounds(y_clusters, page.rect.y0, page.rect.y1)

    crops: List[Tuple[int, int, fitz.Rect]] = []
    for x, y in centers:
        col = nearest_index(x_clusters, x)
        row = nearest_index(y_clusters, y)
        x0, x1 = x_bands[col]
        y0, y1 = y_bands[row]

        # Small insets remove neighbor bleed at boundaries.
        inset_x = 8
        inset_y = 8
        rect = fitz.Rect(x0 + inset_x, y0 + inset_y, x1 - inset_x, y1 - inset_y)
        crops.append((row, col, rect))

    # One file per grid location in row-major order.
    return sorted(crops, key=lambda t: (t[0], t[1]))


def export_crop_pdf(page: fitz.Page, rect: fitz.Rect, output_path: Path, dpi: int) -> None:
    pix = page.get_pixmap(clip=rect, dpi=dpi, alpha=False)
    out_doc = fitz.open()
    out_page = out_doc.new_page(width=rect.width, height=rect.height)
    out_page.insert_image(out_page.rect, pixmap=pix)
    out_doc.save(output_path)
    out_doc.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract 12 grouped panels from a Hot Wheels poster PDF.")
    parser.add_argument("input_pdf", type=Path, help="Path to source PDF.")
    parser.add_argument("--output-dir", type=Path, default=Path("output/group_pdfs"), help="Output directory.")
    parser.add_argument("--anchor-phrase", default="MINI COLLECTION", help="Text phrase used to anchor each panel.")
    parser.add_argument("--expected-count", type=int, default=12, help="Expected number of panel groups.")
    parser.add_argument("--dpi", type=int, default=220, help="Rasterization DPI for each extracted PDF.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(args.input_pdf)
    disabled = disable_background_layers(doc)

    page = doc[0]
    crops = build_crop_rects(page, args.anchor_phrase, args.expected_count)

    for index, (row, col, rect) in enumerate(crops, start=1):
        out_name = f"group_{index:02d}_r{row+1}c{col+1}.pdf"
        export_crop_pdf(page, rect, args.output_dir / out_name, dpi=args.dpi)

    print(f"Wrote {len(crops)} PDFs to: {args.output_dir}")
    if disabled:
        print("Disabled layers:", ", ".join(disabled))
    else:
        print("No optional content layers disabled.")

    doc.close()


if __name__ == "__main__":
    main()
