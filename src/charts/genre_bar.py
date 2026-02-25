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

    bars = (
        alt.Chart(agg)
        .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
        .encode(
            x=alt.X(
                "track_genre:N",
                sort=sort_order,
                title=None,
                axis=alt.Axis(
                    labelAngle=-25,
                    labelLimit=80,
                    labelAlign="right",
                    labelBaseline="top",
                    labelPadding=6,
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
                    orient="left",
                    gradientLength=80,
                    gradientThickness=8,
                    offset=4,
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

    return (
        (bars + text)
        .properties(
            width=width,
            height=height,
            padding={"top": 8, "right": 8, "bottom": 36, "left": 8},
        )
        .configure(autosize=alt.AutoSizeParams(type="fit", contains="padding"))
        .configure_view(stroke=None)
        .configure_axis(labelFontSize=11, titleFontSize=11)
        .configure_title(fontSize=13, fontWeight=600, anchor="start")
    )
