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


def make_audio_profile(df: pd.DataFrame, *, width: int = 240, height: int = 260):
    if df is None or len(df) == 0:
        return (
            alt.Chart(pd.DataFrame({"feature": [], "mean_value": []}))
            .mark_bar()
            .properties(width=width, height=height, title="Audio Feature Profile")
        )

    cols = [c for c in PROFILE_FEATURES if c in df.columns]
    means = df[cols].mean().reset_index()
    means.columns = ["feature", "mean_value"]
    means["feature"] = means["feature"].str.capitalize()
    feat_labels = [c.capitalize() for c in cols]

    bars = (
        alt.Chart(means)
        .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5)
        .encode(
            y=alt.Y(
                "feature:N",
                sort=feat_labels,
                title=None,
                axis=alt.Axis(labelFontSize=11),
            ),
            x=alt.X(
                "mean_value:Q",
                title="Mean (0–1)",
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
        .mark_text(align="left", dx=4, fontSize=10, color="#555")
        .encode(
            y=alt.Y("feature:N", sort=feat_labels),
            x="mean_value:Q",
            text=alt.Text("mean_value:Q", format=".2f"),
        )
    )

    return (
        (bars + text)
        .properties(width=width, height=height, title="Avg Audio Profile (Selection)")
        .configure_view(stroke=None)
        .configure_axis(labelFontSize=11, titleFontSize=11)
        .configure_title(fontSize=13, fontWeight=600, anchor="start")
    )
