"""Mood quadrant chart builders for energy-valence heatmap summaries."""

import altair as alt
import pandas as pd


def make_mood_quadrant(
    df: pd.DataFrame,
    *,
    width: int = 290,
    height: int = 250,
):
    """Build a binned energy/valence heatmap with per-cell track counts.

    Args:
        df: Input track rows containing ``energy`` and ``valence`` columns.
        width: Target chart width in pixels.
        height: Target chart height in pixels.

    Returns:
        alt.Chart: Configured Altair heatmap chart.
    """
    required = {"energy", "valence"}
    if df is None or len(df) == 0 or not required.issubset(df.columns):
        return (
            alt.Chart(pd.DataFrame({"label": ["No data"]}))
            .mark_text(fontSize=12, color="#8898a9")
            .encode(text="label:N")
            .properties(width=width, height=height)
            .configure_view(stroke=None)
        )

    work = df[["energy", "valence"]].copy()
    work["energy"] = pd.to_numeric(work["energy"], errors="coerce")
    work["valence"] = pd.to_numeric(work["valence"], errors="coerce")
    work = work.dropna()
    if work.empty:
        return (
            alt.Chart(pd.DataFrame({"label": ["No data"]}))
            .mark_text(fontSize=12, color="#8898a9")
            .encode(text="label:N")
            .properties(width=width, height=height)
            .configure_view(stroke=None)
        )

    bins = 5
    work["x_bin"] = pd.cut(work["energy"], bins=bins, labels=False, include_lowest=True).astype(int)
    work["y_bin"] = pd.cut(work["valence"], bins=bins, labels=False, include_lowest=True).astype(int)
    counts = work.groupby(["x_bin", "y_bin"]).size().reset_index(name="count")

    all_bins = pd.MultiIndex.from_product([range(bins), range(bins)], names=["x_bin", "y_bin"]).to_frame(index=False)
    counts = all_bins.merge(counts, on=["x_bin", "y_bin"], how="left").fillna({"count": 0})
    counts["count"] = counts["count"].astype(int)
    step = 1.0 / bins
    counts["x0"] = counts["x_bin"] * step
    counts["x1"] = counts["x0"] + step
    counts["y0"] = counts["y_bin"] * step
    counts["y1"] = counts["y0"] + step
    counts["x_mid"] = counts["x0"] + (step / 2.0)
    counts["y_mid"] = counts["y0"] + (step / 2.0)
    counts["cell"] = (
        "E" + (counts["x_bin"] + 1).astype(str) +
        " · V" + (counts["y_bin"] + 1).astype(str)
    )

    base = (
        alt.Chart(counts)
        .mark_rect(stroke="#ffffff", strokeWidth=1.2, opacity=0.96)
        .encode(
            x=alt.X("x0:Q", title="Energy", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(values=[0, 0.5, 1.0], grid=False)),
            x2="x1:Q",
            y=alt.Y("y0:Q", title="Valence", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(values=[0, 0.5, 1.0], grid=False)),
            y2="y1:Q",
            color=alt.Color(
                "count:Q",
                title="Tracks",
                scale=alt.Scale(
                    domain=[float(counts["count"].min()), float(counts["count"].max())],
                    range=["#4E79A7", "#AFCDEA", "#F7F7F7", "#F4B7A5", "#D16B6B"],
                ),
                legend=alt.Legend(orient="right", titleFontSize=10, labelFontSize=10),
            ),
            tooltip=[
                alt.Tooltip("cell:N", title="Cell"),
                alt.Tooltip("count:Q", title="Tracks"),
            ],
        )
    )

    text = (
        alt.Chart(counts)
        .mark_text(fontSize=10, color="#2f3e4c", fontWeight=700)
        .encode(
            x=alt.X("x_mid:Q"),
            y=alt.Y("y_mid:Q"),
            text=alt.Text("count:Q"),
        )
    )

    return (
        (base + text)
        .properties(width=width, height=height)
        .configure_view(stroke=None)
        .configure_axis(labelFontSize=10, titleFontSize=11)
    )
