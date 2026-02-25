import altair as alt
import pandas as pd

BRIGHT_PALETTE = [
    "#1DB954", "#FF7A00", "#4C7DFF", "#E71D36",
    "#9B5DE5", "#00BBF9", "#F15BB5", "#FFD166",
    "#2EC4B6", "#EF476F",
]


def make_scatter(
    df: pd.DataFrame,
    *,
    mode: str = "brush",
    max_points: int = 2000,
    topk_genres: int = 10,
    selection_name: str = "brush_selection",
    width: int = 520,
    height: int = 380,
):
    if df is None or len(df) == 0:
        return (
            alt.Chart(pd.DataFrame({"energy": [], "valence": []}))
            .mark_point()
            .encode(x="energy:Q", y="valence:Q")
            .properties(width=width, height=height),
            {"n_total": 0, "n_shown": 0, "sampled": False},
        )

    x_domain = [float(df["energy"].min()), float(df["energy"].max())]
    y_domain = [float(df["valence"].min()), float(df["valence"].max())]

    n_total = len(df)
    sampled = n_total > max_points
    plot_df = df.sample(n=max_points, random_state=42) if sampled else df.copy()

    top = plot_df["track_genre"].value_counts().head(topk_genres).index
    plot_df = plot_df.assign(
        genre_group=plot_df["track_genre"].where(plot_df["track_genre"].isin(top), "Other")
    )
    legend_order = list(top) + ["Other"]
    palette = BRIGHT_PALETTE[: len(legend_order) - 1] + ["#cccccc"]

    base = (
        alt.Chart(plot_df)
        .encode(
            x=alt.X(
                "energy:Q",
                title="Energy",
                scale=alt.Scale(domain=x_domain),
                axis=alt.Axis(grid=False),
            ),
            y=alt.Y(
                "valence:Q",
                title="Valence (Mood)",
                scale=alt.Scale(domain=y_domain),
                axis=alt.Axis(grid=False),
            ),
            color=alt.Color(
                "genre_group:N",
                title=f"Genre (Top {topk_genres})",
                sort=legend_order,
                scale=alt.Scale(domain=legend_order, range=palette),
                legend=alt.Legend(
                    symbolType="circle",
                    symbolSize=100,
                    orient="right",
                    titleFontSize=11,
                    labelFontSize=10,
                ),
            ),
            tooltip=[
                alt.Tooltip("track_name:N", title="Track"),
                alt.Tooltip("artists:N", title="Artist"),
                alt.Tooltip("track_genre:N", title="Genre"),
                alt.Tooltip("popularity:Q", title="Popularity"),
                alt.Tooltip("energy:Q", title="Energy", format=".2f"),
                alt.Tooltip("valence:Q", title="Valence", format=".2f"),
                alt.Tooltip("tempo:Q", title="Tempo", format=".0f"),
                alt.Tooltip("danceability:Q", title="Danceability", format=".2f"),
            ],
        )
        .properties(width=width, height=height)
    )

    size_enc = alt.Size(
        "popularity:Q",
        title="Popularity",
        scale=alt.Scale(range=[20, 200]),
        legend=alt.Legend(orient="right", titleFontSize=10, labelFontSize=10),
    )

    if mode == "brush":
        brush = alt.selection_interval(name=selection_name)

        chart = (
            base.mark_point()
            .encode(
                opacity=alt.condition(brush, alt.value(0.85), alt.value(0.07)),
                size=size_enc,
            )
            .add_params(brush)
        )

    else:
        chart = (
            base.mark_point(opacity=0.75)
            .encode(size=size_enc)
            .interactive()
        )

    chart = chart.configure(
        autosize=alt.AutoSizeParams(type="pad", contains="padding")
    ).configure_view(stroke=None)

    meta = {
        "n_total": n_total,
        "n_shown": len(plot_df),
        "sampled": sampled,
        "top_genres": list(top),
        "x_domain": x_domain,
        "y_domain": y_domain,
    }
    return chart, meta
