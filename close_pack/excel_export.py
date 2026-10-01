"""
All Excel presentation lives here: fonts, fills, borders, conditional
formatting, charts, named styles, column widths, freeze panes, and print
setup. This module contains every openpyxl import in the project.

Calculation modules (variance.py, kpi.py, controls.py) hand this module
clean DataFrames/dicts; this module never computes a number, it only
formats ones it's given. Charts are matplotlib PNGs embedded as images
(openpyxl has no public API for Excel's native Sparkline object, and this
gives the waterfall and trend charts a second life as README screenshots).

Restrained finance style: dark navy/gray for headers and neutral chrome;
green ONLY for favorable outcomes, red ONLY for unfavorable, amber ONLY
for watch items. Chart colors follow the dataviz skill's reference
palette (fixed-order categorical triad, single axis, legend for 2+
series). Spreadsheet CELL shading uses Excel's own conventional
light-fill/dark-font red-amber-green instead of the chart-canvas status
hexes — different medium, same restraint.
"""

import io
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, NamedStyle, PatternFill, Side
from openpyxl.drawing.image import Image as XLImage
from openpyxl.utils import get_column_letter
from openpyxl.workbook.views import BookView
from openpyxl.worksheet.page import PageMargins

from close_pack import controls as controls_mod
from close_pack import kpi as kpi_mod
from close_pack import variance as variance_mod

COMPANY_NAME = "Beacon Outdoor Goods (fictional — synthetic data)"
# The clean, short form used for prominent titles (e.g. Summary!A1) —
# DERIVED from COMPANY_NAME, never a second hardcoded literal. A future
# company config changes COMPANY_NAME in this one place and every title
# in the workbook (long and short form) updates automatically.
COMPANY_SHORT_NAME = COMPANY_NAME.split(" (")[0]

# ---------------------------------------------------------------------
# Palette (see dataviz skill / references/palette.md) — 6-digit hex, no '#'.
# ---------------------------------------------------------------------
NAVY = "1F2A44"
STATUS_GOOD = "0CA30C"
STATUS_WARNING = "FAB219"
STATUS_CRITICAL = "D03B3B"
SERIES_ACTUAL = "2A78D6"
SERIES_BUDGET = "EB6834"
SERIES_FORECAST = "1BAF7A"
INK_PRIMARY = "0B0B0B"
INK_SECONDARY = "52514E"
INK_MUTED = "898781"
GRIDLINE = "E1E0D9"
BASELINE = "C3C2B7"

RAG_COLOR = {"Green": STATUS_GOOD, "Amber": STATUS_WARNING, "Red": STATUS_CRITICAL, "N/A": INK_MUTED}

# Excel's own conventional RAG cell shading (light fill + dark font) — a
# different medium than a chart canvas, so it uses Excel's native idiom.
FILL_GREEN, FONT_GREEN = "C6EFCE", "006100"
FILL_AMBER, FONT_AMBER = "FFEB9C", "9C6500"
FILL_RED, FONT_RED = "FFC7CE", "9C0006"
FILL_NEUTRAL, FONT_NEUTRAL = "F2F2F2", "666666"
RAG_FILL_FONT = {
    "Green": (FILL_GREEN, FONT_GREEN),
    "Amber": (FILL_AMBER, FONT_AMBER),
    "Red": (FILL_RED, FONT_RED),
    "N/A": (FILL_NEUTRAL, FONT_NEUTRAL),
}
# Close-calendar task status -> (fill, font). "Not Started"/"Not
# Applicable" are neutral (pending is not itself bad), matching the
# restrained-style rule that amber/red are reserved for actual watch/
# unfavorable items, not mere absence of progress.
TASK_STATUS_FILL_FONT = {
    "Complete": (FILL_GREEN, FONT_GREEN),
    "In Progress": (FILL_AMBER, FONT_AMBER),
    "Exception": (FILL_RED, FONT_RED),
    # Blocked (knock-on from an unresolved dependency) uses the SAME red as
    # Exception (the root cause) — both need attention, and the text label
    # itself already distinguishes "the problem" from "waiting on the
    # problem," so a second red shade would be decoration, not signal.
    "Blocked": (FILL_RED, FONT_RED),
    "Not Started": (FILL_NEUTRAL, FONT_NEUTRAL),
    "Not Applicable": (FILL_NEUTRAL, FONT_NEUTRAL),
}
CONTROL_STATUS_FILL_FONT = {
    "Effective": (FILL_GREEN, FONT_GREEN),
    "Exception": (FILL_RED, FONT_RED),
}


def _argb(hex6: str) -> str:
    return f"FF{hex6}"


def _mpl(hex6: str) -> str:
    return f"#{hex6}"


HEADER_FONT = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
HEADER_FILL = PatternFill("solid", fgColor=_argb(NAVY))
TITLE_FONT = Font(name="Calibri", bold=True, size=16, color=_argb(NAVY))
SUBTITLE_FONT = Font(name="Calibri", italic=True, size=10, color=_argb(INK_SECONDARY))
SECTION_FONT = Font(name="Calibri", bold=True, size=12, color=_argb(NAVY))
LABEL_FONT = Font(name="Calibri", bold=True, size=10, color=_argb(NAVY))
BODY_FONT = Font(name="Calibri", size=10, color=_argb(INK_PRIMARY))
NOTE_FONT = Font(name="Calibri", italic=True, size=8, color=_argb(INK_MUTED))
NM_FONT = Font(name="Calibri", size=10, color=_argb(INK_MUTED))

# Full-dollar formats (detail/audit sheets) and a $000s display-only format
# for the executive dashboard (the trailing comma is an Excel display-scale
# trick: it divides the DISPLAYED value by 1,000 without touching the
# stored number, so precision is never lost).
CURRENCY_FMT = '$#,##0;[RED]($#,##0)'
CURRENCY2_FMT = '$#,##0.00;[RED]($#,##0.00)'
CURRENCY_000_FMT = '$#,##0,"K";[RED]($#,##0,"K")'
PCT_FMT = "0.0%"
PCT_SIGNED_FMT = '+0.0%;-0.0%'
# Variance Detail's exact professional 3-part formats: positive; negative
# in accounting parentheses; a dash for zero — no color codes baked in,
# since favorability there is shown via cell fill (green/red), not font color.
DETAIL_DOLLAR_FMT = '$#,##0;($#,##0);-'
DETAIL_PCT_FMT = '0.0%;(0.0%);-'


# ---------------------------------------------------------------------
# Shared workbook plumbing
# ---------------------------------------------------------------------

def _register_named_styles(wb: Workbook) -> None:
    """Register 'currency' and 'percent' NamedStyles once per workbook."""
    if "currency" not in wb.named_styles:
        wb.add_named_style(NamedStyle(
            name="currency", font=BODY_FONT, number_format=CURRENCY_FMT,
            alignment=Alignment(horizontal="right"),
        ))
    if "percent" not in wb.named_styles:
        wb.add_named_style(NamedStyle(
            name="percent", font=BODY_FONT, number_format=PCT_FMT,
            alignment=Alignment(horizontal="right"),
        ))


def _print_setup(ws, title: str) -> None:
    """Landscape, fit-to-one-page-wide, with a title header and page footer."""
    ws.page_setup.orientation = "landscape"
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.page_margins = PageMargins(left=0.4, right=0.4, top=0.5, bottom=0.5)
    ws.oddHeader.center.text = title
    ws.oddFooter.right.text = "Page &P of &N"


def _write_title_block(ws, title: str, subtitle: str, start_row: int = 1, start_col: int = 1) -> int:
    ws.cell(row=start_row, column=start_col, value=title).font = TITLE_FONT
    ws.cell(row=start_row + 1, column=start_col, value=subtitle).font = SUBTITLE_FONT
    return start_row + 3


