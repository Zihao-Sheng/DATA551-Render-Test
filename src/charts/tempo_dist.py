"""Tempo distribution chart builders for BPM histogram summaries."""

import altair as alt
import pandas as pd


def make_tempo_distribution(
    df: pd.DataFrame,
    *,
    width: int = 290,
    height: int = 240,
):
    """Build a tempo histogram with a highlighted median reference line.

    Args:
        df: Input track rows containing a ``tempo`` column.
        width: Target chart width in pixels.
        height: Target chart height in pixels.

    Returns:
        alt.Chart: Configured Altair histogram chart.
    """
    if df is None or len(df) == 0 or "tempo" not in df.columns:
        return (
            alt.Chart(pd.DataFrame({"label": ["No data"]}))
            .mark_text(fontSize=12, color="#8898a9")
            .encode(text="label:N")
            .properties(width=width, height=height)
            .configure_view(stroke=None)
        )

    work = df[["tempo"]].copy()
    work["tempo"] = pd.to_numeric(work["tempo"], errors="coerce").clip(0, 250)
    work = work.dropna()
    if work.empty:
        return (
            alt.Chart(pd.DataFrame({"label": ["No data"]}))
            .mark_text(fontSize=12, color="#8898a9")
            .encode(text="label:N")
            .properties(width=width, height=height)
            .configure_view(stroke=None)
        )

    median_val = float(work["tempo"].median())
    median_df = pd.DataFrame({"tempo": [median_val]})

    bars = (
        alt.Chart(work)
        .mark_bar(
            cornerRadiusTopLeft=4,
            cornerRadiusTopRight=4,
            color="#7CBF8E",
            opacity=0.9,
            stroke="#ffffff",
            strokeWidth=0.6,
        )
        .encode(
            x=alt.X(
                "tempo:Q",
                bin=alt.Bin(maxbins=18),
                title="Tempo (BPM)",
                scale=alt.Scale(domain=[0, 250]),
                axis=alt.Axis(grid=False),
            ),
            y=alt.Y("count():Q", title="Track Count", axis=alt.Axis(grid=True, gridOpacity=0.2)),
            tooltip=[alt.Tooltip("count():Q", title="Tracks")],
        )
    )

    median_line = (
        alt.Chart(median_df)
        .mark_rule(color="#7A4CC2", strokeWidth=2.0)
        .encode(x=alt.X("tempo:Q"))
    )

    median_text = (
        alt.Chart(median_df)
        .mark_text(align="left", dx=4, dy=-4, color="#7A4CC2", fontSize=10, fontWeight=700)
        .encode(
            x=alt.X("tempo:Q"),
            y=alt.value(12),
            text=alt.value(f"Median {median_val:.0f}"),
        )
    )

    return (
        (bars + median_line + median_text)
        .properties(width=width, height=height)
        .configure_view(stroke=None)
        .configure_axis(labelFontSize=10, titleFontSize=11, gridOpacity=0.2)
    )
