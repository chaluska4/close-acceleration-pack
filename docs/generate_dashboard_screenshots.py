"""
Generates the three README hero screenshots in docs/images/ from the real,
final workbooks in deliverables/ — actual Excel cell content (fonts, fills,
merges, RAG colors), not a redrawn approximation.

macOS-only: renders each workbook off-screen via Quick Look (`qlmanage -t`),
the only reproducible local renderer available without LibreOffice/Excel
GUI automation (headless, no screen-capture permission required). Quick
Look's xlsx generator (a) does not draw embedded chart images, and (b) clips
content to a fixed canvas that ignores the workbook's own zoom/print-scale
settings — so each shot is built from one or two crops of the full render,
positioned to land only on content that's fully visible (verified by pixel
inspection against this specific layout), never mid-column or mid-sentence.
That means these crop boxes are tuned to the current card/column layout in
close_pack/excel_export.py; if that layout changes materially, re-run this
and eyeball the output before committing.

Run after `make all` has produced deliverables/*.xlsx:

    python docs/generate_dashboard_screenshots.py
"""

import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
DELIVERABLES = REPO_ROOT / "deliverables"
IMAGES_DIR = Path(__file__).parent / "images"


def render_thumbnail(xlsx_path: Path, out_dir: Path) -> Path:
    subprocess.run(
        ["qlmanage", "-t", "-s", "2000", "-o", str(out_dir), str(xlsx_path)],
        check=True, capture_output=True,
    )
    png_path = out_dir / f"{xlsx_path.name}.png"
    if not png_path.exists():
        raise RuntimeError(f"qlmanage did not produce a thumbnail for {xlsx_path}")
    return png_path


def save(img: Image.Image, name: str) -> None:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    out = IMAGES_DIR / name
    img.save(out)
    print(f"  docs/images/{name}  ({img.size[0]}x{img.size[1]})")


def build_kpi_dashboard_png(render: Image.Image) -> Image.Image:
    # Title + "Executive KPIs" + 4 of 6 KPI cards + Management Insights
    # (Top Favorable/Top Unfavorable). Cards 5-6 and the "Risk & Action"
    # line sit past Quick Look's render edge, so this crop stops just
    # before either would appear partially cut.
    return render.crop((0, 0, 1850, 560))


def build_variance_summary_png(render: Image.Image) -> Image.Image:
    # The 4-metric card row on this sheet is wider than Quick Look's canvas
    # (even 1 card is ~950px), so this composites the title block with the
    # Favorable/Unfavorable Drivers commentary instead — the clearest,
    # fully-visible demonstration of the favorable/unfavorable + materiality
    # narrative logic.
    title = render.crop((0, 0, 1150, 235))
    drivers = render.crop((0, 815, 1150, 1250))
    gap = 10
    combo = Image.new("RGB", (1150, title.height + gap + drivers.height), "white")
    combo.paste(title, (0, 0))
    combo.paste(drivers, (0, title.height + gap))
    return combo


def build_close_calendar_png(render: Image.Image) -> Image.Image:
    # Top metadata/summary-box strip is wider than the task table (the
    # table's own right edge is capped tighter to stay clear of the
    # "Exception Notes" column, which Quick Look clips mid-sentence).
    top = render.crop((0, 0, 1830, 271))
    table = render.crop((0, 271, 1787, render.size[1]))
    combo = Image.new("RGB", (1830, top.height + table.height), "white")
    combo.paste(top, (0, 0))
    combo.paste(table, (0, top.height))
    return combo


def main():
    if sys.platform != "darwin":
        print("This script uses macOS Quick Look (qlmanage) and only runs on macOS.", file=sys.stderr)
        sys.exit(1)

    missing = [f for f in ("kpi_dashboard.xlsx", "variance_analysis.xlsx", "close_checklist.xlsx")
               if not (DELIVERABLES / f).exists()]
    if missing:
        print(f"Missing from deliverables/: {missing}. Run `make all` and copy them first.", file=sys.stderr)
        sys.exit(1)

    print("Writing screenshots:")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        kpi_render = Image.open(render_thumbnail(DELIVERABLES / "kpi_dashboard.xlsx", tmp_path))
        save(build_kpi_dashboard_png(kpi_render), "kpi-dashboard.png")

        var_render = Image.open(render_thumbnail(DELIVERABLES / "variance_analysis.xlsx", tmp_path))
        save(build_variance_summary_png(var_render), "variance-summary.png")

        close_render = Image.open(render_thumbnail(DELIVERABLES / "close_checklist.xlsx", tmp_path))
        save(build_close_calendar_png(close_render), "close-calendar.png")


if __name__ == "__main__":
    main()
