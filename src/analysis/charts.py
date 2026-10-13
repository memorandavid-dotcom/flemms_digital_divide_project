"""Generate a visual summary of the main findings (outputs/charts/).

Three charts:
    1. functional_literacy_by_access_tier.png
       Bar chart: weighted functional literacy rate by household digital access tier
       with unweighted sample sizes annotated on each bar.

    2. home_internet_by_region.png
       Horizontal bar chart: % households with home internet by region, sorted
       descending, with weighted population and sample sizes in a side column.

    3. sample_sizes.png
       Grid heat-map: unweighted persons-sampled by region x digital-access-tier
       (from agg_literacy_digital), so readers see exactly where cells are thin.

Requirements: matplotlib (already in requirements.txt as a dependency of pandas
visualisation, but we import it explicitly; add if missing).

Output files are committed to outputs/charts/ so the demo and README can embed them.
"""

import warnings
from pathlib import Path

import pandas as pd

from src.config import layer_path
from src.utils.logging_utils import get_logger

log = get_logger(__name__)

# ── colour palette (PSA-adjacent: navy blue + gold accent) ──────────────────
_TIER_COLOURS = {
    "No access": "#C0392B",   # deep red
    "Low":       "#E67E22",   # orange
    "Moderate":  "#2980B9",   # steel blue
    "High":      "#1A5276",   # dark navy
}
_REGION_COLOUR = "#2471A3"
_SAMPLE_CMAP   = "YlGnBu"


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


def _load_household(curated: Path) -> pd.DataFrame | None:
    p = curated / "household.parquet"
    if not p.exists():
        return None
    return pd.read_parquet(p, columns=["region_code", "has_home_internet", "household_weight"])


def chart_literacy_by_tier(agg: pd.DataFrame, out_dir: Path, plt, mticker) -> Path:
    """Bar chart: weighted literacy rate by digital access tier, n annotated."""
    tier_order = ["No access", "Low", "Moderate", "High"]

    grp = (
        agg.groupby("digital_access_tier")
        .agg(
            persons_sampled=("persons_sampled", "sum"),
            weighted_pop=("weighted_population", "sum"),
            # weighted rate: weighted mean of rates
            fl_rate=("functional_literacy_rate", lambda x: (
                (x * agg.loc[x.index, "weighted_population"]).sum()
                / agg.loc[x.index, "weighted_population"].sum()
            )),
        )
        .reindex([t for t in tier_order if t in agg["digital_access_tier"].unique()])
    )

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(
        grp.index,
        grp["fl_rate"],
        color=[_TIER_COLOURS.get(t, "#555") for t in grp.index],
        edgecolor="white", linewidth=0.8,
    )

    for bar, (tier, row) in zip(bars, grp.iterrows()):
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + 0.6,
                f"{h:.1f}%", ha="center", va="bottom", fontsize=9, fontweight="bold")
        ax.text(bar.get_x() + bar.get_width() / 2, h / 2,
                f"n={row['persons_sampled']:,}", ha="center", va="center",
                fontsize=7.5, color="white", alpha=0.92)

    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax.set_xlabel("Household digital access tier", fontsize=10)
    ax.set_ylabel("Survey-weighted functional literacy rate", fontsize=10)
    ax.set_title(
        "Functional Literacy Rate by Household Digital Access Tier\n"
        "FLEMMS 2024 · Persons 10\u201364 · Survey-weighted · n = unweighted sample",
        fontsize=10, pad=10,
    )

    note = (
        "Note: Rates are weighted point estimates; design-aware standard errors "
        "are not available from the public-use file.\n"
        "Unweighted n shown on bars. Treat small-cell rates as indicative, not precise."
    )
    fig.text(0.5, -0.04, note, ha="center", fontsize=7.5, color="#555",
             wrap=True)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    fig.tight_layout()
    out = out_dir / "functional_literacy_by_access_tier.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    log.info("Chart saved: %s", out)
    return out


