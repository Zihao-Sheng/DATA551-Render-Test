import altair as alt
import pandas as pd

BRIGHT_PALETTE = [
    "#1DB954", "#FF7A00", "#4C7DFF", "#E71D36",
    "#9B5DE5", "#00BBF9", "#F15BB5", "#FFD166",
    "#2EC4B6", "#EF476F",
]
OTHER_COLOR = "#d4d4d4"


def make_scatter(
    df: pd.DataFrame,
    *,
    mode: str = "brush",
    max_points: int = 2000,
    topk_genres: int = 10,
    selection_name: str = "brush_selection",
    point_selection_name: str = "track_pick",
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
    if sampled:
        # Stable downsampling: pick a deterministic subset by track_id hash
        # so points don't "jump" between callback updates.
        if "track_id" in df.columns:
            work = df.copy()
            hash_series = pd.util.hash_pandas_object(work["track_id"].astype(str), index=False)
            plot_df = (
                work.assign(_stable_hash=hash_series.values)
                .sort_values("_stable_hash", kind="mergesort")
                .head(max_points)
                .drop(columns=["_stable_hash"])
            )
        else:
            plot_df = df.sample(n=max_points, random_state=42)
    else:
        plot_df = df.copy()

    plot_df = plot_df.assign(_row_id=plot_df.index.astype(str))

    top = plot_df["track_genre"].value_counts().head(topk_genres).index
    plot_df = plot_df.assign(
        genre_group=plot_df["track_genre"].where(plot_df["track_genre"].isin(top), "Other")
    )
    legend_order = list(top) + ["Other"]
    palette = BRIGHT_PALETTE[: len(legend_order) - 1] + [OTHER_COLOR]

    base = (
        alt.Chart(plot_df)
        .encode(
            detail=alt.Detail("_row_id:N"),
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
                    symbolOpacity=1,
                    symbolStrokeColor="#ffffff",
                    symbolStrokeWidth=0.6,
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
    point_pick = alt.selection_point(
        name=point_selection_name,
        fields=["_row_id"],
        on="click",
        clear="dblclick",
        empty=False,
    )

    if mode == "brush":
        brush = alt.selection_interval(name=selection_name, empty=True)
        other_layer = (
            base.transform_filter("datum.genre_group === 'Other'")
            .mark_point(filled=True)
            .encode(
                # Keep "Other" as contextual background so it does not overpower highlighted genres.
                opacity=alt.condition(brush, alt.value(0.42), alt.value(0.16)),
                size=size_enc,
            )
        )
        color_layer = (
            base.transform_filter("datum.genre_group !== 'Other'")
            .mark_point(filled=True)
            .encode(
                opacity=alt.condition(brush, alt.value(0.90), alt.value(0.22)),
                size=size_enc,
            )
        )
        chart = alt.layer(other_layer, color_layer).add_params(brush, point_pick)

    else:
        chart = (
            base.mark_point(opacity=0.75, filled=True)
            .encode(
                size=size_enc,
            )
            .add_params(point_pick)
            .interactive()
        )

    autosize_type = "fit" if str(width) == "container" else "pad"
    chart = (
        chart.configure(
            autosize=alt.AutoSizeParams(type=autosize_type, contains="padding")
        )
        .configure_view(stroke=None)
    )

    meta = {
        "n_total": n_total,
        "n_shown": len(plot_df),
        "sampled": sampled,
        "top_genres": list(top),
        "x_domain": x_domain,
        "y_domain": y_domain,
    }
    return chart, meta
