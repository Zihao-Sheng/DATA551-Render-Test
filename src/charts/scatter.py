# charts/scatter.py
import altair as alt
import pandas as pd


def make_scatter(
    df: pd.DataFrame,
    *,
    mode: str = "brush",  # "brush" or "pan"
    max_points: int = 2000,
    topk_genres: int = 10,
    selection_name: str = "brush_selection",
    width: int = 520,
    height: int = 400,
):
    # Limit the number of points to improve performance and readability
    n_total = len(df)
    sampled = False
    if n_total > max_points:
        df = df.sample(n=max_points, random_state=42)
        sampled = True

    # Group less frequent genres into "Other" to keep the legend concise
    top = df["track_genre"].value_counts().head(topk_genres).index
    df = df.assign(
        genre_group=df["track_genre"].where(df["track_genre"].isin(top), "Other")
    )
    legend_order = list(top) + ["Other"]

    chart = (
        alt.Chart(df)
        .mark_point(opacity=0.5)
        .encode(
            x=alt.X("energy:Q", title="Energy"),
            y=alt.Y("valence:Q", title="Valence"),
            color=alt.Color(
                "genre_group:N",
                title=f"Genre (Top {topk_genres} + Other)",
                sort=legend_order,
            ),
            size=alt.Size(
                "popularity:Q",
                title="Popularity",
                scale=alt.Scale(range=[20, 200]),
            ),
            tooltip=[
                "track_name:N",
                "artists:N",
                "track_genre:N",
                "genre_group:N",
                "popularity:Q",
                "tempo:Q",
                "explicit:N",
            ],
        )
        .properties(width=width, height=height)
        .configure(autosize=alt.AutoSizeParams(type="fit", contains="padding"))
    )

    # Interaction mode
    if mode == "brush":
        brush = alt.selection_interval(name=selection_name)
        chart = chart.add_params(brush)
    elif mode == "pan":
        chart = chart.interactive()
    else:
        raise ValueError("mode must be either 'brush' or 'pan'")

    meta = {
        "n_total": n_total,
        "n_shown": len(df),
        "sampled": sampled,
        "max_points": max_points,
        "topk_genres": topk_genres,
        "top_genres": list(top),
        "mode": mode,
    }
    return chart, meta
