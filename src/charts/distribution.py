"""Distribution chart builders for normalized audio feature densities."""

import altair as alt
import pandas as pd

FEATURES = ["danceability", "energy", "valence", "acousticness"]
PALETTE = ["#1DB954", "#FF7A00", "#4C7DFF", "#9B5DE5"]


def make_distribution(
    df: pd.DataFrame,
    *,
    max_points: int = 3000,
    width: int = 480,
    height: int = 200,
    swap_axes: bool = False,
):
    """Build a multi-feature density area chart for selected tracks.

    Args:
        df: Input track rows containing normalized audio feature columns.
        max_points: Maximum number of rows to sample for rendering performance.
        width: Target chart width in pixels.
        height: Target chart height in pixels.
        swap_axes: Compatibility flag retained for callers; currently ignored.

    Returns:
        alt.Chart: Configured Altair density chart.
    """
    if df is None or len(df) == 0:
        return (
            alt.Chart(pd.DataFrame({"Feature": [], "value": []}))
            .mark_area()
            .properties(width=width, height=height)
        )

    plot_df = df if len(df) <= max_points else df.sample(n=max_points, random_state=42)
    cols = [c for c in FEATURES if c in plot_df.columns]

    melted = (
        plot_df[cols]
        .melt(var_name="Feature", value_name="value")
        .dropna()
    )
    melted["Feature"] = melted["Feature"].str.capitalize()
    feat_labels = [c.capitalize() for c in cols]

    # Keep Feature Density on canonical axes (x=value, y=density).
    # `swap_axes` is accepted for API compatibility but intentionally ignored
    # to avoid unstable orientation rendering in compact popup layouts.
    _ = swap_axes
    chart = (
        alt.Chart(melted)
        .transform_density(
            "value",
            as_=["value", "density"],
            groupby=["Feature"],
            extent=[0, 1],
        )
        .mark_area(opacity=0.55, interpolate="monotone")
        .encode(
            x=alt.X(
                "value:Q",
                title="Feature Value",
                scale=alt.Scale(domain=[0, 1]),
                axis=alt.Axis(grid=False),
            ),
            y=alt.Y(
                "density:Q",
                title="Density",
                stack=None,
                axis=alt.Axis(labels=False, ticks=False, domain=False, grid=False),
            ),
            color=alt.Color(
                "Feature:N",
                scale=alt.Scale(domain=feat_labels, range=PALETTE[: len(feat_labels)]),
                legend=alt.Legend(orient="top", titleFontSize=11, labelFontSize=11),
            ),
            tooltip=[
                alt.Tooltip("Feature:N"),
                alt.Tooltip("value:Q", format=".2f"),
                alt.Tooltip("density:Q", format=".3f"),
            ],
        )
        .properties(width=width, height=height)
    )

    return (
        chart
        .configure(autosize=alt.AutoSizeParams(type="fit", contains="padding"))
        .configure_view(stroke=None)
        .configure_axis(labelFontSize=11, titleFontSize=11)
        .configure_title(fontSize=13, fontWeight=600, anchor="start")
    )
