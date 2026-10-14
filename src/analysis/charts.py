"""Generate a visual summary of the main findings (outputs/charts/).

Three charts:
    1. functional_literacy_by_access_tier.png
       Weighted functional literacy rate by household digital access tier, with
       the 95% confidence interval and the unweighted sample size of each bar.

    2. home_internet_by_region.png
       Share of households with home internet by region, sorted, with 95%
       confidence intervals, sample sizes and the national rate for reference.

    3. sample_sizes_region_tier.png
       Heat-map of unweighted persons sampled by region x digital access tier
       (from agg_literacy_digital), so readers see where cells are thin.

Charts 1 and 2 read outputs/analysis/key_estimates.csv, written by the
estimate_key_indicators task (src/analysis/estimates.py), so the charts show
exactly the numbers and intervals reported in the README.
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import layer_path
from src.utils.logging_utils import get_logger

log = get_logger(__name__)

# Colours: one blue, light to dark, for the ordered access tiers; a single blue
# for regions (they are not ordered); a one-hue blue ramp for the heat-map.
_TIER_COLOURS = {"No access": "#86b6ef", "Low": "#3987e5", "Moderate": "#1c5cab", "High": "#0d366b"}
_REGION_COLOUR = "#2a78d6"
_HEAT_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
_INK, _INK_SECONDARY, _GRID = "#0b0b0b", "#52514e", "#e4e3df"
_CI_NOTE = ("Error bars: 95% confidence interval, design-based (survey weights, sampled PSUs as clusters, "
            "regions as strata).")


def _require_matplotlib():
    try:
        import matplotlib
        matplotlib.use("Agg")          # non-interactive backend – safe in Docker
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
        return plt, mticker
    except ImportError as exc:
        raise ImportError(
            "matplotlib is required for chart generation.  "
            "Add 'matplotlib' to requirements.txt and rebuild the image."
        ) from exc


def _style(ax, grid_axis: str) -> None:
    """Quiet frame: no top/right spines, faint solid gridlines behind the bars."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(_GRID)
    ax.tick_params(colors=_INK_SECONDARY, labelsize=9)
    ax.grid(axis=grid_axis, color=_GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _load_estimates() -> pd.DataFrame:
    path = layer_path("outputs") / "analysis" / "key_estimates.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run the estimate_key_indicators step first.")
    return pd.read_csv(path)


def _load_agg(curated: Path) -> pd.DataFrame:
    """Load agg_literacy_digital Parquet; fall back to the CSV copy."""
    parquet = curated / "agg_literacy_digital.parquet"
    csv_copy = layer_path("outputs") / "agg_literacy_digital.csv"
    if parquet.exists():
        return pd.read_parquet(parquet)
    if csv_copy.exists():
        return pd.read_csv(csv_copy)
    raise FileNotFoundError(
        "agg_literacy_digital.parquet not found in the curated layer.  "
        "Run the pipeline through the curated stage first."
    )


def _load_region_names(curated: Path) -> dict[int, str]:
    p = curated / "dim_region.parquet"
    if not p.exists():
        return {}
    df = pd.read_parquet(p, columns=["region_code", "region_short_name"])
    return df.set_index("region_code")["region_short_name"].to_dict()


def chart_literacy_by_tier(estimates: pd.DataFrame, out_dir: Path, plt, mticker) -> Path:
    """Bar chart: weighted literacy rate by digital access tier, with 95% CI and n."""
    rows = estimates[(estimates["indicator"] == "Functional literacy (persons 10-64)")
                     & (estimates["breakdown"] == "Digital access tier")].set_index("group")
    rows = rows.reindex([t for t in _TIER_COLOURS if t in rows.index])
    x = np.arange(len(rows))

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x, rows["weighted_pct"], width=0.62, color=[_TIER_COLOURS[t] for t in rows.index])
    ax.errorbar(x, rows["weighted_pct"],
                yerr=[rows["weighted_pct"] - rows["ci95_low"], rows["ci95_high"] - rows["weighted_pct"]],
                fmt="none", ecolor=_INK, elinewidth=1.4, capsize=5, capthick=1.4)
    for i, (_, row) in enumerate(rows.iterrows()):
        ax.text(i, row["ci95_high"] + 1.5, f"{row['weighted_pct']:.1f}%", ha="center", va="bottom",
                fontsize=11, fontweight="bold", color=_INK)
    ax.set_xticks(x, [f"{tier}\nn = {n:,}" for tier, n in zip(rows.index, rows["unweighted_n"])])
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    ax.set_xlabel("Household digital access tier (n = unweighted persons sampled)", fontsize=9, color=_INK_SECONDARY)
    ax.set_ylabel("Functionally literate, persons 10–64", fontsize=9, color=_INK_SECONDARY)
    ax.set_title("Functional literacy rises with household digital access", loc="left",
                 fontsize=13, fontweight="bold", color=_INK, pad=22)
    ax.text(0, 1.02, "FLEMMS 2024, survey-weighted rates", transform=ax.transAxes, fontsize=9, color=_INK_SECONDARY)
    _style(ax, "y")
    fig.text(0.01, -0.03, _CI_NOTE + "\nAn association, not proof of cause: income and education affect both.",
             fontsize=7.5, color=_INK_SECONDARY)

    fig.tight_layout()
    out = out_dir / "functional_literacy_by_access_tier.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    log.info("Chart saved: %s", out)
    return out