def _write_table_header(ws, row: int, headers: list, start_col: int = 1) -> None:
    for i, h in enumerate(headers, start=start_col):
        c = ws.cell(row=row, column=i, value=h)
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[row].height = 30


def _write_group_header(ws, row: int, groups: list) -> None:
    """groups: list of (label, start_col, end_col) merged group headers,
    written above the detailed column headers — used to visually separate
    'Actual vs Budget' from 'Actual vs Forecast' on the Variance Detail sheet."""
    for label, start_col, end_col in groups:
        if end_col > start_col:
            ws.merge_cells(start_row=row, start_column=start_col, end_row=row, end_column=end_col)
        c = ws.cell(row=row, column=start_col, value=label)
        c.font = Font(name="Calibri", bold=True, size=9, color=_argb(INK_SECONDARY))
        c.alignment = Alignment(horizontal="center")
        c.fill = PatternFill("solid", fgColor=_argb(FILL_NEUTRAL))
    ws.row_dimensions[row].height = 16


def _set_column_widths(ws, widths: dict) -> None:
    for col_idx, width in widths.items():
        ws.column_dimensions[get_column_letter(col_idx)].width = width


# ---------------------------------------------------------------------
# Pixel-accurate chart placement.
#
# openpyxl does not size an embedded image to its target cells — left to
# its defaults, an image is placed at its native PNG pixel size, which for
# a matplotlib figure is typically far larger than a handful of rows. That
# (plus advancing the next chart's row by a flat guess) is what caused the
# dashboard's charts to overlap. Every chart below is instead given an
# EXPLICIT pixel width/height computed from the sheet's actual column
# widths/row heights, so its footprint is exact and two charts can never
# collide as long as their target cell ranges don't.
# ---------------------------------------------------------------------

def _col_width_to_px(width: float) -> float:
    """Excel column 'character width' -> pixels (Calibri 11 default font;
    the standard Excel/ECMA-376 approximation: px = width*7 + 5)."""
    return round(width * 7 + 5)


def _row_height_to_px(points: float) -> float:
    """Row height in points -> pixels at 96 DPI (Excel/openpyxl's reference)."""
    return round(points * 4 / 3)


def _range_pixel_box(ws, start_col: int, end_col: int, start_row: int, end_row: int) -> tuple:
    """Total pixel width/height of the given 1-indexed inclusive cell range,
    from whatever column widths/row heights are ALREADY set on `ws` —
    call this only after setting explicit widths/heights for that range."""
    width = sum(
        _col_width_to_px(ws.column_dimensions[get_column_letter(c)].width or 8.43)
        for c in range(start_col, end_col + 1)
    )
    height = sum(
        _row_height_to_px(ws.row_dimensions[r].height or 15.0)
        for r in range(start_row, end_row + 1)
    )
    return width, height


def _figsize_for_box(box_w_px: float, box_h_px: float, base_height_in: float = 4.0) -> tuple:
    """A matplotlib figsize (inches) whose ASPECT RATIO matches the target
    pixel box. Rendering at this aspect first, then resizing to the exact
    box in `_embed_chart`, means no stretch/squish distortion — only a
    clean downscale (the source PNG is rendered at high DPI regardless)."""
    aspect = box_w_px / box_h_px
    return (aspect * base_height_in, base_height_in)


def _embed_chart(ws, png_bytes: io.BytesIO, anchor_cell: str,
                  start_col: int, end_col: int, start_row: int, end_row: int,
                  padding: float = 0.94) -> None:
    """Embed a chart at `anchor_cell`, explicitly sized (in pixels) to fill
    `padding` of the target cell range — never the PNG's native size. The
    padding leaves a visible margin on all sides of the image within its
    box, which is what keeps adjacent charts from visually touching even
    without a dedicated spacer column between them."""
    box_w, box_h = _range_pixel_box(ws, start_col, end_col, start_row, end_row)
    img = XLImage(png_bytes)
    img.width = box_w * padding
    img.height = box_h * padding
    ws.add_image(img, anchor_cell)


def _format_value(value: float, fmt: str) -> str:
    if fmt == "currency":
        return f"${value:,.0f}"
    return f"{value:.1%}"


def _wrapped_row_height(row_texts: dict, col_widths: dict, line_height: float = 14.0,
                         padding: float = 8.0, min_height: float = 30.0) -> float:
    """row_texts: {col_index: text}. col_widths: {col_index: column width in
    openpyxl character units}. Returns a row height tall enough that
    wrap_text won't visually clip whichever column needs the most lines —
    a fixed row height silently truncates long wrapped cells (e.g. the
    187-character Controls Log remediation text), so heights for any sheet
    with long free-text columns must be computed from content, not guessed."""
    max_lines = 1
    for col, text in row_texts.items():
        if not text:
            continue
        chars_per_line = max(int(col_widths.get(col, 20)), 8)
        lines = -(-len(str(text)) // chars_per_line)  # ceil division
        max_lines = max(max_lines, lines)
    return max(min_height, max_lines * line_height + padding)


def _write_note(ws, row: int, text: str, span_cols: int, start_col: int = 1) -> int:
    ws.merge_cells(start_row=row, start_column=start_col, end_row=row, end_column=start_col + span_cols - 1)
    cell = ws.cell(row=row, column=start_col, value=text)
    cell.font = NOTE_FONT
    cell.alignment = Alignment(wrap_text=True, vertical="top")
    return row + 1


# ---------------------------------------------------------------------
# Matplotlib chart rendering
# ---------------------------------------------------------------------

def _mpl_style() -> None:
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 9,
        "axes.edgecolor": _mpl(BASELINE),
        "axes.labelcolor": _mpl(INK_SECONDARY),
        "text.color": _mpl(INK_PRIMARY),
        "xtick.color": _mpl(INK_MUTED),
        "ytick.color": _mpl(INK_MUTED),
        "grid.color": _mpl(GRIDLINE),
        "grid.linewidth": 0.6,
        "axes.grid": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    })


def _fig_to_png(fig) -> io.BytesIO:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


_MONTH_ABBREV = {
    "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr", "05": "May", "06": "Jun",
    "07": "Jul", "08": "Aug", "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec",
}


def _month_labels(months: list) -> list:
    """'2025-01'..'2025-12' -> 'Jan'..'Dec'."""
    return [_MONTH_ABBREV[m.split("-")[1]] for m in months]


# Two-line/abbreviated x-axis labels for the bridge chart — "Professional
# Services" is the one leaf-level line long enough to collide with its
# neighbors at normal chart width; every other line item is short enough
# that widening the chart alone is sufficient.
_BRIDGE_LABEL_OVERRIDES = {"Professional Services": "Professional\nSvcs."}


def _bridge_axis_label(line_item: str) -> str:
    return _BRIDGE_LABEL_OVERRIDES.get(line_item, line_item)


