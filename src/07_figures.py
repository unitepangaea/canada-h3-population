"""07: Phase G figures (protocol Section 9).

Every map is drawn in EPSG:3347 (NAD83 / Statistics Canada Lambert, Lambert Conformal Conic), as Paul
requested at the start of Phase G. Hexagon vertices come from h3.cell_to_boundary and are projected
vertex by vertex; at r <= 6 an edge is <= 3.7 km, so straight edges in EPSG:3347 are adequate.

Colour (dataviz skill; checked with scripts/validate_palette.js):
  - Density maps: one 10-step single-hue blue ramp (OKLab interpolation through the reference blue
    steps 100, 400, 700). Monotone lightness, adjacent dL >= 0.06, hue spread 4 deg. The same
    half-decade log classes are used at every resolution and in every map:
    < 1, 1-3, 3-10, ..., 3,000-10,000, >= 10,000 people per km2.
    Unpopulated land is a neutral grey so the lightest class does not read as "no population".
  - Method pairs: categorical slots 1-3 (blue, orange, aqua), which pass the all-pairs CVD check.
  - Agreement categories: ordinal blue ramp (steps 250/400/550/700, validated with --ordinal),
    plus orange and aqua for cells populated in one layer only.

Outputs (300 dpi PNG plus PDF) in Papers/hexagonPops/figures_v2/:
  fig1a_relative_categories   relative agreement categories by r, three pairs (F2_categories_relative.csv)
  fig1b_bland_altman          Bland-Altman, PHH vs NAR, r = 6, 7, 8, M on a log axis (layers; F1_core_metrics.csv)
  figA_displacement_by_res    D/P by r, forced agreement by r, D8 decomposition (F1, F3, F4)
  fig2_toronto_3x3            Toronto, rows r = 8, 7, 6, columns PHH, NAR, HYB
  fig3_national_hyb_r6        national hybrid density, r = 6
  figS1_national_hyb_r8       national hybrid density, r = 8 (supplement)
  figB_urban_rural            Ottawa-Gatineau and a rural Saskatchewan window, hybrid, r = 6, 7, 8
  figure_sources.csv          figure -> source files
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import h3
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import geopandas as gpd  # noqa: E402
import shapely  # noqa: E402
import shapely.ops  # noqa: E402
from matplotlib.cm import ScalarMappable  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap, ListedColormap  # noqa: E402
from matplotlib import patheffects  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch, Rectangle  # noqa: E402
from pyproj import Transformer  # noqa: E402
from shapely.geometry import box  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
from hexpop.io import Log  # noqa: E402

# ----------------------------------------------------------------------------
# Style
# ----------------------------------------------------------------------------
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8f8e88"
GRID, SURFACE, LAND, BORDER = "#e4e3df", "#ffffff", "#ebeae6", "#9a9993"
PAIR_COLOURS = {"PHH vs NAR": "#2a78d6", "HYB vs PHH": "#eb6834", "HYB vs NAR": "#1baf7a"}
PAIR_XY = {"PHH vs NAR": ("PHH", "NAR"), "HYB vs PHH": ("PHH", "HYB"), "HYB vs NAR": ("NAR", "HYB")}

DENS_BREAKS = [1, 3, 10, 30, 100, 300, 1_000, 3_000, 10_000]          # people per km2
DENS_COLOURS = ["#cde2fb", "#adcef7", "#8dbaf3", "#6da6ee", "#4c92e8",
                "#347dd7", "#2a6bbb", "#20599f", "#164785", "#0d366b"]
CAT_ORDER = ["match", "minor", "moderate", "major", "x-only", "y-only"]
CAT_LABELS = {"match": "Match (R < 0.05)", "minor": "Minor (0.05 to < 0.25)", "moderate": "Moderate (0.25 to < 0.50)",
              "major": "Major (R ≥ 0.50)", "x-only": "Populated in x only", "y-only": "Populated in y only"}
CAT_COLOURS = {"match": "#86b6ef", "minor": "#3987e5", "moderate": "#1c5cab", "major": "#0d366b",
               "x-only": "#eb6834", "y-only": "#1baf7a"}
DECOMP_COLOURS = ["#86b6ef", "#2a78d6", "#104281"]
METHOD_TITLES = {"phh": "PHH (road network points)", "nar": "NAR (address locations)", "hyb": "Hybrid (τ = 50)"}

FULL_W = 7.48          # 190 mm, double-column width
TO_MAP = Transformer.from_crs("EPSG:4326", C.MAP_CRS, always_xy=True)
TO_GEO = Transformer.from_crs(C.MAP_CRS, "EPSG:4326", always_xy=True)

TORONTO = {8: "882b9bc711fffff", 7: "872b9bc71ffffff", 6: "862b9bc77ffffff"}
WINDOWS = {   # name: (centre lat, centre lon, width km, height km)
    "Ottawa–Gatineau": (45.40, -75.72, 60, 44),
    "Rural Saskatchewan (Humboldt area)": (52.05, -105.10, 60, 44),
}

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.spines.top": False, "axes.spines.right": False,
    "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.dpi": 300, "figure.dpi": 100,
})

SOURCES: list[dict] = []


def area_km2(r: int) -> float:
    return h3.average_hexagon_area(r, unit="km^2")


def res_label(r: int, sep: str = " ") -> str:
    return f"r = {r}{sep}({area_km2(r):.2f} km²)" if r == 8 else f"r = {r}{sep}({area_km2(r):.1f} km²)"


def save(fig, name: str, sources: list, log: Log) -> None:
    C.FIGURES_V2.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(C.FIGURES_V2 / f"{name}.{ext}", dpi=300, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    for s in sources:
        SOURCES.append({"figure": name, "source": C.rel(s)})
    log(f"wrote {name}.png/.pdf")


def panel_label(ax, s: str, x: float = -0.02, y: float = 1.02) -> None:
    ax.text(x, y, s, transform=ax.transAxes, fontsize=9, fontweight="bold", ha="right", va="bottom")


# ----------------------------------------------------------------------------
# Map helpers
# ----------------------------------------------------------------------------
def layer_path(layer: str, r: int, tag: str = "v2") -> Path:
    return C.OUTPUT_V2 / tag / f"res{r}" / f"{layer}_h3_res{r}.parquet"


def load_layer(layer: str, r: int, cells: set | None = None, tag: str = "v2") -> pd.DataFrame:
    df = pd.read_parquet(layer_path(layer, r, tag), columns=["h3", "population", "pop_density_km2"])
    return df[df.h3.isin(cells)] if cells is not None else df


def hex_verts(cells) -> list[np.ndarray]:
    bnd = [h3.cell_to_boundary(c) for c in cells]                 # (lat, lng) tuples
    n = np.fromiter((len(b) for b in bnd), dtype=int, count=len(bnd))
    arr = np.concatenate([np.asarray(b) for b in bnd])
    x, y = TO_MAP.transform(arr[:, 1], arr[:, 0])
    return np.split(np.column_stack([x, y]), np.cumsum(n)[:-1])


def density_colours(d: np.ndarray) -> np.ndarray:
    return np.asarray(DENS_COLOURS)[np.digitize(d, DENS_BREAKS)]


def draw_hex(ax, df: pd.DataFrame, gap: bool, rasterized: bool = False) -> None:
    fc = density_colours(df.pop_density_km2.to_numpy())
    if gap:   # zoomed maps: thin surface-coloured gap between cells
        pc = PolyCollection(hex_verts(df.h3), facecolors=fc, edgecolors=SURFACE, linewidths=0.25, zorder=2)
    else:     # national maps: edge = face, so antialiasing leaves no seams
        pc = PolyCollection(hex_verts(df.h3), facecolors=fc, edgecolors=fc, linewidths=0.08, zorder=2)
    pc.set_rasterized(rasterized)
    ax.add_collection(pc)


def provinces() -> gpd.GeoDataFrame:
    return gpd.read_file(C.PROV_GPKG).to_crs(C.MAP_CRS)


def draw_land(ax, prov: gpd.GeoDataFrame, bounds=None) -> None:
    p = prov if bounds is None else gpd.clip(prov, box(*bounds))
    p.plot(ax=ax, facecolor=LAND, edgecolor="none", zorder=0)
    p.boundary.plot(ax=ax, color=BORDER, linewidth=0.4, zorder=3)


def map_axes(ax, bounds) -> None:
    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])
    ax.set_aspect("equal")
    ax.set_axis_off()


def scalebar(ax, km: float, loc=(0.04, 0.05)) -> None:
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    sx, sy = x0 + loc[0] * (x1 - x0), y0 + loc[1] * (y1 - y0)
    ax.plot([sx, sx + km * 1000], [sy, sy], color=INK, lw=1.4, solid_capstyle="butt", zorder=6)
    ax.text(sx + km * 500, sy + 0.012 * (y1 - y0), f"{km:g} km", ha="center", va="bottom", fontsize=6.5, zorder=6,
            path_effects=[patheffects.withStroke(linewidth=2, foreground=SURFACE)])


def density_legend(fig, rect) -> None:
    cax = fig.add_axes(rect)
    sm = ScalarMappable(norm=BoundaryNorm(np.arange(11), 10), cmap=ListedColormap(DENS_COLOURS))
    cb = fig.colorbar(sm, cax=cax, orientation="horizontal", ticks=np.arange(1, 10))
    cb.set_ticklabels([f"{b:,}" for b in DENS_BREAKS])
    cb.outline.set_visible(False)
    cax.tick_params(length=2, labelsize=6.5, colors=INK2)
    cb.set_label("Population density (people per km², half-decade log classes; same classes at every resolution)",
                 fontsize=7, color=INK)
    # 'no population' swatch to the left of the bar
    w = rect[3] * 1.6 * fig.get_figheight() / fig.get_figwidth()
    x = rect[0] - 0.012 - w
    fig.add_artist(Rectangle((x, rect[1]), w, rect[3], transform=fig.transFigure, facecolor=LAND,
                             edgecolor=BORDER, linewidth=0.4))
    fig.text(x + w / 2, rect[1] - 0.006, "No\npopulation", ha="center", va="top", fontsize=6.5, color=INK2)


def window_bounds(lat: float, lon: float, w_km: float, h_km: float) -> tuple:
    x, y = TO_MAP.transform(lon, lat)
    return (x - w_km * 500, y - h_km * 500, x + w_km * 500, y + h_km * 500)


def cells_in_bounds(bounds, r: int) -> set:
    pad = 3 * h3.average_hexagon_edge_length(r, unit="m")
    poly = shapely.segmentize(box(bounds[0] - pad, bounds[1] - pad, bounds[2] + pad, bounds[3] + pad), 1000)
    poly = shapely.transform(poly, lambda xy: np.column_stack(TO_GEO.transform(xy[:, 0], xy[:, 1])))
    return set(h3.geo_to_cells(poly, r))


def outline_cell(ax, cell: str) -> None:
    v = hex_verts([cell])[0]
    v = np.vstack([v, v[:1]])
    ax.plot(v[:, 0], v[:, 1], color=SURFACE, lw=2.4, zorder=4)
    ax.plot(v[:, 0], v[:, 1], color=INK, lw=1.0, zorder=5)


# ----------------------------------------------------------------------------
# Fig. 1a: relative agreement categories
# ----------------------------------------------------------------------------
def fig1a(log: Log) -> None:
    src = C.TABLES / "F2_categories_relative.csv"
    rel = pd.read_csv(src)
    rel = rel[~rel.category.str.startswith("H5")].copy()

    def cat(row):
        if row.category.endswith("-only"):
            return "x-only" if row.category.split("-")[0] == PAIR_XY[row.pair][0] else "y-only"
        return row.category
    rel["cat"] = rel.apply(cat, axis=1)

    fig, axes = plt.subplots(2, 3, figsize=(FULL_W, 3.5), sharex=True, sharey=True)
    metrics = [("pct_of_cells_M5", "Share of cells"), ("pct_of_pop_M5", "Share of population")]
    for i, (col, ylab) in enumerate(metrics):
        for j, pair in enumerate(PAIR_COLOURS):
            ax = axes[i, j]
            for k, r in enumerate(C.RESOLUTIONS):
                d = rel[(rel.pair == pair) & (rel.res == r)].set_index("cat")[col].reindex(CAT_ORDER).fillna(0)
                left = 0.0
                for c, w in d.items():
                    ax.barh(k, w, left=left, height=0.62, color=CAT_COLOURS[c], edgecolor=SURFACE, linewidth=0.8)
                    if w >= 9:
                        dark = c in ("minor", "moderate", "major")
                        ax.text(left + w / 2, k, f"{w:.0f}%", ha="center", va="center", fontsize=6.5,
                                color=SURFACE if dark else INK)
                    left += w
            ax.set_yticks(range(len(C.RESOLUTIONS)), [f"r = {r}" for r in C.RESOLUTIONS])
            ax.invert_yaxis()
            ax.set_xlim(0, 100)
            ax.tick_params(axis="y", length=0)
            ax.spines["left"].set_visible(False)
            if i == 0:
                x, y = PAIR_XY[pair]
                ax.set_title(f"{pair}\n(x = {x}, y = {y})", color=INK)
            if j == 0:
                ax.set_ylabel(ylab)
            if i == 1:
                ax.set_xlabel("Percent")
        panel_label(axes[i, 0], "(a)" if i == 0 else "(b)", x=-0.18)
    handles = [Patch(facecolor=CAT_COLOURS[c], label=CAT_LABELS[c]) for c in CAT_ORDER]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, fontsize=7,
               bbox_to_anchor=(0.5, -0.13), handlelength=1.2, columnspacing=1.4)
    fig.text(0.5, -0.17, "Cells with M ≥ 5 only. R = |y − x| / M, where M is the mean of the two estimates.",
             ha="center", fontsize=6.5, color=INK2)
    fig.tight_layout(h_pad=1.2)
    save(fig, "fig1a_relative_categories", [src], log)


# ----------------------------------------------------------------------------
# Fig. 1b: Bland-Altman, PHH vs NAR, at each r
# ----------------------------------------------------------------------------
def fig1b(log: Log) -> None:
    f1 = pd.read_csv(C.TABLES / "F1_core_metrics.csv")
    cmap = LinearSegmentedColormap.from_list("blue", DENS_COLOURS[1:])
    fig, axes = plt.subplots(1, 3, figsize=(FULL_W, 2.6))
    srcs = [C.TABLES / "F1_core_metrics.csv"]
    hb = None
    for ax, r in zip(axes, C.RESOLUTIONS):
        x = load_layer("phh", r).set_index("h3").population
        y = load_layer("nar", r).set_index("h3").population
        srcs += [layer_path("phh", r), layer_path("nar", r)]
        df = pd.concat({"x": x[x > 0], "y": y[y > 0]}, axis=1).fillna(0.0)
        M = (df.x + df.y) / 2
        dlt = df.y - df.x
        lim = 1.05 * dlt.abs().max()
        hb = ax.hexbin(M, dlt, xscale="log", gridsize=(55, 36), bins="log", mincnt=1, cmap=cmap,
                       extent=(np.log10(M.min()), np.log10(M.max()), -lim, lim), linewidths=0, rasterized=True)
        row = f1[(f1.tag == "v2") & (f1.pair == "PHH vs NAR") & (f1.res == r)].iloc[0]
        ax.axhline(row.ba_bias, color=INK, lw=1.0, zorder=3)
        for v in (row.ba_loa_lower, row.ba_loa_upper):
            ax.axhline(v, color=INK2, lw=1.0, ls=(0, (4, 2)), zorder=3)
        ax.text(0.03, 0.97, f"95% limits of agreement ±{row.ba_loa_upper:,.1f}\n"
                            f"cells = {len(df):,}", transform=ax.transAxes, ha="left", va="top",
                fontsize=6.5, color=INK2)
        ax.set_ylim(-lim, lim)
        ax.set_title(res_label(r), color=INK)
        ax.set_xlabel("M, mean of PHH and NAR (people per cell)")
        ax.grid(axis="y", color=GRID, lw=0.5)
        ax.set_axisbelow(True)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}".replace("-", "−")))
    axes[0].set_ylabel("NAR − PHH (people per cell)")
    fig.tight_layout()
    cax = fig.add_axes([1.005, 0.25, 0.012, 0.6])
    cb = fig.colorbar(hb, cax=cax)
    cb.outline.set_visible(False)
    cb.set_label("Cells per bin (log scale)", fontsize=7)
    cax.tick_params(labelsize=6.5, length=2)
    leg = [Line2D([], [], color=INK, lw=1.0, label="Mean difference (bias)"),
           Line2D([], [], color=INK2, lw=1.0, ls=(0, (4, 2)), label="Bias ± 1.96 SD")]
    fig.legend(handles=leg, loc="lower center", ncol=2, frameon=False, fontsize=7, bbox_to_anchor=(0.5, -0.08))
    save(fig, "fig1b_bland_altman", srcs, log)


# ----------------------------------------------------------------------------
# Fig. new A: displacement against resolution
# ----------------------------------------------------------------------------
def figA(log: Log) -> None:
    f1 = pd.read_csv(C.TABLES / "F1_core_metrics.csv")
    f3 = pd.read_csv(C.TABLES / "F3_forced.csv").set_index("res")
    f4 = pd.read_csv(C.TABLES / "F4_decomposition.csv").set_index("pair")
    fig, axes = plt.subplots(1, 3, figsize=(FULL_W, 3.1), gridspec_kw={"width_ratios": [1, 1, 1.25]})
    fig.subplots_adjust(left=0.075, right=0.985, top=0.93, bottom=0.40, wspace=0.62)
    xt = [res_label(r, "\n") for r in C.RESOLUTIONS]

    ax = axes[0]
    ends = []
    for pair, col in PAIR_COLOURS.items():
        d = f1[(f1.tag == "v2") & (f1.pair == pair)].set_index("res").D_over_P.reindex(C.RESOLUTIONS) * 100
        ax.plot(C.RESOLUTIONS, d, color=col, lw=1.6, marker="o", ms=4.5, mec=SURFACE, mew=0.8, label=pair, zorder=3)
        ends.append(d.iloc[-1])
    cond = f3.D_over_pop_non_forced_pct.reindex(C.RESOLUTIONS)
    ax.plot(C.RESOLUTIONS, cond, color=PAIR_COLOURS["PHH vs NAR"], lw=1.2, ls=(0, (3, 2)), marker="o", ms=3.5,
            mfc=SURFACE, label="PHH vs NAR, DBs without\nforced agreement", zorder=3)
    ends.append(cond.iloc[-1])
    ypos = sorted(ends)
    for k in range(1, len(ypos)):            # end labels at least 10% of the axis apart
        ypos[k] = max(ypos[k], ypos[k - 1] + 0.1 * max(ends))
    for v, yv in zip(sorted(ends), ypos):
        ax.text(8.12, yv, f"{v:.1f}%", va="center", fontsize=6.5, color=INK2)
    ax.set_ylabel("Displaced population, D/P (%)")
    ax.set_ylim(0, None)
    ax.legend(frameon=False, fontsize=6.3, loc="upper center", bbox_to_anchor=(0.5, -0.37), ncol=1,
              handlelength=2.2)
    panel_label(ax, "(a)", x=-0.3, y=1.04)

    ax = axes[1]
    for c, lab, ls in [("pct_pop_forced", "Population", "-"), ("pct_dbs_forced", "Populated DBs", (0, (3, 2)))]:
        d = f3[c].reindex(C.RESOLUTIONS)
        ax.plot(C.RESOLUTIONS, d, color=INK2, lw=1.4, ls=ls, marker="o", ms=4, mfc=SURFACE if ls != "-" else INK2,
                mec=INK2, label=lab, zorder=3)
        other = f3["pct_dbs_forced" if c == "pct_pop_forced" else "pct_pop_forced"].reindex(C.RESOLUTIONS)
        for r, v in d.items():   # the higher of the two values is labelled above, the lower below
            up = v >= other[r]
            ax.text(r, v + (4 if up else -4), f"{v:.0f}%", ha="center", va="bottom" if up else "top",
                    fontsize=6.3, color=INK2)
    ax.set_ylabel("In forced-agreement DBs (%)")
    ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=6.3, loc="upper center", bbox_to_anchor=(0.5, -0.37), ncol=1,
              handlelength=2.2)
    panel_label(ax, "(b)", x=-0.3, y=1.04)
    for a in axes[:2]:
        a.set_xticks(C.RESOLUTIONS, xt)
        a.set_xlim(5.7, 8.5)
        a.grid(axis="y", color=GRID, lw=0.5)
        a.set_axisbelow(True)
        a.set_xlabel("H3 resolution (mean cell area)")

    ax = axes[2]
    cols = ["pct_local_resolves_within_res7_parent", "pct_persists_to_res7_resolves_within_res6",
            "pct_persists_to_res6"]
    labs = ["Offsets within the r = 7 parent", "Offsets within the r = 6 parent", "Persists at r = 6"]
    pairs = list(PAIR_COLOURS)
    for k, pair in enumerate(pairs):
        left = 0.0
        for c, colr in zip(cols, DECOMP_COLOURS):
            w = f4.loc[pair, c]
            ax.barh(k, w, left=left, height=0.6, color=colr, edgecolor=SURFACE, linewidth=0.8)
            ax.text(left + w / 2, k, f"{w:.0f}%", ha="center", va="center", fontsize=6.5,
                    color=INK if colr == DECOMP_COLOURS[0] else SURFACE)
            left += w
    ax.set_yticks(range(len(pairs)), pairs)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("Share of displacement at r = 8, $D_8$ (%)")
    ax.legend(handles=[Patch(facecolor=c, label=l) for c, l in zip(DECOMP_COLOURS, labs)], frameon=False,
              fontsize=6.3, loc="upper center", bbox_to_anchor=(0.35, -0.30), ncol=1, handlelength=1.2)
    panel_label(ax, "(c)", x=-0.3, y=1.04)
    save(fig, "figA_displacement_by_res",
         [C.TABLES / "F1_core_metrics.csv", C.TABLES / "F3_forced.csv", C.TABLES / "F4_decomposition.csv"], log)


# ----------------------------------------------------------------------------
# Fig. 2: Toronto 3 x 3
# ----------------------------------------------------------------------------
def fig2(log: Log, prov: gpd.GeoDataFrame) -> None:
    disk = h3.grid_disk(TORONTO[6], 1)
    pts = np.vstack(hex_verts(disk))
    pad = 500
    b = (pts[:, 0].min() - pad, pts[:, 1].min() - pad, pts[:, 0].max() + pad, pts[:, 1].max() + pad)
    asp = (b[3] - b[1]) / (b[2] - b[0])
    rows = [8, 7, 6]
    fig, axes = plt.subplots(3, 3, figsize=(FULL_W, FULL_W * asp * 1.0 + 0.6))
    srcs = []
    for i, r in enumerate(rows):
        cells = cells_in_bounds(b, r)
        for j, layer in enumerate(["phh", "nar", "hyb"]):
            ax = axes[i, j]
            df = load_layer(layer, r, cells)
            srcs.append(layer_path(layer, r))
            draw_land(ax, prov, b)
            draw_hex(ax, df, gap=True)
            outline_cell(ax, TORONTO[r])
            map_axes(ax, b)
            pop = df.set_index("h3").population.get(TORONTO[r], 0.0)
            ax.text(0.98, 0.02, f"Outlined cell: {pop:,.0f} people", transform=ax.transAxes, ha="right",
                    va="bottom", fontsize=6.5, color=INK, bbox=dict(facecolor=SURFACE, edgecolor="none", pad=1.5,
                                                                       alpha=0.85))
            if i == 0:
                ax.set_title(METHOD_TITLES[layer], color=INK)
            if j == 0:
                ax.text(-0.04, 0.5, res_label(r, "\n"), transform=ax.transAxes, rotation=90, ha="right",
                        va="center", fontsize=8)
            if i == 2 and j == 0:
                scalebar(ax, 5)
    fig.subplots_adjust(left=0.05, right=0.995, top=0.95, bottom=0.11, wspace=0.03, hspace=0.04)
    density_legend(fig, [0.30, 0.055, 0.6, 0.018])
    save(fig, "fig2_toronto_3x3", srcs + [C.PROV_GPKG], log)


# ----------------------------------------------------------------------------
# Fig. 3 / S1: national hybrid
# ----------------------------------------------------------------------------
def fig_national(log: Log, prov: gpd.GeoDataFrame, r: int, name: str) -> None:
    # national display: drop parts under 20 km2 and simplify to 1.5 km (EPSG:3347 metres); the zoomed
    # maps clip the full-resolution boundaries instead
    parts = prov.explode(index_parts=False)
    parts = parts[parts.area >= 20e6]
    simple = parts.dissolve("PR").reset_index()
    simple["geometry"] = simple.geometry.simplify(1500)
    b = simple.total_bounds
    pad = 0.01 * (b[2] - b[0])
    b = (b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad)
    asp = (b[3] - b[1]) / (b[2] - b[0])
    fig = plt.figure(figsize=(FULL_W, FULL_W * asp + 0.7))
    ax = fig.add_axes([0, 0.12, 1, 0.88])
    df = load_layer("hyb", r)
    simple.plot(ax=ax, facecolor=LAND, edgecolor="none", zorder=0)
    draw_hex(ax, df, gap=False, rasterized=True)
    simple.boundary.plot(ax=ax, color=BORDER, linewidth=0.35, zorder=3)
    map_axes(ax, b)
    scalebar(ax, 500, loc=(0.05, 0.12))
    ax.text(0.05, 0.02, f"Hybrid layer (τ = 50), {res_label(r)}, {len(df):,} populated cells.\n"
                        "NAD83 / Statistics Canada Lambert (EPSG:3347).",
            transform=ax.transAxes, ha="left", va="bottom", fontsize=6.5, color=INK2)
    density_legend(fig, [0.25, 0.07, 0.65, 0.022])
    save(fig, name, [layer_path("hyb", r), C.PROV_GPKG], log)


# ----------------------------------------------------------------------------
# Fig. new B: urban and rural windows at r = 6, 7, 8
# ----------------------------------------------------------------------------
def figB(log: Log, prov: gpd.GeoDataFrame) -> None:
    names = list(WINDOWS)
    w = WINDOWS[names[0]]
    asp = w[3] / w[2]
    fig, axes = plt.subplots(2, 3, figsize=(FULL_W, FULL_W / 3 * asp * 2 + 0.75))
    srcs = []
    for i, nm in enumerate(names):
        b = window_bounds(*WINDOWS[nm])
        for j, r in enumerate(C.RESOLUTIONS):
            ax = axes[i, j]
            df = load_layer("hyb", r, cells_in_bounds(b, r))
            srcs.append(layer_path("hyb", r))
            draw_land(ax, prov, b)
            draw_hex(ax, df, gap=r < 8)
            map_axes(ax, b)
            # cells whose centre lies in the window
            ll = np.array([h3.cell_to_latlng(c) for c in df.h3])
            x, y = TO_MAP.transform(ll[:, 1], ll[:, 0])
            inside = (x >= b[0]) & (x <= b[2]) & (y >= b[1]) & (y <= b[3])
            ax.text(0.98, 0.02, f"{inside.sum():,} populated cells", transform=ax.transAxes, ha="right",
                    va="bottom", fontsize=6.5, color=INK,
                    bbox=dict(facecolor=SURFACE, edgecolor="none", pad=1.5, alpha=0.85))
            if i == 0:
                ax.set_title(res_label(r), color=INK)
            if j == 0:
                ax.text(-0.04, 0.5, nm.replace(" (", "\n("), transform=ax.transAxes, rotation=90, ha="right",
                        va="center", fontsize=8)
                scalebar(ax, 10)
    fig.subplots_adjust(left=0.05, right=0.995, top=0.93, bottom=0.15, wspace=0.03, hspace=0.04)
    density_legend(fig, [0.30, 0.08, 0.6, 0.025])
    save(fig, "figB_urban_rural", srcs + [C.PROV_GPKG], log)


FIGS = ["1a", "1b", "A", "2", "3", "S1", "B"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", choices=FIGS, default=FIGS)
    a = ap.parse_args()
    C.TABLES.mkdir(exist_ok=True)
    log = Log(C.TABLES / "phaseG_figures_log.txt")
    t0 = time.time()
    prov = provinces() if set(a.only) & {"2", "3", "S1", "B"} else None
    for f in a.only:
        {"1a": lambda: fig1a(log), "1b": lambda: fig1b(log), "A": lambda: figA(log),
         "2": lambda: fig2(log, prov), "3": lambda: fig_national(log, prov, 6, "fig3_national_hyb_r6"),
         "S1": lambda: fig_national(log, prov, 8, "figS1_national_hyb_r8"), "B": lambda: figB(log, prov)}[f]()
    src = pd.DataFrame(SOURCES).drop_duplicates()
    out = C.FIGURES_V2 / "figure_sources.csv"
    if out.exists():
        old = pd.read_csv(out)
        src = pd.concat([old[~old.figure.isin(src.figure)], src])
    src.sort_values(["figure", "source"]).to_csv(out, index=False)
    log(f"done in {time.time() - t0:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