def chart_home_internet_by_region(estimates: pd.DataFrame, out_dir: Path, plt, mticker) -> Path:
    """Horizontal bar chart: % households with home internet by region, with 95% CI and n."""
    internet = estimates[estimates["indicator"] == "Households with home internet"]
    national = internet[internet["breakdown"] == "National"].iloc[0]
    rows = internet[internet["breakdown"] == "Region"].sort_values("weighted_pct")
    y = np.arange(len(rows))

    fig, ax = plt.subplots(figsize=(8, 7.5))
    ax.barh(y, rows["weighted_pct"], height=0.68, color=_REGION_COLOUR)
    ax.errorbar(rows["weighted_pct"], y,
                xerr=[rows["weighted_pct"] - rows["ci95_low"], rows["ci95_high"] - rows["weighted_pct"]],
                fmt="none", ecolor=_INK, elinewidth=1.1, capsize=3, capthick=1.1)
    for i, (_, row) in enumerate(rows.iterrows()):
        ax.text(row["ci95_high"] + 0.8, i, f"{row['weighted_pct']:.1f}%   n = {row['unweighted_n']:,}",
                va="center", ha="left", fontsize=8, color=_INK_SECONDARY, zorder=4,
                bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})
    ax.axvline(national["weighted_pct"], color=_INK_SECONDARY, linewidth=1, zorder=0.5)
    ax.text(national["weighted_pct"] + 0.5, len(rows) - 0.4, f"Philippines {national['weighted_pct']:.1f}%",
            fontsize=8, color=_INK_SECONDARY, va="bottom")
    ax.set_yticks(y, rows["group"])
    ax.set_xlim(0, 72)
    ax.set_ylim(-0.6, len(rows) + 0.4)
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    ax.set_xlabel("Households with home internet (n = unweighted households sampled)", fontsize=9,
                  color=_INK_SECONDARY)
    ax.set_title("Home internet access by region", loc="left", fontsize=13, fontweight="bold", color=_INK, pad=22)
    ax.text(0, 1.015, "FLEMMS 2024, survey-weighted share of households", transform=ax.transAxes,
            fontsize=9, color=_INK_SECONDARY)
    _style(ax, "x")
    fig.text(0.01, -0.02, _CI_NOTE + "\nRegions whose intervals overlap should not be ranked against each other.",
             fontsize=7.5, color=_INK_SECONDARY)

    fig.tight_layout()
    out = out_dir / "home_internet_by_region.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    log.info("Chart saved: %s", out)
    return out


def chart_sample_sizes(agg: pd.DataFrame, region_names: dict, out_dir: Path, plt) -> Path:
    """Heat-map: unweighted persons sampled by region x digital access tier."""
    from matplotlib.colors import LinearSegmentedColormap

    pivot = (
        agg.groupby(["region_code", "digital_access_tier"])["persons_sampled"]
        .sum()
        .unstack("digital_access_tier")
        .reindex(columns=[t for t in _TIER_COLOURS if t in agg["digital_access_tier"].unique()])
    )
    pivot.index = [region_names.get(int(rc), f"Region {rc}") for rc in pivot.index]
    pivot = pivot.sort_index()

    fig, ax = plt.subplots(figsize=(7.5, 8))
    im = ax.imshow(pivot.values, cmap=LinearSegmentedColormap.from_list("blues", _HEAT_RAMP), aspect="auto")
    threshold = np.nanmax(pivot.values) * 0.45
    for (i, j), val in np.ndenumerate(pivot.values):
        if not np.isnan(val):
            ax.text(j, i, f"{int(val):,}", ha="center", va="center", fontsize=8,
                    color="white" if val > threshold else _INK)

    ax.set_xticks(range(len(pivot.columns)), pivot.columns, fontsize=9)
    ax.set_yticks(range(len(pivot.index)), pivot.index, fontsize=8.5)
    ax.tick_params(colors=_INK_SECONDARY, length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xlabel("Household digital access tier", fontsize=9, color=_INK_SECONDARY)
    ax.set_title("Sample sizes behind the rates", loc="left", fontsize=13, fontweight="bold", color=_INK, pad=22)
    ax.text(0, 1.015, "Unweighted persons 10–64 sampled, by region and access tier", transform=ax.transAxes,
            fontsize=9, color=_INK_SECONDARY)
    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cbar.outline.set_visible(False)
    cbar.ax.tick_params(colors=_INK_SECONDARY, labelsize=8)
    cbar.set_label("Persons sampled", fontsize=8, color=_INK_SECONDARY)
    fig.text(0.01, -0.01, f"Smallest cell: {int(np.nanmin(pivot.values)):,} people. Rates for small cells are "
             "less precise; check their confidence intervals before comparing.", fontsize=7.5, color=_INK_SECONDARY)

    fig.tight_layout()
    out = out_dir / "sample_sizes_region_tier.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    log.info("Chart saved: %s", out)
    return out


def generate_charts(batch_id: str) -> list[str]:
    """Generate all three summary charts.  Returns the paths of created files."""
    plt, mticker = _require_matplotlib()

    warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

    curated = layer_path("curated")
    out_dir = layer_path("outputs") / "charts"
    out_dir.mkdir(parents=True, exist_ok=True)

    estimates = _load_estimates()
    agg = _load_agg(curated)
    # Keep only analysis-eligible age groups (10-64)
    age_10_64 = ["10-14", "15-24", "25-34", "35-44", "45-54", "55-64"]
    if "age_group" in agg.columns:
        agg = agg[agg["age_group"].isin(age_10_64)]

    produced = [
        str(chart_literacy_by_tier(estimates, out_dir, plt, mticker)),
        str(chart_home_internet_by_region(estimates, out_dir, plt, mticker)),
        str(chart_sample_sizes(agg, _load_region_names(curated), out_dir, plt)),
    ]
    log.info("Chart generation complete: %d files in %s", len(produced), out_dir)
    return produced