def render_waterfall_png(components: list, budget_oi: float, actual_oi: float, month_label: str,
                          figsize: tuple = (10.6, 4.4)) -> io.BytesIO:
    """Operating Income bridge using ONLY leaf-level P&L drivers (Revenue,
    COGS, and the five opex lines — never Gross Profit/Total Opex/
    Operating Income as a bar, since those are calculated subtotals of
    the bars already shown and would double-count). Favorable
    contributions in status-good, unfavorable in status-critical; the two
    anchor bars (start/end) are neutral navy. `month_label` is the
    already-formatted reporting period (e.g. 'December 2025') used
    verbatim in a management-facing title — no internal/technical wording."""
    _mpl_style()
    labels = ["Budget\nOI"] + [_bridge_axis_label(c[0]) for c in components] + ["Actual\nOI"]
    contributions = [c[1] for c in components]
    n = len(labels)

    bottoms = [0.0] * n
    heights = [0.0] * n
    colors = [_mpl(NAVY)] * n

    heights[0] = budget_oi
    running = budget_oi
    for i, contribution in enumerate(contributions, start=1):
        bottoms[i] = min(running, running + contribution)
        heights[i] = abs(contribution)
        colors[i] = _mpl(STATUS_GOOD) if contribution >= 0 else _mpl(STATUS_CRITICAL)
        running += contribution
    heights[-1] = actual_oi

    fig, ax = plt.subplots(figsize=figsize)
    x = list(range(n))
    ax.bar(x, heights, bottom=bottoms, color=colors, width=0.62, edgecolor="white", linewidth=0.8)
    ax.grid(False)  # a labeled bridge chart doesn't need gridlines too

    running = budget_oi
    for i, contribution in enumerate(contributions, start=1):
        ax.plot([i - 1 + 0.31, i - 0.31], [running, running], color=_mpl(BASELINE), linewidth=1, zorder=1)
        running += contribution

    display_values = [budget_oi] + contributions + [actual_oi]
    max_top = max(b + h for b, h in zip(bottoms, heights))
    for i, (bottom, height, value) in enumerate(zip(bottoms, heights, display_values)):
        # variance_mod.format_k() falls back to whole dollars under $1,000,
        # so a small driver never mislabels itself "+$0K".
        text = variance_mod.format_k(value) if i in (0, n - 1) else \
            f"{'+' if value >= 0 else '-'}{variance_mod.format_k(abs(value))}"
        ax.text(i, bottom + height + max_top * 0.02, text, ha="center", va="bottom",
                 fontsize=8, fontweight="bold", color=_mpl(INK_PRIMARY))

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("Operating Income ($000s)")
    ax.set_ylim(0, max_top * 1.22)
    ax.set_title(f"{month_label} Operating Income Bridge — Budget to Actual", fontsize=12, fontweight="bold",
                 color=_mpl(NAVY), loc="left")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v / 1000:,.0f}K"))
    fig.tight_layout()
    return _fig_to_png(fig)


def render_revenue_trend_png(months: list, actual: list, budget: list, forecast: list,
                              figsize: tuple = (9.2, 2.7)) -> io.BytesIO:
    """Single-axis Revenue trend: Actual vs Budget vs Forecast, fixed-order
    categorical colors, legend (3 series), thin lines, recessive grid.
    `figsize` defaults to a wide standalone aspect (used for README
    screenshots); pass an aspect matched to the target grid cell when
    embedding in the dashboard so resizing to fit never distorts it."""
    _mpl_style()
    fig, ax = plt.subplots(figsize=figsize)
    x = list(range(len(months)))
    ax.plot(x, actual, color=_mpl(SERIES_ACTUAL), linewidth=2.2, marker="o", markersize=4, label="Actual")
    ax.plot(x, budget, color=_mpl(SERIES_BUDGET), linewidth=1.8, linestyle="--", marker="o", markersize=3, label="Budget")
    ax.plot(x, forecast, color=_mpl(SERIES_FORECAST), linewidth=1.8, linestyle=":", marker="o", markersize=3, label="Forecast")
    ax.set_xticks(x)
    ax.set_xticklabels(_month_labels(months), fontsize=8)
    ax.set_ylabel("Revenue ($)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v / 1000:,.0f}k"))
    ax.set_title("Revenue: Actual vs. Budget vs. Forecast (FY2025)", fontsize=11, fontweight="bold",
                 color=_mpl(NAVY), loc="left")
    ax.legend(frameon=True, facecolor="white", edgecolor="none", framealpha=0.9, loc="upper left", fontsize=8, ncol=3)

    # December-only end labels (not a label on every point, which would be
    # clutter) — the one month a reader most wants the exact figure for.
    last_idx = len(months) - 1
    for series_vals, color in ((actual, SERIES_ACTUAL), (budget, SERIES_BUDGET), (forecast, SERIES_FORECAST)):
        ax.annotate(f"${series_vals[-1] / 1000:,.0f}K", xy=(last_idx, series_vals[-1]),
                    xytext=(8, 0), textcoords="offset points", fontsize=8, fontweight="bold",
                    color=_mpl(color), va="center", ha="left")
    ax.set_xlim(-0.4, last_idx + 1.7)  # room for the December end labels, no clipping

    fig.tight_layout()
    return _fig_to_png(fig)


def render_margin_trend_png(months: list, gross_margin: list, operating_margin: list,
                             figsize: tuple = (9.2, 2.7)) -> io.BytesIO:
    """Single-axis trend: Gross Margin % and Operating Margin %."""
    _mpl_style()
    fig, ax = plt.subplots(figsize=figsize)
    x = list(range(len(months)))
    ax.plot(x, gross_margin, color=_mpl(SERIES_ACTUAL), linewidth=2.0, marker="o", markersize=3, label="Gross Margin %")
    ax.plot(x, operating_margin, color=_mpl(SERIES_BUDGET), linewidth=2.0, marker="o", markersize=3, label="Operating Margin %")
    ax.set_xticks(x)
    ax.set_xticklabels(_month_labels(months), fontsize=8)
    ax.set_ylabel("Margin %")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_title("Gross Margin % and Operating Margin % Trend", fontsize=11, fontweight="bold",
                 color=_mpl(NAVY), loc="left")
    ax.legend(frameon=True, facecolor="white", edgecolor="none", framealpha=0.9, loc="upper left", fontsize=8, ncol=2)
    fig.tight_layout()
    return _fig_to_png(fig)


def render_unit_economics_png(months: list, revenue_per_unit: list, cost_per_unit: list,
                               figsize: tuple = (9.2, 2.7)) -> io.BytesIO:
    """Single-axis trend: Revenue per Unit and (Total) Cost per Unit."""
    _mpl_style()
    fig, ax = plt.subplots(figsize=figsize)
    x = list(range(len(months)))
    ax.plot(x, revenue_per_unit, color=_mpl(SERIES_ACTUAL), linewidth=2.0, marker="o", markersize=3, label="Revenue per Unit")
    ax.plot(x, cost_per_unit, color=_mpl(SERIES_FORECAST), linewidth=2.0, marker="o", markersize=3, label="Cost per Unit")
    ax.set_xticks(x)
    ax.set_xticklabels(_month_labels(months), fontsize=8)
    ax.set_ylabel("$ per Unit")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.set_title("Revenue per Unit and Cost per Unit Trend", fontsize=11, fontweight="bold",
                 color=_mpl(NAVY), loc="left")
    ax.legend(frameon=True, facecolor="white", edgecolor="none", framealpha=0.9, loc="upper left", fontsize=8, ncol=2)
    fig.tight_layout()
    return _fig_to_png(fig)


# ---------------------------------------------------------------------
# Workbook 1: Variance Analysis
# ---------------------------------------------------------------------

def _write_metric_card(ws, top_row: int, left_col: int, width: int, label: str,
                        value: float, number_format: str, accent_hex: str) -> int:
    """A compact 3-row KPI card (accent strip, label, big value) — the
    Summary sheet's simpler sibling to the KPI Dashboard's card (no
    target/RAG/trend needed here). Returns the last row used."""
    right_col = left_col + width - 1

    ws.merge_cells(start_row=top_row, start_column=left_col, end_row=top_row, end_column=right_col)
    ws.cell(row=top_row, column=left_col).fill = PatternFill("solid", fgColor=_argb(accent_hex))
    ws.row_dimensions[top_row].height = 5

    label_row = top_row + 1
    ws.merge_cells(start_row=label_row, start_column=left_col, end_row=label_row, end_column=right_col)
    lc = ws.cell(row=label_row, column=left_col, value=label)
    lc.font = Font(name="Calibri", bold=True, size=9, color=_argb(INK_SECONDARY))
    lc.alignment = Alignment(horizontal="center")

    value_row = label_row + 1
    ws.merge_cells(start_row=value_row, start_column=left_col, end_row=value_row, end_column=right_col)
    vc = ws.cell(row=value_row, column=left_col, value=value)
    vc.number_format = number_format
    vc.font = Font(name="Calibri", bold=True, size=20, color=_argb(NAVY))
    vc.alignment = Alignment(horizontal="center")
    ws.row_dimensions[value_row].height = 28

    return value_row


