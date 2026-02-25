import altair as alt
import pandas as pd


def make_genre_bar(df: pd.DataFrame, *, top_n: int = 15, width: int = 480, height: int = 300):
    if df is None or len(df) == 0:
        return (
            alt.Chart(pd.DataFrame({"track_genre": [], "avg_popularity": []}))
            .mark_bar()
            .encode(x="avg_popularity:Q", y="track_genre:N")
            .properties(width=width, height=height, title="Average Popularity by Genre")
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

    bars = (
        alt.Chart(agg)
        .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5)
        .encode(
            y=alt.Y("track_genre:N", sort="-x", title=None, axis=alt.Axis(labelLimit=120)),
            x=alt.X(
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
                    gradientLength=140,
                    title="Avg Energy",
                    titleFontSize=11,
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
        .properties(width=width, height=height, title="Top Genres by Average Popularity")
    )

    text = (
        alt.Chart(agg)
        .mark_text(align="left", dx=4, fontSize=10, color="#666")
        .encode(
            y=alt.Y("track_genre:N", sort="-x"),
            x=alt.X("avg_popularity:Q"),
            text=alt.Text("avg_popularity:Q", format=".1f"),
        )
    )

    return (
        (bars + text)
        .configure_view(stroke=None)
        .configure_axis(labelFontSize=11, titleFontSize=12)
        .configure_title(fontSize=13, fontWeight=600, anchor="start")
    )