def chart_home_internet_by_region(household: pd.DataFrame, region_names: dict,
                                   out_dir: Path, plt, mticker) -> Path:
    """Horizontal bar chart: % households with home internet by region."""
    grp = (
        household.groupby("region_code")
        .apply(lambda df: pd.Series({
            "pct": 100 * (df["household_weight"] * df["has_home_internet"]).sum()
                   / df["household_weight"].sum(),
            "n_hh": len(df),
        }), include_groups=False)
        .sort_values("pct", ascending=True)
    )
    grp.index = [region_names.get(int(rc), f"Region {rc}") for rc in grp.index]

    fig, ax = plt.subplots(figsize=(8, 7))
    bars = ax.barh(grp.index, grp["pct"],
                   color=_REGION_COLOUR, edgecolor="white", linewidth=0.5)

    for bar, (rname, row) in zip(bars, grp.iterrows()):
        w = bar.get_width()
        ax.text(w + 0.3, bar.get_y() + bar.get_height() / 2,
                f"{w:.1f}%  (n={int(row['n_hh']):,})",
                va="center", ha="left", fontsize=7.5)

    ax.set_xlim(0, 70)
    ax.xaxis.set_major_formatter(mticker.PercentFormatter())
    ax.set_xlabel("Households with home internet (survey-weighted %)", fontsize=10)
    ax.set_title(
        "Home Internet Access by Region\n"
        "FLEMMS 2024 Households · Survey-weighted · n = sampled households",
        fontsize=10, pad=10,
    )

    note = (
        "Note: Weighted point estimates only; design-aware CIs not available from public-use file.\n"
        "n = unweighted household count in parentheses."
    )
    fig.text(0.5, -0.02, note, ha="center", fontsize=7.5, color="#555")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", linestyle="--", alpha=0.4)

    fig.tight_layout()
    out = out_dir / "home_internet_by_region.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    log.info("Chart saved: %s", out)
    return out


def chart_sample_sizes(agg: pd.DataFrame, region_names: dict,
                        out_dir: Path, plt) -> Path:
    """Heat-map: unweighted persons-sampled by region x digital-access-tier."""
    import numpy as np

    tier_order = ["No access", "Low", "Moderate", "High"]
    pivot = (
        agg.groupby(["region_code", "digital_access_tier"])["persons_sampled"]
        .sum()
        .unstack("digital_access_tier")
        .reindex(columns=[t for t in tier_order if t in agg["digital_access_tier"].unique()])
    )
    pivot.index = [region_names.get(int(rc), f"Region {rc}") for rc in pivot.index]
    pivot = pivot.sort_index()

    fig, ax = plt.subplots(figsize=(8, 8))
    im = ax.imshow(pivot.values, cmap=_SAMPLE_CMAP, aspect="auto")

    # Annotate each cell
    for (i, j), val in np.ndenumerate(pivot.values):
        if not np.isnan(val):
            text_colour = "black" if val < pivot.values[~np.isnan(pivot.values)].max() * 0.6 else "white"
            ax.text(j, i, f"{int(val):,}", ha="center", va="center",
                    fontsize=7, color=text_colour)

    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, fontsize=9)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index, fontsize=8)
    ax.set_xlabel("Household digital access tier", fontsize=10)
    ax.set_title(
        "Unweighted Sample Sizes: Persons 10\u201364 by Region and Access Tier\n"
        "FLEMMS 2024 · Use caution where n is small",
        fontsize=10, pad=10,
    )

    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("Persons sampled (unweighted n)", fontsize=8)

    fig.tight_layout()
    out = out_dir / "sample_sizes_region_tier.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
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

    agg = _load_agg(curated)
    # Keep only analysis-eligible age groups (10-64)
    age_10_64 = ["10-14", "15-24", "25-34", "35-44", "45-54", "55-64"]
    if "age_group" in agg.columns:
        agg = agg[agg["age_group"].isin(age_10_64)]

    region_names = _load_region_names(curated)
    household = _load_household(curated)

    produced = []
    produced.append(str(chart_literacy_by_tier(agg, out_dir, plt, mticker)))

    if household is not None:
        produced.append(str(chart_home_internet_by_region(household, region_names, out_dir, plt, mticker)))
    else:
        log.warning("household.parquet not found; skipping home-internet chart")

    produced.append(str(chart_sample_sizes(agg, region_names, out_dir, plt)))

    log.info("Chart generation complete: %d files in %s", len(produced), out_dir)
    return produced