def build_variance_workbook(var_df: pd.DataFrame, month: str, out_path) -> None:
    """Three sheets: Summary (KPI cards + management narrative), Variance
    Detail (full 12-month supporting schedule), Waterfall (chart +
    reconciliation control). `month` drives every period label on every
    sheet — nothing here hard-codes a specific reporting period."""
    wb = Workbook()
    _register_named_styles(wb)

    _build_variance_summary_sheet(wb.active, var_df, month)
    wb.active.title = "Summary"

    detail_ws = wb.create_sheet("Variance Detail")
    _build_variance_detail_sheet(detail_ws, var_df)

    waterfall_ws = wb.create_sheet("Waterfall")
    _build_waterfall_sheet(waterfall_ws, var_df, month)

    wb.save(out_path)


def _build_variance_summary_sheet(ws, var_df, month):
    ws.sheet_view.showGridLines = False
    summary = variance_mod.narrative(var_df, month, n=3)
    month_lbl = variance_mod.month_label(month)

    ws.cell(row=1, column=1, value=COMPANY_SHORT_NAME).font = \
        Font(name="Calibri", bold=True, size=11, color=_argb(INK_SECONDARY))
    ws.cell(row=2, column=1, value=f"{month_lbl} Variance Analysis").font = TITLE_FONT
    ws.cell(row=3, column=1, value="Fictional company | Synthetic data").font = NOTE_FONT
    ws.cell(row=4, column=1, value="USD (rounded to nearest $K)").font = NOTE_FONT
    row = 6

    budget_accent = STATUS_GOOD if summary["oi_variance"] >= 0 else STATUS_CRITICAL
    forecast_accent = STATUS_GOOD if summary["oi_variance_forecast"] >= 0 else STATUS_CRITICAL
    card_specs = [
        ("Actual Operating Income", summary["actual_oi"], NAVY),
        ("Budget Operating Income", summary["budget_oi"], NAVY),
        ("Variance to Budget", summary["oi_variance"], budget_accent),
        ("Variance to Forecast", summary["oi_variance_forecast"], forecast_accent),
    ]
    last_card_col = 2
    left_col = 2
    last_card_row = row
    for label, value, accent in card_specs:
        last_card_row = _write_metric_card(ws, row, left_col, 3, label, value, CURRENCY_000_FMT, accent)
        last_card_col = left_col + 2
        left_col += 4
    row = last_card_row + 2
    summary_end_col = last_card_col

    ws.cell(row=row, column=1, value="Management Summary").font = SECTION_FONT
    row += 1
    ws.cell(row=row, column=1, value=summary["management_summary"]).font = BODY_FONT
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=summary_end_col)
    ws.row_dimensions[row].height = 30
    row += 2

    for section, key, color in [("Favorable Drivers", "favorable", STATUS_GOOD),
                                 ("Unfavorable Drivers", "unfavorable", STATUS_CRITICAL)]:
        if not summary[key]:
            continue
        ws.cell(row=row, column=1, value=section).font = SECTION_FONT
        row += 1
        for sentence in summary[key]:
            bullet = ws.cell(row=row, column=1, value=f"●  {sentence}")
            bullet.font = Font(name="Calibri", size=10, color=_argb(color))
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=summary_end_col)
            row += 1
        row += 1

    row = _write_note(
        ws, row,
        "Variance $ = Actual − Comparison. Favorable/unfavorable reflects economic impact, not raw "
        "sign (e.g. lower expenses are favorable). Only material items (≥ 5% or ≥ $10K) are cited above.",
        span_cols=summary_end_col,
    )

    _set_column_widths(ws, {
        1: 20, 2: 13, 3: 13, 4: 13, 5: 4, 6: 13, 7: 13, 8: 13,
        9: 4, 10: 13, 11: 13, 12: 13, 13: 4, 14: 13, 15: 13, 16: 13,
    })
    _print_setup(ws, f"{month_lbl} Variance Analysis")


# (key, header, kind, comparison-group). kind: "dollar" | "pct" | "material" |
# None (raw text). comparison-group ties a variance/material cell back to the
# favorable_variance_vs_*/flag_vs_* columns that determine its color — only
# set for cells that are actually part of a Budget or Forecast comparison.
_DETAIL_COLUMNS = [
    ("month", "Month", None, None),
    ("line_item", "Line Item", None, None),
    ("actual", "Actual", "dollar", None),
    ("budget", "Budget", "dollar", None),
    ("variance_vs_budget", "$ Var vs Budget", "dollar", "budget"),
    ("variance_pct_vs_budget", "% Var vs Budget", "pct", "budget"),
    ("flag_vs_budget", "Material?", "material", "budget"),
    ("forecast", "Forecast", "dollar", None),
    ("variance_vs_forecast", "$ Var vs Fcst", "dollar", "forecast"),
    ("variance_pct_vs_forecast", "% Var vs Fcst", "pct", "forecast"),
    ("flag_vs_forecast", "Material?", "material", "forecast"),
]


_DETAIL_COLUMN_WIDTHS = {1: 11, 2: 22, 3: 13, 4: 13, 5: 16, 6: 15, 7: 11, 8: 13, 9: 15, 10: 14, 11: 11}


