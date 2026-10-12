"""Export the site's CSS milestone mark as a portal-ready PNG.

Requires Pillow. The proportions and colors mirror `.mark` / `.mark-grid` in
src/styles.css; run from the repository root with `python scripts/render_logo.py`.
"""

from pathlib import Path

from PIL import Image, ImageDraw


SCALE = 4
SIZE = 1024


def px(value: int) -> int:
    return value * SCALE


def render() -> None:
    side = px(SIZE)
    logo = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    background = ImageDraw.Draw(logo)
    background.rounded_rectangle(
        (0, 0, side - 1, side - 1),
        radius=px(304),
        fill="#112640",
        outline="#234666",
        width=px(14),
    )

    bars = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    drawing = ImageDraw.Draw(bars)
    for left, top, right in ((171, 583, 342), (427, 384, 598), (683, 185, 854)):
        drawing.rounded_rectangle(
            (px(left), px(top), px(right), px(839)),
            radius=px(75),
            fill="#5ad6ac",
        )
    bars = bars.rotate(-28, resample=Image.Resampling.BICUBIC, center=(side / 2, side / 2))
    logo.alpha_composite(bars)

    output = Path(__file__).resolve().parents[1] / "public" / "milestonebond-logo.png"
    logo.resize((SIZE, SIZE), Image.Resampling.LANCZOS).save(output, optimize=True)
    print(output)


if __name__ == "__main__":
    render()
