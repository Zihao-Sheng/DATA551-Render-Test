"""Audio profile chart builders for aggregated feature comparisons."""

import altair as alt
import pandas as pd

PROFILE_FEATURES = [
    "danceability", "energy", "valence",
    "acousticness", "speechiness", "liveness", "instrumentalness",
]
PALETTE = [
    "#1DB954", "#FF7A00", "#4C7DFF", "#9B5DE5",
    "#F15BB5", "#FFD166", "#2EC4B6",
]


def make_audio_profile(df: pd.DataFrame, *, width: int = 240, height: int = 260, swap_axes: bool = False):
    """Create an aggregated audio-feature profile bar chart.

    Args:
        df: Input track rows containing profile feature columns.
        width: Target chart width in pixels.
        height: Target chart height in pixels.
        swap_axes: When True, render horizontal bars instead of vertical bars.

    Returns:
        alt.Chart: Configured Altair bar chart for profile means.
    """
    if df is None or len(df) == 0:
        return (
            alt.Chart(pd.DataFrame({"feature": [], "mean_value": []}))
            .mark_bar()
            .properties(width=width, height=height)
        )

    cols = [c for c in PROFILE_FEATURES if c in df.columns]
    means = df[cols].mean().reset_index()
    means.columns = ["feature", "mean_value"]
    means["feature"] = means["feature"].str.capitalize()
    feat_labels = [c.capitalize() for c in cols]

    if swap_axes:
        bars = (
            alt.Chart(means)
            .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5)
            .encode(
                y=alt.Y(
                    "feature:N",
                    sort=feat_labels,
                    title=None,
                    axis=alt.Axis(labelFontSize=10, labelLimit=120, labelPadding=4),
                ),
                x=alt.X(
                    "mean_value:Q",
                    title="Mean (0-1)",
                    scale=alt.Scale(domain=[0, 1]),
                    axis=alt.Axis(grid=True, gridOpacity=0.2, labelFontSize=10),
                ),
                color=alt.Color(
                    "feature:N",
                    scale=alt.Scale(domain=feat_labels, range=PALETTE[: len(feat_labels)]),
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("feature:N", title="Feature"),
                    alt.Tooltip("mean_value:Q", title="Mean", format=".3f"),
                ],
            )
        )

        text = (
            alt.Chart(means)
            .mark_text(align="left", dx=4, fontSize=9, color="#555")
            .encode(
                y=alt.Y("feature:N", sort=feat_labels),
                x=alt.X("mean_value:Q"),
                text=alt.Text("mean_value:Q", format=".2f"),
            )
        )
    else:
        bars = (
            alt.Chart(means)
            .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5)
            .encode(
                x=alt.X(
                    "feature:N",
                    sort=feat_labels,
                    title=None,
                    axis=alt.Axis(
                        labelFontSize=11,
                        labelAngle=-25,
                        labelLimit=80,
                        labelAlign="right",
                        labelBaseline="top",
                        labelPadding=6,
                    ),
                ),
                y=alt.Y(
                    "mean_value:Q",
                    title="Mean (0-1)",
                    scale=alt.Scale(domain=[0, 1]),
                    axis=alt.Axis(grid=True, gridOpacity=0.2, labelFontSize=11),
                ),
                color=alt.Color(
                    "feature:N",
                    scale=alt.Scale(domain=feat_labels, range=PALETTE[: len(feat_labels)]),
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("feature:N", title="Feature"),
                    alt.Tooltip("mean_value:Q", title="Mean", format=".3f"),
                ],
            )
        )

        text = (
            alt.Chart(means)
            .mark_text(align="center", dy=-6, fontSize=10, color="#555")
            .encode(
                x=alt.X("feature:N", sort=feat_labels),
                y=alt.Y("mean_value:Q"),
                text=alt.Text("mean_value:Q", format=".2f"),
            )
        )

    return (
        (bars + text)
        .properties(
            width=width,
            height=height,
            padding={"top": 26, "right": 8, "bottom": 36, "left": 8},
        )
        .configure(autosize=alt.AutoSizeParams(type="fit", contains="padding"))
        .configure_view(stroke=None)
        .configure_axis(labelFontSize=11, titleFontSize=11)
        .configure_title(fontSize=13, fontWeight=600, anchor="start")
    )