def _build_variance_detail_sheet(ws, var_df):
    ws.sheet_view.showGridLines = False
    note_text = (
        "Variance $ = Actual − Comparison. Green/red reflects impact on Operating Income: "
        "higher revenue or profit is favorable; lower expense is favorable. N/M applies when the "
        "comparison base is immaterial or Operating Income changes sign. Amounts in full USD."
    )
    note_row = _write_note(ws, 1, note_text, span_cols=11)
    # Explicit row height (not Excel's auto-fit) so the note reliably
    # displays as two clean lines at normal zoom, regardless of viewer.
    ws.row_dimensions[1].height = _wrapped_row_height(
        {1: note_text}, {1: sum(_DETAIL_COLUMN_WIDTHS.values())}, min_height=28.0,
    )

    group_row = note_row
    header_row = group_row + 1
    _write_group_header(ws, group_row, [
        ("", 1, 4), ("ACTUAL vs BUDGET", 5, 7), ("", 8, 8), ("ACTUAL vs FORECAST", 9, 11),
    ])
    _write_table_header(ws, header_row, [label for _, label, _, _ in _DETAIL_COLUMNS])

    ordered = var_df.sort_values(["month", "line_item"]).reset_index(drop=True)
    for r, (_, data_row) in enumerate(ordered.iterrows(), start=header_row + 1):
        for c, (key, _, kind, compare) in enumerate(_DETAIL_COLUMNS, start=1):
            value = data_row[key]

            if kind == "material":
                is_material = bool(value)
                cell = ws.cell(row=r, column=c, value=("Yes" if is_material else "—"))
                cell.alignment = Alignment(horizontal="center")
                if is_material:
                    is_favorable = data_row[f"favorable_variance_vs_{compare}"] > 0
                    fill_hex, font_hex = (FILL_GREEN, FONT_GREEN) if is_favorable else (FILL_RED, FONT_RED)
                    cell.fill = PatternFill("solid", fgColor=_argb(fill_hex))
                    cell.font = Font(name="Calibri", bold=True, size=10, color=_argb(font_hex))
                else:
                    cell.font = NM_FONT
                continue

            if kind == "pct" and pd.isna(value):
                cell = ws.cell(row=r, column=c, value="N/M")
                cell.font = NM_FONT
                cell.alignment = Alignment(horizontal="center")
                continue

            cell = ws.cell(row=r, column=c, value=value)
            cell.font = BODY_FONT
            if kind == "dollar":
                cell.number_format = DETAIL_DOLLAR_FMT
            elif kind == "pct":
                cell.number_format = DETAIL_PCT_FMT

            # Tint the variance $/% cells themselves: green if this
            # comparison is material AND favorable, red if material and
            # unfavorable, untouched (neutral) if immaterial. Computed
            # directly from variance.py's own columns — not re-derived.
            if compare and key.startswith("variance"):
                if bool(data_row[f"flag_vs_{compare}"]):
                    is_favorable = data_row[f"favorable_variance_vs_{compare}"] > 0
                    cell.fill = PatternFill("solid", fgColor=_argb(FILL_GREEN if is_favorable else FILL_RED))

    last_row = header_row + len(ordered)
    last_col = len(_DETAIL_COLUMNS)
    ws.auto_filter.ref = f"A{header_row}:{get_column_letter(last_col)}{last_row}"

    _set_column_widths(ws, _DETAIL_COLUMN_WIDTHS)
    _print_setup(ws, "Variance Detail — All Months")

    # Freeze panes LAST, after every other sheet-setup call, as the final
    # word on this sheet's view state — and as a literal "C4", not a
    # computed cell reference, even though header_row is always 3 by
    # construction (note row 1 + group-header row 2 + this header row 3).
    # Freezes rows 1-3 (note/group/column headers) and columns A-B
    # (Month, Line Item) while the data itself scrolls normally in both
    # directions. Must never become data-dependent (e.g. tied to
    # `last_row`) — the frozen region is the sheet's fixed scaffolding,
    # not its variable-length data.
    assert header_row == 3, f"Variance Detail header_row drifted to {header_row}; freeze_panes='C4' assumes row 3"
    ws.freeze_panes = "C4"


def _build_waterfall_sheet(ws, var_df, month):
    ws.sheet_view.showGridLines = False
    month_lbl = variance_mod.month_label(month)
    row = _write_title_block(
        ws, f"{month_lbl} Operating Income Bridge",
        f"{COMPANY_NAME} | USD (rounded to nearest $K)",
    )

    components = variance_mod.waterfall_components(var_df, month)
    month_df = var_df[var_df["month"] == month].set_index("line_item")
    budget_oi = float(month_df.loc["Operating Income", "budget"])
    actual_oi = float(month_df.loc["Operating Income", "actual"])

    # Explicit, compact display size (not the PNG's native ~1800px width) —
    # wide enough that every leaf-level driver's x-axis label (including
    # the two-line "Professional Svcs.") has room to breathe, while still
    # fitting a normal laptop screen without horizontal scrolling.
    chart_width_px, chart_height_px = 1000, 420
    aspect = chart_width_px / chart_height_px
    png = render_waterfall_png(components, budget_oi, actual_oi, month_lbl, figsize=(aspect * 4.2, 4.2))
    img = XLImage(png)
    img.width = chart_width_px
    img.height = chart_height_px
    ws.add_image(img, f"A{row}")
    row += 23  # clear the image before the reconciliation control

    recon = variance_mod.waterfall_reconciliation(var_df, month)
    reconciled = recon["difference"] == 0
    recon_text = ("Bridge Reconciliation: $0  (Reconciled: Yes)" if reconciled else
                  f"Bridge Reconciliation: ${recon['difference']:,.2f}  (Reconciled: No)")
    recon_cell = ws.cell(row=row, column=1, value=recon_text)
    recon_cell.font = Font(name="Calibri", bold=True, size=11,
                            color=_argb(STATUS_GOOD if reconciled else STATUS_CRITICAL))
    row += 2

    # Compact 3-line reconciliation detail — auditable without crowding:
    # the sum of every driver bar should equal the OI variance exactly.
    ws.cell(row=row, column=1, value="Reconciliation Detail").font = SECTION_FONT
    row += 1
    for recon_label, recon_value, is_difference in [
        ("Sum of leaf-level driver impacts", recon["sum_components"], False),
        ("Operating Income variance", recon["oi_variance"], False),
        ("Difference", recon["difference"], True),
    ]:
        ws.cell(row=row, column=1, value=recon_label).font = LABEL_FONT
        cell = ws.cell(row=row, column=2, value=recon_value)
        cell.number_format = CURRENCY2_FMT if is_difference else CURRENCY_000_FMT
        cell.font = Font(name="Calibri", bold=is_difference, size=10,
                          color=_argb(STATUS_GOOD if is_difference else INK_PRIMARY))
        row += 1
    row += 1

    ws.cell(row=row, column=1, value="Bridge Detail").font = SECTION_FONT
    row += 1
    _write_table_header(ws, row, ["Line Item", "Impact on Operating Income"])
    row += 1
    for label, contribution in components:
        ws.cell(row=row, column=1, value=label).font = BODY_FONT
        cell = ws.cell(row=row, column=2, value=contribution)
        cell.number_format = CURRENCY_000_FMT
        cell.font = Font(name="Calibri", size=10,
                          color=_argb(STATUS_GOOD if contribution >= 0 else STATUS_CRITICAL))
        row += 1

    _set_column_widths(ws, {1: 34, 2: 24})
    _print_setup(ws, f"{month_lbl} Operating Income Bridge")


# ---------------------------------------------------------------------
# Workbook 2: KPI Dashboard
# ---------------------------------------------------------------------

CARD_WIDTH = 3   # columns occupied by each KPI card
CARD_GAP = 1     # blank columns between cards

# The dashboard's deliberate vertical layout: a fixed 2x2 chart/table grid
# below the cards, at the exact anchors and approximate cell ranges
# requested (B17/N17/B33/N33). Row 32 is left blank as the grid's own
# vertical spacer between the two grid rows.
GRID_COL_LEFT_START, GRID_COL_LEFT_END = 2, 13     # B:M
GRID_COL_RIGHT_START, GRID_COL_RIGHT_END = 14, 25  # N:Y
GRID_ROW_TOP_START, GRID_ROW_TOP_END = 17, 31
GRID_ROW_BOTTOM_START, GRID_ROW_BOTTOM_END = 33, 47
GRID_ROW_HEIGHT_PT = 22.0


def _trend_display_text(card: dict) -> str:
    """Month-over-month change, finance-notation style: percentage-POINT
    variance for margin/ratio KPIs (e.g. '+2.1 pts F') rather than a
    confusing relative percent-of-a-percent change; relative % change for
    dollar KPIs, where that's the standard convention. 'F'/'U' mirrors the
    RAG lettering — color is not the only signal. Used by the compact KPI
    Detail table (_write_kpi_table); the big dashboard cards use the plainer
    _card_status_label/_card_mom_text pair below instead."""
    t = kpi_mod.trend(card["value"], card["prior"], card["direction"])
    if t["delta"] is None:
        return "no prior month"
    letter = "F" if t["favorable"] else ("U" if t["favorable"] is False else "")
    if card["fmt"] == "pct":
        pts = t["delta"] * 100
        value_text = f"{pts:+.1f} pts"
    else:
        value_text = f"{t['pct_change']:+.1%}"
    return f"{value_text} {letter}".strip()


