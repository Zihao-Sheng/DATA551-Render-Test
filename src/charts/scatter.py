"""Scatter chart builders for energy-valence exploration views."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

BRIGHT_PALETTE = [
    "#1DB954", "#FF7A00", "#4C7DFF", "#E71D36",
    "#9B5DE5", "#00BBF9", "#F15BB5", "#FFD166",
    "#2EC4B6", "#EF476F",
]
OTHER_COLOR = "#d4d4d4"


def _marker_sizes(popularity: pd.Series) -> np.ndarray:
    """Convert popularity scores into marker sizes for scatter bubbles.

    Args:
        popularity: Series of popularity values in the range [0, 100].

    Returns:
        np.ndarray: Bubble sizes scaled for chart readability.
    """
    pop = pd.to_numeric(popularity, errors="coerce").fillna(0).to_numpy(dtype=float)
    pop = np.clip(pop, 0, 100)
    # Similar visual hierarchy to the original chart.
    return 4.0 + (pop / 100.0) * 14.0


def _text_color_for_bg(hex_color: str) -> str:
    """Choose a readable text color based on a background hex color.

    Args:
        hex_color: Background color as a six-digit hex string.

    Returns:
        str: Dark or light text color token for contrast.
    """
    c = str(hex_color or "").lstrip("#")
    if len(c) != 6:
        return "#ffffff"
    try:
        r = int(c[0:2], 16)
        g = int(c[2:4], 16)
        b = int(c[4:6], 16)
    except Exception:
        return "#ffffff"
    # Perceived luminance for contrast.
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    return "#1f2937" if lum > 160 else "#ffffff"


def make_scatter(
    df: pd.DataFrame,
    *,
    mode: str = "brush",
    max_points: int = 2000,
    topk_genres: int = 10,
    selection_name: str = "brush_selection",
    point_selection_name: str = "track_pick",
    width: int | str = 520,
    height: int | str = 380,
):
    """Build an interactive Plotly scatter chart for track selection.

    Args:
        df: Input track rows containing fields used by the scatter view.
        mode: Interaction mode, such as ``brush`` for lasso selection behavior.
        max_points: Maximum number of points to render before deterministic sampling.
        topk_genres: Number of top genres to color separately from ``Other``.
        selection_name: Compatibility parameter retained for legacy callers.
        point_selection_name: Compatibility parameter retained for legacy callers.
        width: Target chart width in pixels.
        height: Target chart height in pixels.

    Returns:
        tuple[go.Figure, dict]: Scatter figure and metadata about rendered points.
    """
    _ = selection_name, point_selection_name  # Kept for API compatibility.
    fixed_width = int(width) if isinstance(width, int) else 520
    fixed_height = int(height) if isinstance(height, int) else 380

    if df is None or len(df) == 0:
        fig = go.Figure()
        fig.update_layout(
            width=fixed_width,
            height=fixed_height,
            autosize=False,
            margin=dict(l=44, r=8, t=8, b=44),
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(family="'Inter', system-ui, -apple-system, Segoe UI, Roboto, Arial", size=10, color="#2f3b57"),
            dragmode="select" if mode == "brush" else "pan",
            clickmode="event",
            xaxis=dict(title="<b>Energy</b>", range=[0, 1], showgrid=False, zeroline=False, constrain="domain"),
            yaxis=dict(
                title="<b>Valence (Mood)</b>",
                range=[0, 1],
                showgrid=False,
                zeroline=False,
                scaleanchor="x",
                scaleratio=1,
                constrain="domain",
            ),
        )
        return fig, {"n_total": 0, "n_shown": 0, "sampled": False, "top_genres": [], "x_domain": [0, 1], "y_domain": [0, 1]}

    # Keep a stable square metric space for Energy/Valence.
    x_domain = [0.0, 1.0]
    y_domain = [0.0, 1.0]

    n_total = len(df)
    sampled = n_total > max_points
    if sampled:
        if "track_id" in df.columns:
            hash_series = pd.util.hash_pandas_object(df["track_id"].astype(str), index=False)
            plot_df = (
                df.assign(_stable_hash=hash_series.values)
                .sort_values("_stable_hash", kind="mergesort")
                .head(max_points)
                .drop(columns=["_stable_hash"])
            )
        else:
            plot_df = df.sample(n=max_points, random_state=42)
    else:
        plot_df = df

    plot_df = plot_df.assign(_row_id=plot_df.index.astype(str))
    top = plot_df["track_genre"].value_counts().head(topk_genres).index
    plot_df = plot_df.assign(
        genre_group=plot_df["track_genre"].where(plot_df["track_genre"].isin(top), "Other")
    )
    legend_order = list(top) + ["Other"]
    palette = BRIGHT_PALETTE[: len(legend_order) - 1] + [OTHER_COLOR]
    color_map = {g: c for g, c in zip(legend_order, palette)}

    fig = go.Figure()
    # Draw "Other" first so gray context points stay underneath colored genres.
    draw_order = (["Other"] if "Other" in legend_order else []) + [g for g in legend_order if g != "Other"]
    for genre in draw_order:
        gdf = plot_df[plot_df["genre_group"] == genre]
        if gdf.empty:
            continue
        customdata = (
            gdf.assign(
                _row_id=gdf["_row_id"].astype(str),
                track_id=gdf["track_id"].astype(str),
                track_name=gdf["track_name"].astype(str),
                artists=gdf["artists"].astype(str),
                track_genre=gdf["track_genre"].astype(str),
                popularity=pd.to_numeric(gdf["popularity"], errors="coerce").fillna(0),
            )[["_row_id", "track_id", "track_name", "artists", "track_genre", "popularity"]]
            .to_numpy(dtype=object)
        )
        hovertemplate = (
            "Track: %{customdata[2]}<br>"
            "Artist: %{customdata[3]}<br>"
            "Genre: %{customdata[4]}<br>"
            "Popularity: %{customdata[5]:.0f}<br>"
            "Energy: %{x:.2f}<br>"
            "Valence: %{y:.2f}<br>"
            "<extra></extra>"
        )
        fig.add_trace(
            go.Scatter(
                x=pd.to_numeric(gdf["energy"], errors="coerce"),
                y=pd.to_numeric(gdf["valence"], errors="coerce"),
                mode="markers",
                name=str(genre),
                customdata=customdata,
                marker=dict(
                    color=color_map.get(genre, OTHER_COLOR),
                    size=_marker_sizes(gdf["popularity"]),
                    opacity=0.76 if genre != "Other" else 0.44,
                    line=dict(width=0),
                ),
                hovertemplate=hovertemplate,
                hoverlabel=dict(
                    bgcolor=color_map.get(genre, OTHER_COLOR),
                    bordercolor=color_map.get(genre, OTHER_COLOR),
                    font=dict(
                        family="'Inter', system-ui, -apple-system, Segoe UI, Roboto, Arial",
                        size=11,
                        color=_text_color_for_bg(color_map.get(genre, OTHER_COLOR)),
                    ),
                ),
                selected=dict(marker=dict(opacity=0.95)),
                unselected=dict(marker=dict(opacity=0.10 if genre != "Other" else 0.08)),
                legendrank=10,
                legend="legend",
            )
        )

    # Bubble-size legend (Popularity) using dummy traces.
    for pop in [0, 20, 40, 60, 80]:
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                name=str(pop),
                marker=dict(
                    size=float(_marker_sizes(pd.Series([pop]))[0]),
                    color="#bfbfbf",
                    line=dict(width=0),
                    opacity=0.95,
                ),
                hoverinfo="skip",
                showlegend=True,
                legendrank=101 + pop,
                legend="legend2",
            )
        )

    fig.update_layout(
        width=fixed_width,
        height=fixed_height,
        autosize=False,
        margin=dict(l=44, r=8, t=8, b=44),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="'Inter', system-ui, -apple-system, Segoe UI, Roboto, Arial", size=10, color="#2f3b57"),
        dragmode="select" if mode == "brush" else "pan",
        clickmode="event",
        hovermode="closest",
        hoverlabel=dict(
            namelength=-1,
            align="left",
        ),
        legend=dict(
            title=dict(text=f"Genre (Top {topk_genres})"),
            orientation="v",
            x=1.02,
            xanchor="left",
            y=1.0,
            yanchor="top",
            bgcolor="rgba(255,255,255,0)",
            font=dict(size=9),
            title_font=dict(size=10),
            itemwidth=30,
            tracegroupgap=2,
            itemsizing="constant",
        ),
        legend2=dict(
            title=dict(text="Popularity"),
            orientation="v",
            x=1.02,
            xanchor="left",
            y=0.38,
            yanchor="top",
            bgcolor="rgba(255,255,255,0)",
            font=dict(size=9),
            title_font=dict(size=10),
            itemwidth=30,
            tracegroupgap=2,
            itemsizing="trace",
        ),
    )
    fig.update_xaxes(
        title="<b>Energy</b>",
        range=x_domain,
        showgrid=False,
        zeroline=False,
        showline=True,
        linecolor="#6b7280",
        linewidth=1,
        ticks="outside",
        constrain="domain",
        tickfont=dict(size=9),
        title_font=dict(size=10),
    )
    fig.update_yaxes(
        title="<b>Valence (Mood)</b>",
        range=y_domain,
        showgrid=False,
        zeroline=False,
        showline=True,
        linecolor="#6b7280",
        linewidth=1,
        ticks="outside",
        scaleanchor="x",
        scaleratio=1,
        constrain="domain",
        tickfont=dict(size=9),
        title_font=dict(size=10),
    )

    meta = {
        "n_total": n_total,
        "n_shown": len(plot_df),
        "sampled": sampled,
        "top_genres": list(top),
        "x_domain": x_domain,
        "y_domain": y_domain,
    }
    return fig, meta
