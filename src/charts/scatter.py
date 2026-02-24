# charts/scatter.py
import altair as alt
import pandas as pd


def make_scatter(
    df: pd.DataFrame,
    *,
    mode: str = "brush",            # "brush" | "pan"
    max_points: int = 2000,
    topk_genres: int = 10,
    selection_name: str = "brush_selection",
    width: int = 520,
    height: int = 400,
):
    if df is None or len(df) == 0:
        empty = (
            alt.Chart(pd.DataFrame({"energy": [], "valence": []}))
            .mark_point()
            .encode(x="energy:Q", y="valence:Q")
            .properties(width=width, height=height)
        )
        meta = {"n_total": 0, "n_shown": 0, "sampled": False}
        return empty, meta

    # Lock axis domain to full filtered data (even if we sample for plotting)
    x_domain = [float(df["energy"].min()), float(df["energy"].max())]
    y_domain = [float(df["valence"].min()), float(df["valence"].max())]

    # Downsample only for plotting
    n_total = len(df)
    sampled = False
    plot_df = df
    if n_total > max_points:
        plot_df = df.sample(n=max_points, random_state=42)
        sampled = True

    # Group genres for cleaner legend (based on plotted data)
    top = plot_df["track_genre"].value_counts().head(topk_genres).index
    plot_df = plot_df.assign(
        genre_group=plot_df["track_genre"].where(plot_df["track_genre"].isin(top), "Other")
    )
    legend_order = list(top) + ["Other"]

    # Define a bright palette for top genres + light gray for "Other"
    bright_palette = [
        "#4C7DFF",  # blue
        "#FF7A00",  # orange
        "#2EC4B6",  # teal
        "#E71D36",  # red
        "#9B5DE5",  # purple
        "#00BBF9",  # cyan
        "#F15BB5",  # pink
        "#00F5D4",  # mint
        "#FFD166",  # yellow
        "#EF476F",  # coral
    ]

    palette = bright_palette[: len(legend_order) - 1] + ["#D3D3D3"]

    # Base chart WITHOUT .configure(...) (important for layering)
    base = (
        alt.Chart(plot_df)
        .encode(
            x=alt.X("energy:Q", title="Energy", scale=alt.Scale(domain=x_domain)),
            y=alt.Y("valence:Q", title="Valence", scale=alt.Scale(domain=y_domain)),
            color=alt.Color(
                "genre_group:N",
                title=f"Genre (Top {topk_genres} + Other)",
                sort=legend_order,
                scale=alt.Scale(
                    domain=legend_order,
                    range=palette,
                ),
                legend=alt.Legend(
                    symbolType="circle",
                    symbolSize=120,
                    orient="right",
                ),
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
    )

    if mode == "brush":
        brush = alt.selection_interval(name=selection_name)

        points_all = (
            base.mark_point(opacity=0.12)
            .encode(
                size=alt.Size(
                    "popularity:Q",
                    title="Popularity",
                    scale=alt.Scale(range=[20, 200]),
                )
            )
            .add_params(brush)
        )

        points_sel = (
            base.transform_filter(brush)
            .mark_point(opacity=0.9)
            .encode(
                size=alt.Size(
                    "popularity:Q",
                    title="Popularity",
                    scale=alt.Scale(range=[30, 240]),
                )
            )
        )


        chart = points_sel + points_all

    elif mode == "pan":
        chart = (
            base.mark_point(opacity=0.8)
            .encode(
                size=alt.Size(
                    "popularity:Q",
                    title="Popularity",
                    scale=alt.Scale(range=[20, 200]),
                )
            )
            .interactive()
        )
    else:
        raise ValueError("mode must be 'brush' or 'pan'")

    # Apply config ONLY on the final chart (safe for LayerChart)
    chart = chart.configure(
        autosize=alt.AutoSizeParams(type="fit", contains="padding")
    )

    meta = {
        "n_total": n_total,
        "n_shown": len(plot_df),
        "sampled": sampled,
        "max_points": max_points,
        "topk_genres": topk_genres,
        "top_genres": list(top),
        "x_domain": x_domain,
        "y_domain": y_domain,
    }
    return chart, meta