def _card_status_label(value: float, target: float) -> str:
    """Plain-language position of `value` relative to `target` for a
    management-facing KPI card — deliberately a POSITIONAL description
    ('Above'/'Under'/'On Target'), not a favorability judgment: for a
    lower-is-better KPI (e.g. cost per unit), 'Above Target' is bad, while
    for a higher-is-better KPI it's good. The card's fill/font color (driven
    by RAG, unchanged by this function) is what carries favorability."""
    if target == 0:
        if value == 0:
            return "On Target"
        return "Above Target" if value > 0 else "Under Target"
    relative_diff = (value - target) / abs(target)
    if abs(relative_diff) < 0.005:  # within 0.5% of target reads as "on target"
        return "On Target"
    return "Above Target" if value > target else "Under Target"


def _card_mom_text(card: dict) -> str:
    """Just the month-over-month delta's numeric text (pts for ratio/margin
    KPIs, relative % for dollar KPIs) with no favorability letter — the
    dashboard card's 'Status: ...' phrase already states favorability in
    plain words, so repeating an F/U letter here would be redundant."""
    t = kpi_mod.trend(card["value"], card["prior"], card["direction"])
    if t["delta"] is None:
        return "n/a (no prior month)"
    if card["fmt"] == "pct":
        return f"{t['delta'] * 100:+.1f} pts"
    return f"{t['pct_change']:+.1%}"


def _write_kpi_card(ws, top_row: int, left_col: int, card: dict) -> int:
    """Write one 5-row KPI card (accent strip, label, big value, target,
    RAG+trend). Returns the last row used."""
    right_col = left_col + CARD_WIDTH - 1
    rag = card["rag"]
    accent_hex = RAG_COLOR.get(rag, INK_MUTED)
    fill_hex, font_hex = RAG_FILL_FONT.get(rag, RAG_FILL_FONT["N/A"])

    strip_row = top_row
    ws.merge_cells(start_row=strip_row, start_column=left_col, end_row=strip_row, end_column=right_col)
    ws.cell(row=strip_row, column=left_col).fill = PatternFill("solid", fgColor=_argb(accent_hex))
    ws.row_dimensions[strip_row].height = 5

    label_row = strip_row + 1
    ws.merge_cells(start_row=label_row, start_column=left_col, end_row=label_row, end_column=right_col)
    lc = ws.cell(row=label_row, column=left_col, value=card["label"])
    lc.font = Font(name="Calibri", bold=True, size=9, color=_argb(INK_SECONDARY))
    lc.alignment = Alignment(horizontal="center")

    value_row = label_row + 1
    ws.merge_cells(start_row=value_row, start_column=left_col, end_row=value_row, end_column=right_col)
    vc = ws.cell(row=value_row, column=left_col, value=card["value"])
    vc.number_format = CURRENCY_000_FMT if card["fmt"] == "currency" else PCT_FMT
    vc.font = Font(name="Calibri", bold=True, size=18, color=_argb(NAVY))
    vc.alignment = Alignment(horizontal="center")
    ws.row_dimensions[value_row].height = 24

    target_row = value_row + 1
    ws.merge_cells(start_row=target_row, start_column=left_col, end_row=target_row, end_column=right_col)
    # "vs. Budget" only when the target IS that month's budget figure;
    # every ratio/margin KPI's target is a configured threshold, not a
    # budget line, so it reads "vs. KPI Target" to avoid implying otherwise.
    target_phrase = "Budget" if card.get("target_kind") == "budget" else "KPI Target"
    tc = ws.cell(row=target_row, column=left_col,
                 value=f"vs. {target_phrase} {_format_value(card['target'], card['fmt'])}")
    tc.font = Font(name="Calibri", size=8, color=_argb(INK_MUTED))
    tc.alignment = Alignment(horizontal="center")

    # Plain management-facing status/trend line, e.g.:
    #   "Status: Under Target
    #    MoM: +8.3%"
    # An explicit \n (not Excel's automatic word-wrap) forces the break at
    # exactly this point, so it never wraps mid-word or clips at 100% zoom
    # regardless of card width. Font color still comes from RAG (font_hex),
    # so favorable/unfavorable color logic is unchanged.
    trend_row = target_row + 1
    ws.merge_cells(start_row=trend_row, start_column=left_col, end_row=trend_row, end_column=right_col)
    status_label = _card_status_label(card["value"], card["target"])
    mom_text = _card_mom_text(card)
    rc = ws.cell(row=trend_row, column=left_col, value=f"Status: {status_label}\nMoM: {mom_text}")
    rc.font = Font(name="Calibri", bold=True, size=9, color=_argb(font_hex))
    rc.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[trend_row].height = 28

    return trend_row


def _write_management_insights(ws, row: int, insights: dict) -> int:
    ws.cell(row=row, column=1, value="Management Insights").font = SECTION_FONT
    row += 1
    lines = [
        ("Top Favorable Driver", insights["top_favorable"], STATUS_GOOD),
        ("Top Unfavorable Driver", insights["top_unfavorable"], STATUS_CRITICAL),
        ("Risk & Action", insights["risk_action"], NAVY),
    ]
    label_font = Font(name="Calibri", bold=True, size=11, color=_argb(NAVY))
    # Label merged across A:D, not just column A (width 3, ~26px) — the
    # longest label, "Top Unfavorable Driver:", needs ~165px at 11pt bold
    # and was being truncated to "Top" because the adjacent narrative cell
    # (non-empty) blocks Excel's normal text-overflow-into-empty-neighbor
    # behavior. Narrative now starts one column later (E) to make room;
    # still spans nearly the full grid width.
    label_end_col = 4
    narrative_start_col = label_end_col + 1
    for label, text, color in lines:
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=label_end_col)
        lc = ws.cell(row=row, column=1, value=f"{label}:")
        lc.font = label_font
        lc.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
        ws.merge_cells(start_row=row, start_column=narrative_start_col, end_row=row, end_column=GRID_COL_RIGHT_END)
        c = ws.cell(row=row, column=narrative_start_col, value=text)
        c.font = Font(name="Calibri", size=11, color=_argb(color))
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[row].height = 32
        row += 1
    return row


def _write_kpi_table(ws, start_row: int, start_col: int, cards: list) -> int:
    """Compact KPI detail table anchored at (start_row, start_col) — does
    NOT touch ws.freeze_panes; the dashboard sets one modest freeze for
    the whole sheet, not per-section."""
    headers = ["KPI", "Actual", "Target / Budget", "Variance", "Trend (MoM)", "RAG"]
    _write_table_header(ws, start_row, headers, start_col=start_col)
    row = start_row + 1
    for card in cards:
        fmt = CURRENCY_000_FMT if card["fmt"] == "currency" else PCT_FMT
        variance_fmt = CURRENCY_000_FMT if card["fmt"] == "currency" else PCT_SIGNED_FMT

        ws.cell(row=row, column=start_col, value=card["label"]).font = LABEL_FONT

        actual_cell = ws.cell(row=row, column=start_col + 1, value=card["value"])
        actual_cell.number_format = fmt
        actual_cell.font = BODY_FONT

        target_cell = ws.cell(row=row, column=start_col + 2, value=card["target"])
        target_cell.number_format = fmt
        target_cell.font = BODY_FONT

        variance_cell = ws.cell(row=row, column=start_col + 3, value=card["value"] - card["target"])
        variance_cell.number_format = variance_fmt
        variance_cell.font = BODY_FONT

        ws.cell(row=row, column=start_col + 4, value=_trend_display_text(card)).font = BODY_FONT

        rag = card["rag"]
        fill_hex, font_hex = RAG_FILL_FONT.get(rag, RAG_FILL_FONT["N/A"])
        # Plain positional text instead of the coded F/U letter — reuses the
        # same direction-agnostic value-vs-target comparison as the Dashboard
        # cards (_card_status_label), not a RAG->text lookup, since RAG color
        # alone doesn't say which side of target a lower-is-better KPI (e.g.
        # Total Cost per Unit) is on. Green/Red fill and underlying RAG
        # status logic are both unchanged.
        rag_text = _card_status_label(card["value"], card["target"]) if rag != "N/A" else "N/A"
        rag_cell = ws.cell(row=row, column=start_col + 5, value=rag_text)
        rag_cell.fill = PatternFill("solid", fgColor=_argb(fill_hex))
        rag_cell.font = Font(name="Calibri", bold=True, size=10, color=_argb(font_hex))
        rag_cell.alignment = Alignment(horizontal="center")

        row += 1
    return row


