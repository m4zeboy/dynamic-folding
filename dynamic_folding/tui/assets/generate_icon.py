"""Generate the dynamic-folding Windows icon from the "Geometric Fold" brand mark.

Offline and deterministic — draws the five mark polygons (from the brand SVG, on a
100x100 grid) in the app accent ``#3B82F6`` at the brand opacities, supersampled for
clean edges, and writes a multi-size ``.ico`` (+ a ``.png``) next to this file.

Run:  uv run --no-sync python dynamic_folding/tui/assets/generate_icon.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ACCENT = (59, 130, 246)  # #3B82F6 (V1_B)

# (polygon points on the 100x100 grid, opacity) — drawn container-first.
SHAPES: list[tuple[list[tuple[int, int]], float]] = [
    ([(20, 20), (60, 20), (60, 40), (80, 40), (80, 80), (40, 80), (40, 60), (20, 60)], 0.12),
    ([(20, 20), (40, 40), (40, 60), (20, 60)], 0.80),
    ([(40, 40), (60, 40), (60, 60), (40, 60)], 0.60),
    ([(60, 40), (80, 40), (80, 80), (60, 80)], 1.00),
    ([(40, 60), (60, 60), (60, 80), (40, 80)], 0.40),
]

ICO_SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def render_master(size: int = 1024) -> Image.Image:
    """Render the mark at *size*x*size* (supersampled), transparent background."""
    scale = size / 100.0
    base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for points, opacity in SHAPES:
        layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        scaled = [(round(x * scale), round(y * scale)) for x, y in points]
        draw.polygon(scaled, fill=(*ACCENT, round(opacity * 255)))
        base = Image.alpha_composite(base, layer)
    return base


def main() -> None:
    out_dir = Path(__file__).resolve().parent
    master = render_master(1024)
    icon_256 = master.resize((256, 256), Image.LANCZOS)

    ico_path = out_dir / "dynamic-folding.ico"
    png_path = out_dir / "dynamic-folding.png"
    icon_256.save(ico_path, format="ICO", sizes=ICO_SIZES)
    icon_256.save(png_path, format="PNG")
    print(f"wrote {ico_path} (sizes={[s[0] for s in ICO_SIZES]})")
    print(f"wrote {png_path}")


if __name__ == "__main__":
    main()
