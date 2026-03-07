import altair as alt
import pandas as pd


def make_genre_bar(df: pd.DataFrame, *, top_n: int = 15, width: int = 480, height: int = 300):
    if df is None or len(df) == 0:
        return (
            alt.Chart(pd.DataFrame({"track_genre": [], "avg_popularity": []}))
            .mark_bar()
            .encode(x="track_genre:N", y="avg_popularity:Q")
            .properties(width=width, height=height)
        )

    agg = (
        df.groupby("track_genre")
        .agg(
            avg_popularity=("popularity", "mean"),
            avg_energy=("energy", "mean"),
            avg_danceability=("danceability", "mean"),
            count=("track_name", "count"),
        )
        .reset_index()
        .nlargest(top_n, "avg_popularity")
    )

    sort_order = agg.sort_values("avg_popularity", ascending=False)["track_genre"].tolist()
    n_genres = len(sort_order)
    dense = n_genres >= 10
    label_angle = -55 if dense else -25
    label_limit = 55 if dense else 80
    label_padding = 2 if dense else 6

    bars = (
        alt.Chart(agg)
        .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
        .encode(
            x=alt.X(
                "track_genre:N",
                sort=sort_order,
                title=None,
                axis=alt.Axis(
                    labelAngle=label_angle,
                    labelLimit=label_limit,
                    labelAlign="right",
                    labelBaseline="top",
                    labelPadding=label_padding,
                    labelOverlap="greedy",
                    labelExpr="length(datum.label) > 11 ? slice(datum.label, 0, 11) + '…' : datum.label",
                ),
            ),
            y=alt.Y(
                "avg_popularity:Q",
                title="Avg Popularity",
                scale=alt.Scale(domain=[0, 100]),
                axis=alt.Axis(grid=True, gridOpacity=0.2),
            ),
            color=alt.Color(
                "avg_energy:Q",
                title="Avg Energy",
                scale=alt.Scale(scheme="plasma", domain=[0, 1]),
                legend=alt.Legend(
                    orient="top",
                    direction="horizontal",
                    gradientLength=130,
                    gradientThickness=8,
                    offset=6,
                    title="Avg Energy",
                    titleFontSize=10,
                    labelFontSize=9,
                ),
            ),
            tooltip=[
                alt.Tooltip("track_genre:N", title="Genre"),
                alt.Tooltip("avg_popularity:Q", title="Avg Popularity", format=".1f"),
                alt.Tooltip("avg_energy:Q", title="Avg Energy", format=".2f"),
                alt.Tooltip("avg_danceability:Q", title="Avg Danceability", format=".2f"),
                alt.Tooltip("count:Q", title="Track Count"),
            ],
        )
        .properties(width=width, height=height)
    )

    text = (
        alt.Chart(agg)
        .mark_text(align="center", dy=-6, fontSize=10, color="#666")
        .encode(
            x=alt.X("track_genre:N", sort=sort_order),
            y=alt.Y("avg_popularity:Q"),
            text=alt.Text("avg_popularity:Q", format=".1f"),
        )
    )

    base = bars if dense else (bars + text)

    return (
        base
        .properties(
            width=width,
            height=height,
            padding={"top": 26, "right": 8, "bottom": 48 if dense else 36, "left": 8},
        )
        .configure(autosize=alt.AutoSizeParams(type="fit", contains="padding"))
        .configure_view(stroke=None)
        .configure_axis(labelFontSize=11, titleFontSize=11)
        .configure_title(fontSize=13, fontWeight=600, anchor="start")
    )