def build_kpi_workbook(kpi_inputs, month: str, out_path) -> None:
    """One sheet, a deliberate top-to-bottom vertical layout:
        rows 1-4   title / reporting period & display units (frozen)
        rows 5-9   6 executive KPI cards
        rows 11-14 management insights (top favorable/unfavorable driver, risk & action)
        rows 17-31 Chart 1 (B17, Revenue trend) | Chart 2 (N17, Margin trend)
        rows 33-47 Chart 3 (B33, Unit-economics trend) | KPI detail table (N33)
    Every chart is embedded at an explicit pixel size computed from this
    sheet's own column widths/row heights (never the PNG's native size),
    so the 2x2 grid cannot overlap. Only a modest "A5" freeze is set —
    the sheet scrolls normally past that point."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Dashboard"
    ws.sheet_view.showGridLines = False
    ws.sheet_view.view = "normal"
    wb.views = [BookView(showHorizontalScroll=True, showVerticalScroll=True, showSheetTabs=True, activeTab=0)]
    _register_named_styles(wb)

    # Column widths / row heights for the whole grid are set FIRST — every
    # pixel-box and figsize computation below depends on these being final.
    # Range stops at the grid's actual right edge (Y) — no styled-but-unused
    # trailing column — and everything (title, cards, insights, charts)
    # shares that same B:Y left/right edge for a consistent dashboard width.
    for c in range(1, GRID_COL_RIGHT_END + 1):
        ws.column_dimensions[get_column_letter(c)].width = 9
    ws.column_dimensions["A"].width = 3  # slim left margin
    for r in list(range(GRID_ROW_TOP_START, GRID_ROW_TOP_END + 1)) + \
             list(range(GRID_ROW_BOTTOM_START, GRID_ROW_BOTTOM_END + 1)):
        ws.row_dimensions[r].height = GRID_ROW_HEIGHT_PT

    var_df = variance_mod.compute_variance(kpi_inputs.pnl)
    cards = kpi_mod.compute_executive_kpis(kpi_inputs, month)
    insights = kpi_mod.management_insights(var_df, cards, month)

    # --- Top section: title (rows 1-2), section label (row 4), 6 cards (rows 5-9) ---
    # Title/labels start at column B — the same left edge as the cards and
    # the chart grid below, rather than sitting alone in the slim margin column.
    _write_title_block(
        ws, "Close Acceleration Pack | Executive KPI Dashboard",
        f"{COMPANY_NAME} | Reporting Period: {month} | Display units: $000s on cards/table, "
        f"whole USD on the per-unit chart",
        start_col=GRID_COL_LEFT_START,
    )
    ws.cell(row=4, column=GRID_COL_LEFT_START, value="Executive KPIs").font = SECTION_FONT

    card_row_start = 5
    left_col = GRID_COL_LEFT_START
    for card in cards:
        last_card_row = _write_kpi_card(ws, card_row_start, left_col, card)
        left_col += CARD_WIDTH + CARD_GAP

    # --- Management insights (rows 11-14) ---
    _write_management_insights(ws, 11, insights)

    # A single, modest freeze — keeps the title in view while scrolling,
    # without pinning the cards, insights, charts, or table.
    ws.freeze_panes = "A5"

    # --- Lower section: 2x2 chart/table grid at the exact requested anchors ---
    pnl = kpi_inputs.pnl
    w_actual = pnl.pivot(index="month", columns="line_item", values="actual")
    w_budget = pnl.pivot(index="month", columns="line_item", values="budget")
    w_forecast = pnl.pivot(index="month", columns="line_item", values="forecast")
    months = list(w_actual.index)

    top_left_box = _range_pixel_box(ws, GRID_COL_LEFT_START, GRID_COL_LEFT_END,
                                     GRID_ROW_TOP_START, GRID_ROW_TOP_END)
    top_right_box = _range_pixel_box(ws, GRID_COL_RIGHT_START, GRID_COL_RIGHT_END,
                                      GRID_ROW_TOP_START, GRID_ROW_TOP_END)
    bottom_left_box = _range_pixel_box(ws, GRID_COL_LEFT_START, GRID_COL_LEFT_END,
                                        GRID_ROW_BOTTOM_START, GRID_ROW_BOTTOM_END)

    # Chart 1 — Revenue Actual vs Budget vs Forecast — anchor B17
    revenue_png = render_revenue_trend_png(
        months, w_actual["Revenue"].tolist(), w_budget["Revenue"].tolist(), w_forecast["Revenue"].tolist(),
        figsize=_figsize_for_box(*top_left_box),
    )
    _embed_chart(ws, revenue_png, "B17", GRID_COL_LEFT_START, GRID_COL_LEFT_END,
                 GRID_ROW_TOP_START, GRID_ROW_TOP_END)

    # Chart 2 — Gross Margin % and Operating Margin % — anchor N17
    gross_margin = kpi_mod.gross_margin_pct(kpi_inputs)
    operating_margin = kpi_mod.operating_margin_pct(kpi_inputs)
    margin_png = render_margin_trend_png(
        months, gross_margin.tolist(), operating_margin.tolist(), figsize=_figsize_for_box(*top_right_box),
    )
    _embed_chart(ws, margin_png, "N17", GRID_COL_RIGHT_START, GRID_COL_RIGHT_END,
                 GRID_ROW_TOP_START, GRID_ROW_TOP_END)

    # Chart 3 — Revenue per Unit and Cost per Unit — anchor B33
    rev_per_unit = kpi_mod.revenue_per_unit(kpi_inputs)
    cost_per_unit = kpi_mod.total_cost_per_unit(kpi_inputs)
    unit_png = render_unit_economics_png(
        months, rev_per_unit.tolist(), cost_per_unit.tolist(), figsize=_figsize_for_box(*bottom_left_box),
    )
    _embed_chart(ws, unit_png, "B33", GRID_COL_LEFT_START, GRID_COL_LEFT_END,
                 GRID_ROW_BOTTOM_START, GRID_ROW_BOTTOM_END)

    # The KPI detail table lives on its own "KPI Detail" tab, not crammed
    # into the 4th grid quadrant next to a chart — a real cell-data table
    # sharing tight row heights with an image looked cramped, so it gets
    # its own sheet and the Dashboard leaves a pointer in its place.
    note_row = GRID_ROW_BOTTOM_START
    ws.cell(row=note_row, column=GRID_COL_RIGHT_START, value="KPI Detail").font = SECTION_FONT
    ws.cell(row=note_row + 1, column=GRID_COL_RIGHT_START,
            value="Full actual / target / variance / trend / RAG table: see the "
                  "\"KPI Detail\" tab.").font = NOTE_FONT

    _build_kpi_detail_sheet(wb.create_sheet("KPI Detail"), cards, month)

    _print_setup(ws, "KPI Dashboard")
    wb.save(out_path)


def _build_kpi_detail_sheet(ws, cards: list, month: str) -> None:
    ws.sheet_view.showGridLines = False
    row = _write_title_block(ws, "KPI Detail", f"{COMPANY_NAME} | Reporting Period: {month}")
    _write_kpi_table(ws, row, 1, cards)
    ws.freeze_panes = ws.cell(row=row + 1, column=1)
    # Column 6 (RAG) widened from 8 to 16 — it used to hold a 1-char code
    # (F/U/W); now it holds "Above Target"/"Under Target" (~13 chars).
    _set_column_widths(ws, {1: 26, 2: 14, 3: 16, 4: 14, 5: 14, 6: 16})
    _print_setup(ws, "KPI Detail")


# ---------------------------------------------------------------------
# Workbook 3: Close Calendar + Controls Log
# ---------------------------------------------------------------------

def build_close_workbook(calendar_df: pd.DataFrame, controls_df: pd.DataFrame, out_path) -> None:
    wb = Workbook()
    _build_close_calendar_sheet(wb.active, calendar_df, controls_df)
    wb.active.title = "Close Calendar"

    controls_ws = wb.create_sheet("Controls Log")
    _build_controls_log_sheet(controls_ws, controls_df)

    wb.save(out_path)


def _write_summary_box(ws, row: int, metrics: list) -> int:
    """A compact row of label/value pairs — tasks complete/total, open
    tasks, controls effective/exception — at the top of the calendar."""
    col = 1
    for label, value in metrics:
        ws.cell(row=row, column=col, value=label).font = Font(name="Calibri", size=9, color=_argb(INK_SECONDARY))
        vcell = ws.cell(row=row + 1, column=col, value=value)
        vcell.font = Font(name="Calibri", bold=True, size=14, color=_argb(NAVY))
        col += 2
    return row + 3


def _build_close_calendar_sheet(ws, calendar_df, controls_df):
    ws.sheet_view.showGridLines = False
    row = _write_title_block(ws, "Month-End Close Calendar (Day 1-5)", COMPANY_NAME)

    cal_summary = controls_mod.close_calendar_summary()
    ctrl_summary = controls_mod.controls_summary(controls_df)

    # Populated from the calendar's own state (controls.current_close_day),
    # never a fixed literal — "as of" tracks wherever the scenario actually is.
    status_cell = ws.cell(row=row, column=1, value=f"Close status as of: Day {cal_summary['current_close_day']}")
    status_cell.font = Font(name="Calibri", bold=True, size=12, color=_argb(NAVY))
    row += 2

    row = _write_summary_box(ws, row, [
        ("Tasks Complete / Total", f"{cal_summary['tasks_complete']} / {cal_summary['tasks_total']}"),
        ("Open Tasks", cal_summary["tasks_open"]),
        ("Controls Effective", f"{ctrl_summary['controls_effective']} / {ctrl_summary['controls_total']}"),
        ("Controls with Exceptions", ctrl_summary["controls_exception"]),
    ])
    row += 1

    header_row = row
    headers = ["Day", "Task", "Owner", "Reviewer / Approver", "Dependency",
               "Evidence / Deliverable", "Status", "Exception Notes"]
    _write_table_header(ws, header_row, headers)
    row += 1

    col_widths = {1: 7, 2: 40, 3: 16, 4: 16, 5: 30, 6: 30, 7: 12, 8: 36}
    keys = ["day", "task", "owner", "reviewer", "dependency", "evidence_ref", "status", "exception_notes"]
    for _, task_row in calendar_df.iterrows():
        fill_hex, font_hex = TASK_STATUS_FILL_FONT.get(task_row["status"], (None, None))
        for c, key in enumerate(keys, start=1):
            cell = ws.cell(row=row, column=c, value=task_row[key])
            cell.alignment = Alignment(wrap_text=True, vertical="center")
            if key == "status" and fill_hex:
                cell.fill = PatternFill("solid", fgColor=_argb(fill_hex))
                cell.font = Font(name="Calibri", bold=True, size=10, color=_argb(font_hex))
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.font = BODY_FONT
        row_texts = {c: task_row[key] for c, key in enumerate(keys, start=1)}
        ws.row_dimensions[row].height = _wrapped_row_height(row_texts, col_widths)
        row += 1

    last_row = row - 1
    ws.auto_filter.ref = f"A{header_row}:{get_column_letter(len(headers))}{last_row}"
    _set_column_widths(ws, col_widths)
    _print_setup(ws, "Month-End Close Calendar")

    # Freeze panes LAST, as an explicit literal "A11" — not a computed
    # cell reference — so the title, close-status line, KPI summary box,
    # AND the column-header row (all rows 1-10) stay visible while
    # scrolling, and no task row is ever frozen. header_row is
    # structurally fixed at 10 (title block 3 rows + status line 2 rows +
    # summary box 4 rows + 1 blank = 10); the assert is a tripwire if that
    # layout ever changes without updating the freeze target.
    assert header_row == 10, f"Close Calendar header_row drifted to {header_row}; freeze_panes='A11' assumes row 10"
    ws.freeze_panes = "A11"


def _build_controls_log_sheet(ws, controls_df):
    ws.sheet_view.showGridLines = False
    row = _write_title_block(
        ws, "Controls Log",
        f"{COMPANY_NAME} | Completeness / Accuracy / Authorization — "
        f"informed by document-validation, evidence-retention, and exception-management principles",
    )
    row = _write_note(
        ws, row,
        "This log demonstrates internal-controls awareness applied to a hypothetical company. "
        "It is not a claim of SOX compliance, audit-readiness, or enterprise-grade coverage.",
        span_cols=11,
    )
    header_row = row
    headers = ["Control ID", "Category", "Process Area", "Risk", "Control Activity", "Owner",
               "Reviewer / Approver", "Frequency", "Evidence Retained", "Status", "Exception / Remediation"]
    _write_table_header(ws, header_row, headers)
    row += 1

    col_widths = {1: 11, 2: 15, 3: 22, 4: 34, 5: 34, 6: 16, 7: 16, 8: 16, 9: 26, 10: 11, 11: 40}
    keys = ["control_id", "category", "process_area", "risk", "control_activity", "owner",
            "reviewer", "frequency", "evidence_ref", "status", "exception_remediation"]
    for _, control_row in controls_df.iterrows():
        fill_hex, font_hex = CONTROL_STATUS_FILL_FONT.get(control_row["status"], (None, None))
        for c, key in enumerate(keys, start=1):
            cell = ws.cell(row=row, column=c, value=control_row[key])
            cell.alignment = Alignment(wrap_text=True, vertical="center")
            if key == "status" and fill_hex:
                cell.fill = PatternFill("solid", fgColor=_argb(fill_hex))
                cell.font = Font(name="Calibri", bold=True, size=10, color=_argb(font_hex))
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.font = BODY_FONT
        row_texts = {c: control_row[key] for c, key in enumerate(keys, start=1)}
        ws.row_dimensions[row].height = _wrapped_row_height(row_texts, col_widths)
        row += 1

    last_row = row - 1
    ws.auto_filter.ref = f"A{header_row}:{get_column_letter(len(headers))}{last_row}"
    _set_column_widths(ws, col_widths)
    _print_setup(ws, "Controls Log")

    # Freeze panes LAST, as an explicit literal "A6" — the title/context
    # note (rows 1-4) plus the column-header row (row 5) stay visible
    # while scrolling; row 6 (the first control record, COMP-01) is NOT
    # frozen. header_row is structurally fixed at 5 (title block 3 rows +
    # note 1 row + 1 = 5); the assert is a tripwire if that layout changes.
    assert header_row == 5, f"Controls Log header_row drifted to {header_row}; freeze_panes='A6' assumes row 5"
    ws.freeze_panes = "A6"
