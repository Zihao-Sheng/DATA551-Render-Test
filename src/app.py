import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dash import Dash, html, dcc, Input, Output, State, callback, ctx, no_update, ALL
import pandas as pd
import numpy as np
import dash_vega_components as dvc
import plotly.graph_objects as go

import altair as alt
alt.data_transformers.disable_max_rows()

from charts.scatter import make_scatter, BRIGHT_PALETTE
from charts.genre_bar import make_genre_bar
from charts.distribution import make_distribution
from charts.profile import make_audio_profile
from charts.song_list import make_song_list_table
from filter import filter_tracks

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "raw" / "dataset.csv"
data = pd.read_csv(DATA_PATH)
data["_track_name_lc"] = data["track_name"].astype(str).str.lower()
data["_artists_lc"] = data["artists"].astype(str).str.lower()

AUDIO_FEATURES = [
    "danceability", "energy", "valence",
    "acousticness", "speechiness", "liveness", "instrumentalness",
]
_feat_min = data[AUDIO_FEATURES].min()
_feat_max = data[AUDIO_FEATURES].max()
_feat_rng = (_feat_max - _feat_min).replace(0, 1)
data_norm = (data[AUDIO_FEATURES] - _feat_min) / _feat_rng

TEMPO_MIN, TEMPO_MAX = 0, 250
POP_MIN, POP_MAX = 0, 100
GENRES_BY_POPULARITY = (
    data.groupby("track_genre")["popularity"]
    .mean()
    .sort_values(ascending=False)
    .index
    .tolist()
)
GENRE_OPTIONS = [{"label": g, "value": g} for g in GENRES_BY_POPULARITY]

app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    assets_folder=str(ROOT / "assets"),
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server

GREEN = "#1DB954"
DARK_GREEN = "#168d3e"
TITLE_GREEN = "#169c46"
PAGE = {
    "fontFamily": "'Inter', system-ui, -apple-system, Segoe UI, Roboto, Arial",
    "backgroundColor": "#f0f2f5",
    "minHeight": "100vh",
    "padding": "0",
    "zoom": "1.0",
}
CARD = {
    "backgroundColor": "white",
    "borderRadius": "12px",
    "padding": "12px",
    "boxShadow": "0 1px 6px rgba(0,0,0,0.07)",
    "marginBottom": "10px",
}
SECTION_TITLE = {
    "fontSize": "12px",
    "fontWeight": "700",
    "color": TITLE_GREEN,
    "marginTop": 0,
    "marginBottom": "8px",
    "letterSpacing": "-0.2px",
}
FILTER_LABEL = {
    "fontSize": "9px",
    "fontWeight": "600",
    "color": "#888",
    "textTransform": "uppercase",
    "letterSpacing": "0.7px",
    "marginTop": "10px",
    "marginBottom": "4px",
}
INPUT_STYLE = {
    "width": "100%",
    "padding": "6px 9px",
    "borderRadius": "8px",
    "border": "1px solid #e2e5ea",
    "outline": "none",
    "fontSize": "11px",
    "boxSizing": "border-box",
}
BADGE = {
    "display": "inline-block",
    "padding": "2px 7px",
    "borderRadius": "16px",
    "fontSize": "10px",
    "fontWeight": "600",
    "marginRight": "4px",
}
PROFILE_AXES = ["energy", "valence", "danceability", "acousticness", "speechiness", "liveness"]


def _extract_track_id_from_scatter_signal(signal_data):
    """
    Best-effort parser for Vega selection signal payloads.
    Handles nested dict/list structures produced by point selections.
    """
    if not signal_data:
        return None

    point_payload = signal_data.get("track_pick")
    if point_payload is None:
        for k, v in (signal_data or {}).items():
            if isinstance(k, str) and "track_pick" in k:
                point_payload = v
                break
    if point_payload is None:
        return None

    def _norm(v):
        if isinstance(v, (list, tuple)):
            if not v:
                return None
            v = v[0]
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

    def _from_fields_values(fields, values):
        if not isinstance(fields, list):
            return None
        if not isinstance(values, list):
            return None
        for idx, f in enumerate(fields):
            if isinstance(f, dict) and f.get("field") == "track_id" and idx < len(values):
                return _norm(values[idx])
        return None

    def _walk(node):
        if isinstance(node, dict):
            if "track_id" in node and node["track_id"] is not None:
                return _norm(node["track_id"])

            # Some Vega payloads encode selected rows as a list of dict values.
            values_node = node.get("values")
            if isinstance(values_node, list):
                for item in values_node:
                    if isinstance(item, dict) and item.get("track_id") is not None:
                        return _norm(item.get("track_id"))
                    if isinstance(item, (list, tuple)):
                        for sub in item:
                            found = _walk(sub)
                            if found:
                                return found

            fv = _from_fields_values(node.get("fields"), node.get("values"))
            if fv:
                return fv

            for k in ("vlPoint", "vlMulti", "vlSingle"):
                if k in node:
                    found = _walk(node[k])
                    if found:
                        return found

            for value in node.values():
                found = _walk(value)
                if found:
                    return found
        elif isinstance(node, list):
            for item in node:
                found = _walk(item)
                if found:
                    return found
        return None

    return _walk(point_payload)


def _get_track_row(track_id: str):
    if not track_id:
        return None
    rows = data[data["track_id"].astype(str) == str(track_id)]
    if rows.empty:
        return None
    row = rows.iloc[0].copy()
    for c in ["popularity", "tempo", *PROFILE_AXES]:
        if c in row.index:
            row[c] = pd.to_numeric(row[c], errors="coerce")
    return row


def _get_scatter_genre_color(track_genre: str, filtered_df: pd.DataFrame, *, max_points: int = 500, topk_genres: int = 10):
    if filtered_df is None or len(filtered_df) == 0:
        return "#cccccc"

    # Match scatter sampling logic so profile color aligns with legend colors.
    if len(filtered_df) > max_points:
        if "track_id" in filtered_df.columns:
            work = filtered_df.copy()
            hash_series = pd.util.hash_pandas_object(work["track_id"].astype(str), index=False)
            plot_df = (
                work.assign(_stable_hash=hash_series.values)
                .sort_values("_stable_hash", kind="mergesort")
                .head(max_points)
                .drop(columns=["_stable_hash"])
            )
        else:
            plot_df = filtered_df.sample(n=max_points, random_state=42)
    else:
        plot_df = filtered_df

    top = plot_df["track_genre"].value_counts().head(topk_genres).index.tolist()
    legend_order = top + ["Other"]
    palette = BRIGHT_PALETTE[: len(legend_order) - 1] + ["#cccccc"]
    color_map = {g: c for g, c in zip(legend_order, palette)}
    return color_map.get(track_genre, color_map["Other"])


def _compute_filtered_df(
    keyword,
    genre_values,
    explicit_mode,
    tempo_bounds,
    pop_bounds,
    liked_filter_values=None,
    liked_tracks=None,
):
    explicit_val = {"explicit": True, "clean": False}.get(explicit_mode)
    genre_set = set(genre_values) if genre_values else None
    filtered = filter_tracks(
        data,
        keyword=keyword or None,
        genres=genre_set,
        tempo_range=tempo_bounds,
        popularity_range=pop_bounds,
        explicit=explicit_val,
        copy=False,
    )
    liked_only = bool(liked_filter_values and "liked" in liked_filter_values)
    if not liked_only:
        return filtered

    liked_set = {str(x) for x in (liked_tracks or []) if str(x)}
    if not liked_set or "track_id" not in filtered.columns:
        return filtered.iloc[0:0]
    return filtered[filtered["track_id"].astype(str).isin(liked_set)]


def _compute_selected_df(filtered_df, bounds):
    if not bounds:
        return filtered_df
    e0, e1 = bounds["energy"]
    v0, v1 = bounds["valence"]
    return filtered_df[
        (filtered_df["energy"] >= e0) & (filtered_df["energy"] <= e1) &
        (filtered_df["valence"] >= v0) & (filtered_df["valence"] <= v1)
    ]

app.layout = html.Div(
    className="page",
    style=PAGE,
    children=[
        html.Div(
            className="topbar",
            style={
                "background": f"linear-gradient(135deg, #0d2016 0%, #1a3a22 100%)",
                "padding": "12px 18px",
                "marginBottom": "0",
            },
            children=html.Div(
                className="topbar-inner",
                style={"maxWidth": "1300px", "margin": "0 auto",
                       "display": "flex", "justifyContent": "space-between", "alignItems": "center"},
                children=[
                    html.Div([
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Span(
                                            className="spotify-logo",
                                            children=[
                                                html.Span(className="spotify-wave spotify-wave-1"),
                                                html.Span(className="spotify-wave spotify-wave-2"),
                                                html.Span(className="spotify-wave spotify-wave-3"),
                                            ],
                                        ),
                                        html.Span(
                                            "Spotify Track Insights Explorer",
                                            style={"fontSize": "16px", "fontWeight": "700", "color": "white", "letterSpacing": "-0.2px"},
                                        ),
                                    ],
                                    style={"display": "flex", "alignItems": "center", "gap": "8px"},
                                ),
                            ]
                        ),
                        html.Div(
                            "Explore audio features, genres, and popularity across 114k+ tracks",
                            style={"fontSize": "10px", "color": "#8fba9a", "marginTop": "2px"},
                        ),
                    ]),
                    html.Div(
                        id="header-stats",
                        className="header-stats",
                        style={"display": "flex", "gap": "8px", "alignItems": "center", "flexWrap": "wrap"},
                    ),
                ],
            ),
        ),

        html.Div(
            id="layout-grid",
            className="layout-grid",
            style={
                "maxWidth": "1300px",
                "margin": "0 auto",
                "display": "grid",
                "alignItems": "start",
            },
            children=[

                html.Div(
                    id="left-panel",
                    className="left-panel",
                    style={**CARD, "marginBottom": 0},
                    children=[
                        html.Div("Filters", style={**SECTION_TITLE, "color": TITLE_GREEN}),

                        html.Div("Search Tracks", style=FILTER_LABEL),
                        dcc.Input(
                            id="keyword",
                            type="text",
                            placeholder="Track name or artist…",
                            debounce=True,
                            style=INPUT_STYLE,
                        ),

                        html.Div("Genre", style=FILTER_LABEL),
                        dcc.Dropdown(
                            id="genre-picker",
                            options=GENRE_OPTIONS,
                            value=None,
                            placeholder="Search & add a genre…",
                            clearable=True,
                            searchable=True,
                            style={"fontSize": "11px"},
                        ),
                        html.Div(
                            id="selected-genres-box",
                            style={
                                "marginTop": "6px",
                                "padding": "6px",
                                "border": "1px solid #e2e5ea",
                                "borderRadius": "10px",
                                "backgroundColor": "#fbfcfd",
                                "minHeight": "46px",
                            },
                        ),

                        html.Div("Explicit Content", style=FILTER_LABEL),
                        dcc.RadioItems(
                            id="explicit",
                            options=[
                                {"label": " All Tracks", "value": "all"},
                                {"label": " Explicit only", "value": "explicit"},
                                {"label": " Clean only", "value": "clean"},
                            ],
                            value="all",
                            style={"rowGap": "5px", "display": "grid"},
                            labelStyle={"display": "flex", "alignItems": "center", "gap": "7px", "fontSize": "12px"},
                            inputStyle={"accentColor": GREEN},
                        ),

                        html.Div("Liked", style=FILTER_LABEL),
                        dcc.Checklist(
                            id="liked-only",
                            options=[{"label": " Liked only", "value": "liked"}],
                            value=[],
                            style={"rowGap": "5px", "display": "grid"},
                            labelStyle={"display": "flex", "alignItems": "center", "gap": "7px", "fontSize": "12px"},
                            inputStyle={"accentColor": GREEN},
                        ),

                        html.Div("Tempo (BPM)", style=FILTER_LABEL),
                        dcc.RangeSlider(
                            id="tempo-range",
                            min=TEMPO_MIN, max=TEMPO_MAX, step=5,
                            value=[TEMPO_MIN, TEMPO_MAX],
                            marks={0: "0", 100: "100", 200: "200", 250: "250"},
                            tooltip={"placement": "bottom", "always_visible": False},
                        ),

                        html.Div("Popularity", style=FILTER_LABEL),
                        dcc.RangeSlider(
                            id="popularity-range",
                            min=POP_MIN, max=POP_MAX, step=5,
                            value=[POP_MIN, POP_MAX],
                            marks={0: "0", 50: "50", 100: "100"},
                            tooltip={"placement": "bottom", "always_visible": False},
                        ),

                        html.Div(
                            id="filter-hint",
                            style={"fontSize": "11px", "color": "#888", "marginTop": "12px",
                                   "padding": "8px 10px", "backgroundColor": "#f8f9fa",
                                   "borderRadius": "10px", "lineHeight": "1.6"},
                        ),
                    ],
                ),

                html.Div(
                    id="main-panel",
                    className="main-panel",
                    style={"minWidth": 0},
                    children=[
                        html.Div(
                            style=CARD,
                            children=[
                                html.Div(
                                    style={"display": "flex", "justifyContent": "space-between", "alignItems": "flex-start"},
                                    children=[
                                        html.Div([
                                            html.H4("Energy vs Valence", style=SECTION_TITLE),
                                            html.Div(id="scatter-meta", style={"fontSize": "10px", "color": "#888", "marginBottom": "5px"}),
                                        ]),
                                        dcc.RadioItems(
                                            id="toolbox-mode",
                                            options=[
                                                {"label": " Brush", "value": "brush"},
                                                {"label": " Pan/Zoom", "value": "pan"},
                                            ],
                                            value="brush",
                                            inline=True,
                                            style={"fontSize": "10px", "color": "#555"},
                                            labelStyle={"marginLeft": "10px", "cursor": "pointer"},
                                            inputStyle={"accentColor": GREEN},
                                        ),
                                    ],
                                ),
                                dvc.Vega(
                                    id="scatter",
                                    spec={},
                                    opt={"renderer": "svg", "actions": False},
                                    signalsToObserve=["brush_selection", "track_pick"],
                                    style={"width": "100%"},
                                ),
                            ],
                        ),

                        html.Div(
                            className="two-up",
                            children=[
                                html.Div(
                                    style={**CARD, "marginBottom": 0, "minWidth": 0},
                                    children=[
                                        html.H4("Top Genres by Popularity", style=SECTION_TITLE),
                                        html.Div(
                                            style={"fontSize": "9px", "color": "#888", "marginBottom": "7px"},
                                            children="Average popularity by genre, colored by mean energy.",
                                        ),
                                        dvc.Vega(
                                            id="genre-bar",
                                            spec={},
                                            opt={"renderer": "svg", "actions": False},
                                            style={"width": "100%", "maxWidth": "100%", "minWidth": 0, "overflow": "hidden"},
                                        ),
                                    ],
                                ),
                                html.Div(
                                    style={**CARD, "marginBottom": 0, "minWidth": 0},
                                    children=[
                                        html.H4("Avg Audio Profile", style=SECTION_TITLE),
                                        html.Div(
                                            style={"fontSize": "9px", "color": "#888", "marginBottom": "7px"},
                                            children="Mean values for selected / filtered tracks.",
                                        ),
                                        dvc.Vega(
                                            id="audio-profile",
                                            spec={},
                                            opt={"renderer": "svg", "actions": False},
                                            style={"width": "100%", "maxWidth": "100%", "minWidth": 0, "overflow": "hidden"},
                                        ),
                                    ],
                                ),
                            ],
                        ),

                        html.Div(
                            style=CARD,
                            children=[
                                html.H4("Feature Density — Selected Tracks", style=SECTION_TITLE),
                                html.Div(
                                    style={"fontSize": "9px", "color": "#888", "marginBottom": "7px"},
                                    children="Distribution of key audio features for the current selection.",
                                ),
                                dvc.Vega(
                                    id="distribution",
                                    spec={},
                                    opt={"renderer": "svg", "actions": False},
                                    style={"width": "100%"},
                                ),
                            ],
                        ),

                    ],
                ),

                html.Div(
                    id="right-panel",
                    className="right-panel",
                    style={"minWidth": 0},
                    children=[
                        html.Div(
                            id="track-profile-card",
                            style={**CARD, "marginBottom": 0, "overflow": "visible"},
                            children=[
                                html.H4("Track Profile", style=SECTION_TITLE),
                                html.Div(
                                    "Click a song from scatter / similar list / table to view its profile.",
                                    style={"fontSize": "9px", "color": "#888", "marginBottom": "7px", "lineHeight": "1.4"},
                                ),
                                html.Div(id="song-profile-container"),
                            ],
                        ),
                        html.Div(
                            id="similar-tracks-card",
                            style={**CARD, "marginBottom": 0, "display": "flex", "flexDirection": "column", "minHeight": 0},
                            children=[
                                html.H4("Discover Similar Tracks", style=SECTION_TITLE),
                                html.Div(
                                    "Pick a popular track from your selection — we'll find "
                                    "audio-similar but less-discovered songs.",
                                    style={"fontSize": "9px", "color": "#888", "marginBottom": "7px", "lineHeight": "1.4"},
                                ),
                                dcc.Dropdown(
                                    id="similar-track-dropdown",
                                    placeholder="Select a reference track…",
                                    options=[],
                                    value=None,
                                    clearable=True,
                                    style={"fontSize": "10px", "marginBottom": "8px"},
                                ),
                                html.Div(id="similar-tracks-container", style={"flex": "1 1 auto", "minHeight": 0, "overflowY": "auto", "overflowX": "hidden", "paddingRight": "2px"}),
                            ],
                        ),
                    ],
                ),

                html.Div(
                    className="bottom-panel",
                    style={**CARD, "minWidth": 0, "marginBottom": 0},
                    children=[
                        html.H4("Track List", style=SECTION_TITLE),
                        html.Div(
                            "Click the star before Title to like/unlike a track.",
                            style={"fontSize": "9px", "color": "#888", "marginBottom": "5px"},
                        ),
                        html.Div(
                            id="song-list-container",
                            children=make_song_list_table(data.head(0), max_rows=0, liked_track_ids=[]),
                        ),
                    ],
                ),
            ],
        ),

        dcc.Store(id="brush-bounds-store"),
        dcc.Store(id="selected-genres-store", data=[]),
        dcc.Store(id="liked-tracks-store", data=[], storage_type="local"),
        dcc.Store(id="selected-track-store", data=None),
    ],
)


@callback(
    Output("selected-genres-store", "data"),
    Output("genre-picker", "value"),
    Input("genre-picker", "value"),
    Input({"type": "genre-remove", "genre": ALL}, "n_clicks"),
    State("selected-genres-store", "data"),
    prevent_initial_call=True,
)
def update_selected_genres_store(picked_genre, _remove_clicks, current_selected):
    selected = list(current_selected or [])
    triggered = ctx.triggered_id

    if isinstance(triggered, dict) and triggered.get("type") == "genre-remove":
        genre = triggered.get("genre")
        selected = [g for g in selected if g != genre]
        return selected, None

    if triggered == "genre-picker" and picked_genre:
        if picked_genre not in selected:
            selected.append(picked_genre)

    return selected, None


@callback(
    Output("selected-genres-box", "children"),
    Input("selected-genres-store", "data"),
)
def render_selected_genres_box(selected_genres):
    selected = list(selected_genres or [])
    if not selected:
        return html.Div("No genres selected.", style={"fontSize": "12px", "color": "#9aa1ab"})

    chips = []
    for g in selected:
        chips.append(
            html.Div(
                style={
                    "display": "inline-flex",
                    "alignItems": "center",
                    "gap": "6px",
                    "padding": "4px 8px",
                    "borderRadius": "14px",
                    "border": "1px solid #d9e9df",
                    "backgroundColor": "#eef8f1",
                    "color": "#2d6a4f",
                    "fontSize": "12px",
                    "fontWeight": "600",
                },
                children=[
                    html.Span(g),
                    html.Button(
                        "×",
                        id={"type": "genre-remove", "genre": g},
                        n_clicks=0,
                        style={
                            "border": "none",
                            "background": "transparent",
                            "color": "#2d6a4f",
                            "cursor": "pointer",
                            "fontSize": "13px",
                            "lineHeight": "1",
                            "padding": "0 2px",
                        },
                    ),
                ],
            )
        )

    return html.Div(
        chips,
        style={"display": "flex", "flexWrap": "wrap", "gap": "6px"},
    )


@callback(
    Output("scatter", "spec"),
    Output("scatter-meta", "children"),
    Output("header-stats", "children"),
    Output("filter-hint", "children"),
    Output("brush-bounds-store", "data"),
    Input("toolbox-mode", "value"),
    Input("keyword", "value"),
    Input("selected-genres-store", "data"),
    Input("explicit", "value"),
    Input("liked-only", "value"),
    Input("tempo-range", "value"),
    Input("popularity-range", "value"),
    Input("liked-tracks-store", "data"),
    Input("scatter", "signalData"),
    State("brush-bounds-store", "data"),
)
def update_scatter_and_stores(
    mode,
    keyword,
    genre_values,
    explicit_mode,
    liked_filter_values,
    tempo_bounds,
    pop_bounds,
    liked_tracks,
    signal_data,
    previous_bounds,
):
    triggered = ctx.triggered_id

    # Perf guard: point-click only updates Track Profile via another callback.
    # Skip expensive filter/chart work when scatter event has no brush payload.
    if triggered == "scatter":
        payload = signal_data or {}
        brush_payload = payload.get("brush_selection")
        point_payload = payload.get("track_pick")
        if point_payload is None:
            for k, v in payload.items():
                if isinstance(k, str) and "track_pick" in k:
                    point_payload = v
                    break
        # Only short-circuit on pure point-pick events.
        # Keep initial render and brush interactions intact.
        if (point_payload is not None) and (not brush_payload):
            return no_update, no_update, no_update, no_update, previous_bounds

    filtered_df = _compute_filtered_df(
        keyword,
        genre_values,
        explicit_mode,
        tempo_bounds,
        pop_bounds,
        liked_filter_values,
        liked_tracks,
    )

    brush = (signal_data or {}).get("brush_selection")
    if brush and "energy" in brush and "valence" in brush:
        e0, e1 = brush["energy"]
        v0, v1 = brush["valence"]
        bounds = {"energy": [e0, e1], "valence": [v0, v1]}
        selected_df = _compute_selected_df(filtered_df, bounds)
    elif triggered == "scatter" and previous_bounds:
        bounds = previous_bounds
        selected_df = _compute_selected_df(filtered_df, bounds)
    else:
        bounds = None
        selected_df = filtered_df

    n_total = len(data)
    n_filtered = len(filtered_df)
    n_selected = len(selected_df)

    stats_children = [
        html.Span(f"Total  {n_total:,}", style={**BADGE, "backgroundColor": "#e8f5e9", "color": "#2d6a4f"}),
        html.Span(f"Filtered  {n_filtered:,}", style={**BADGE, "backgroundColor": "#fff3e0", "color": "#a0522d"}),
        html.Span(f"Selected  {n_selected:,}", style={**BADGE, "backgroundColor": "#e3f2fd", "color": "#1565c0"}),
    ]

    filter_hint = [
        html.Div(f"{n_filtered:,} tracks after filters", style={"marginBottom": "2px"}),
        html.Div(f"{n_selected:,} tracks selected" + (" (brush active)" if bounds else ""), style={"color": GREEN if bounds else "#888"}),
    ]

    n_shown = min(n_filtered, 500)
    sampled = n_filtered > 500
    meta_text = (
        f"Showing {n_shown:,}" + (" sampled" if sampled else "") +
        f" of {n_filtered:,} filtered · " +
        ("Brush to select a region" if mode == "brush" else "Pan & zoom enabled")
    )

    if triggered == "scatter" and signal_data:
        spec_out = no_update
    else:
        chart, _ = make_scatter(
            filtered_df,
            mode=mode,
            max_points=500,
            topk_genres=10,
            selection_name="brush_selection",
            point_selection_name="track_pick",
            width=320,
            height=320,
        )
        spec_out = chart.to_dict()
        bounds = None
        selected_df = filtered_df

    return spec_out, meta_text, stats_children, filter_hint, bounds


@callback(
    Output("genre-bar", "spec"),
    Input("keyword", "value"),
    Input("selected-genres-store", "data"),
    Input("explicit", "value"),
    Input("liked-only", "value"),
    Input("tempo-range", "value"),
    Input("popularity-range", "value"),
    Input("brush-bounds-store", "data"),
    Input("liked-tracks-store", "data"),
)
def update_genre_bar(keyword, genre_values, explicit_mode, liked_filter_values, tempo_bounds, pop_bounds, bounds, liked_tracks):
    filtered_df = _compute_filtered_df(
        keyword,
        genre_values,
        explicit_mode,
        tempo_bounds,
        pop_bounds,
        liked_filter_values,
        liked_tracks,
    )
    df = _compute_selected_df(filtered_df, bounds)
    chart = make_genre_bar(df, top_n=10, width="container", height=220)
    return chart.to_dict()


@callback(
    Output("distribution", "spec"),
    Input("keyword", "value"),
    Input("selected-genres-store", "data"),
    Input("explicit", "value"),
    Input("liked-only", "value"),
    Input("tempo-range", "value"),
    Input("popularity-range", "value"),
    Input("brush-bounds-store", "data"),
    Input("liked-tracks-store", "data"),
)
def update_distribution(keyword, genre_values, explicit_mode, liked_filter_values, tempo_bounds, pop_bounds, bounds, liked_tracks):
    filtered_df = _compute_filtered_df(
        keyword,
        genre_values,
        explicit_mode,
        tempo_bounds,
        pop_bounds,
        liked_filter_values,
        liked_tracks,
    )
    df = _compute_selected_df(filtered_df, bounds)
    chart = make_distribution(df, max_points=2000, width=360, height=160)
    return chart.to_dict()


@callback(
    Output("audio-profile", "spec"),
    Input("keyword", "value"),
    Input("selected-genres-store", "data"),
    Input("explicit", "value"),
    Input("liked-only", "value"),
    Input("tempo-range", "value"),
    Input("popularity-range", "value"),
    Input("brush-bounds-store", "data"),
    Input("liked-tracks-store", "data"),
)
def update_audio_profile(keyword, genre_values, explicit_mode, liked_filter_values, tempo_bounds, pop_bounds, bounds, liked_tracks):
    filtered_df = _compute_filtered_df(
        keyword,
        genre_values,
        explicit_mode,
        tempo_bounds,
        pop_bounds,
        liked_filter_values,
        liked_tracks,
    )
    df = _compute_selected_df(filtered_df, bounds)
    chart = make_audio_profile(df, width="container", height=235)
    return chart.to_dict()


@callback(
    Output("song-list-container", "children"),
    Input("keyword", "value"),
    Input("selected-genres-store", "data"),
    Input("explicit", "value"),
    Input("liked-only", "value"),
    Input("tempo-range", "value"),
    Input("popularity-range", "value"),
    Input("brush-bounds-store", "data"),
    Input("liked-tracks-store", "data"),
)
def update_song_list(keyword, genre_values, explicit_mode, liked_filter_values, tempo_bounds, pop_bounds, bounds, liked_tracks):
    filtered_df = _compute_filtered_df(
        keyword,
        genre_values,
        explicit_mode,
        tempo_bounds,
        pop_bounds,
        liked_filter_values,
        liked_tracks,
    )
    df = _compute_selected_df(filtered_df, bounds)
    if df is None or len(df) == 0:
        return html.Div(
            "No tracks match your filters.",
            style={"fontSize": "13px", "color": "#888", "padding": "16px 0"},
        )
    return make_song_list_table(df, max_rows=5000, liked_track_ids=liked_tracks)


@callback(
    Output("liked-tracks-store", "data"),
    Input("song-table", "active_cell"),
    Input({"type": "similar-like", "track_id": ALL}, "n_clicks"),
    Input({"type": "profile-like", "track_id": ALL}, "n_clicks"),
    State("song-table", "derived_viewport_data"),
    State("song-table", "data"),
    State("liked-tracks-store", "data"),
    prevent_initial_call=True,
)
def toggle_liked_tracks(active_cell, _similar_like_clicks, _profile_like_clicks, viewport_data, table_data, liked_tracks):
    liked = [str(x) for x in (liked_tracks or [])]
    triggered = ctx.triggered_id

    track_id = None
    if isinstance(triggered, dict) and triggered.get("type") in {"similar-like", "profile-like"}:
        triggered_value = (ctx.triggered[0] or {}).get("value") if ctx.triggered else None
        if triggered_value in (None, 0):
            return no_update
        track_id = str(triggered.get("track_id", "")).strip()
    elif triggered == "song-table":
        if not active_cell or active_cell.get("column_id") != "liked":
            return no_update
        row_idx = active_cell.get("row")
        visible_rows = viewport_data or table_data or []
        if row_idx is None or row_idx < 0 or row_idx >= len(visible_rows):
            return no_update
        track_id = str(visible_rows[row_idx].get("track_id", "")).strip()

    if not track_id:
        return no_update

    if track_id in liked:
        liked = [x for x in liked if x != track_id]
    else:
        liked.append(track_id)
    return liked


@callback(
    Output("selected-track-store", "data"),
    Input("scatter", "signalData"),
    Input("song-table", "active_cell"),
    Input({"type": "similar-open", "track_id": ALL}, "n_clicks"),
    State("song-table", "derived_viewport_data"),
    State("song-table", "data"),
    State("selected-track-store", "data"),
    prevent_initial_call=True,
)
def update_selected_track(signal_data, active_cell, _similar_open_clicks, viewport_data, table_data, current_selected):
    triggered = ctx.triggered_id
    track_id = None
    source = None

    if isinstance(triggered, dict) and triggered.get("type") == "similar-open":
        triggered_value = (ctx.triggered[0] or {}).get("value") if ctx.triggered else None
        if triggered_value in (None, 0):
            return no_update
        track_id = str(triggered.get("track_id", "")).strip()
        source = "similar-card"
    elif triggered == "song-table":
        if active_cell:
            row_idx = active_cell.get("row")
            visible_rows = viewport_data or table_data or []
            if row_idx is not None and 0 <= row_idx < len(visible_rows):
                track_id = str(visible_rows[row_idx].get("track_id", "")).strip()
                source = "song-table"
    elif triggered == "scatter":
        track_id = _extract_track_id_from_scatter_signal(signal_data)
        source = "scatter"

    if not track_id:
        return no_update
    if current_selected and str(current_selected.get("track_id")) == track_id:
        return no_update
    return {"track_id": track_id, "source": source}


@callback(
    Output("song-profile-container", "children"),
    Input("selected-track-store", "data"),
    Input("liked-tracks-store", "data"),
    Input("keyword", "value"),
    Input("selected-genres-store", "data"),
    Input("explicit", "value"),
    Input("liked-only", "value"),
    Input("tempo-range", "value"),
    Input("popularity-range", "value"),
)
def render_song_profile(
    selected_track,
    liked_tracks,
    keyword,
    genre_values,
    explicit_mode,
    liked_filter_values,
    tempo_bounds,
    pop_bounds,
):
    track_id = str((selected_track or {}).get("track_id", "")).strip()
    if not track_id:
        return html.Div("No song selected yet.", style={"fontSize": "12px", "color": "#9aa1ab"})

    row = _get_track_row(track_id)
    if row is None:
        return html.Div("Track not found in dataset.", style={"fontSize": "12px", "color": "#c00"})

    liked_set = {str(x) for x in (liked_tracks or [])}
    is_liked = track_id in liked_set
    filtered_df = _compute_filtered_df(
        keyword,
        genre_values,
        explicit_mode,
        tempo_bounds,
        pop_bounds,
        liked_filter_values,
        liked_tracks,
    )
    genre_color = _get_scatter_genre_color(str(row.get("track_genre", "")), filtered_df)

    theta = ["Energy", "Valence", "Dance", "Acoustic", "Speech", "Live"]
    values = [float(row.get(c, 0) if pd.notna(row.get(c, np.nan)) else 0.0) for c in PROFILE_AXES]
    fig = go.Figure(
        data=[
            go.Scatterpolar(
                r=values + [values[0]],
                theta=theta + [theta[0]],
                fill="toself",
                line=dict(color=genre_color, width=2),
                fillcolor=genre_color,
                opacity=0.35,
                hovertemplate="%{theta}: %{r:.2f}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        margin=dict(l=32, r=24, t=2, b=2),
        showlegend=False,
        paper_bgcolor="white",
        polar=dict(
            bgcolor="white",
            radialaxis=dict(visible=True, range=[0, 1], tickfont=dict(size=7), gridcolor="#e6ebf2"),
            angularaxis=dict(tickfont=dict(size=7)),
        ),
    )

    pop = int(row["popularity"]) if pd.notna(row.get("popularity", np.nan)) else 0
    tempo = int(row["tempo"]) if pd.notna(row.get("tempo", np.nan)) else 0
    explicit_text = "Explicit" if bool(row.get("explicit", False)) else "Clean"

    return html.Div(
        [
            html.Div(
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "flex-start", "gap": "8px"},
                children=[
                    html.Div(
                        [
                            html.Div(str(row.get("track_name", "Unknown")), style={"fontSize": "15px", "fontWeight": "700", "color": "#1a1a2e"}),
                            html.Div(
                                f"{row.get('artists', 'Unknown')}  ·  {row.get('track_genre', 'Unknown')}",
                                style={"fontSize": "11px", "color": "#6b7280", "marginTop": "1px"},
                            ),
                        ],
                        style={"minWidth": 0},
                    ),
                    html.Div(
                        [
                            html.Button(
                                "Show Similar Tracks",
                                id="profile-show-similar-btn",
                                n_clicks=0,
                                style={
                                    "width": "fit-content",
                                    "minWidth": "0",
                                    "border": "1px solid #dbe5df",
                                    "backgroundColor": "#f6fbf8",
                                    "color": "#2d6a4f",
                                    "fontSize": "10px",
                                    "fontWeight": "600",
                                    "padding": "4px 7px",
                                    "borderRadius": "8px",
                                    "cursor": "pointer",
                                    "whiteSpace": "nowrap",
                                    "flex": "0 0 auto",
                                },
                            ),
                            html.Button(
                                "★" if is_liked else "☆",
                                id={"type": "profile-like", "track_id": track_id},
                                n_clicks=0,
                                title="Like this track",
                                style={
                                    "border": "none",
                                    "background": "transparent",
                                    "cursor": "pointer",
                                    "fontSize": "20px",
                                    "lineHeight": "1",
                                    "padding": 0,
                                    "color": "#f4b400" if is_liked else "#bcc3cc",
                                },
                            ),
                        ],
                        style={"display": "flex", "alignItems": "center", "gap": "8px", "flex": "0 0 auto"},
                    ),
                ],
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Span(f"Pop {pop}", style={**BADGE, "backgroundColor": "#e8f5e9", "color": "#2d6a4f", "fontSize": "10px"}),
                                    html.Span(f"Tempo {tempo}", style={**BADGE, "backgroundColor": "#e7f0ff", "color": "#1d4ed8", "fontSize": "10px"}),
                                    html.Span(explicit_text, style={**BADGE, "backgroundColor": "#fff4e6", "color": "#9a3412", "fontSize": "10px"}),
                                ],
                                style={"display": "flex", "flexDirection": "column", "alignItems": "flex-start", "gap": "5px", "minWidth": 0},
                            ),
                        ],
                        style={
                            "display": "flex",
                            "flexDirection": "column",
                            "alignItems": "flex-start",
                            "justifyContent": "center",
                            "gap": "5px",
                            "minWidth": 0,
                            "flex": "0 0 28%",
                        },
                    ),
                    dcc.Graph(
                        figure=fig,
                        config={"displayModeBar": False, "staticPlot": True},
                        style={"height": "148px", "width": "72%", "minWidth": "220px", "marginLeft": "-8px"},
                    ),
                ],
                style={"display": "flex", "flexWrap": "nowrap", "alignItems": "center", "gap": "2px"},
            ),
        ],
        style={"display": "grid", "rowGap": "4px"},
    )


@callback(
    Output("similar-track-dropdown", "value", allow_duplicate=True),
    Input("profile-show-similar-btn", "n_clicks"),
    State("selected-track-store", "data"),
    prevent_initial_call=True,
)
def push_profile_track_to_similar(_clicks, selected_track):
    if _clicks in (None, 0):
        return no_update
    track_id = str((selected_track or {}).get("track_id", "")).strip()
    source = str((selected_track or {}).get("source", "")).strip()
    if source == "song-table":
        return no_update
    if not track_id:
        return no_update
    return track_id


@callback(
    Output("song-table", "selected_cells"),
    Input("song-table", "active_cell"),
    State("song-table", "columns"),
    prevent_initial_call=True,
)
def highlight_song_table_row(active_cell, columns):
    if not active_cell:
        return no_update
    row = active_cell.get("row")
    if row is None:
        return no_update
    visible_cols = [col for col in (columns or []) if col.get("id") != "track_id"]
    return [
        {"row": row, "column": idx, "column_id": col["id"]}
        for idx, col in enumerate(visible_cols)
    ]


@callback(
    Output("similar-track-dropdown", "options"),
    Output("similar-track-dropdown", "value"),
    Input("keyword", "value"),
    Input("selected-genres-store", "data"),
    Input("explicit", "value"),
    Input("liked-only", "value"),
    Input("tempo-range", "value"),
    Input("popularity-range", "value"),
    Input("brush-bounds-store", "data"),
    Input("liked-tracks-store", "data"),
    Input("similar-track-dropdown", "search_value"),
    State("similar-track-dropdown", "value"),
)
def update_similar_dropdown(keyword, genre_values, explicit_mode, liked_filter_values, tempo_bounds, pop_bounds, bounds, liked_tracks, search_value, current_value):
    filtered_df = _compute_filtered_df(
        keyword,
        genre_values,
        explicit_mode,
        tempo_bounds,
        pop_bounds,
        liked_filter_values,
        liked_tracks,
    )
    selected_df = _compute_selected_df(filtered_df, bounds)
    current_value_str = str(current_value) if current_value is not None else None
    if selected_df is None or len(selected_df) == 0:
        return [], current_value_str

    df = selected_df
    needed = ["track_id", "track_name", "artists", "popularity"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        return [], current_value_str

    base = df[needed].drop_duplicates("track_id")
    base["track_id"] = base["track_id"].astype(str)
    base["popularity"] = pd.to_numeric(base["popularity"], errors="coerce").fillna(0)

    # Default: show top-30 popular tracks.
    # When user types search, filter across the full selected set.
    if search_value and str(search_value).strip():
        q = str(search_value).strip().lower()
        mask = (
            base["track_name"].astype(str).str.lower().str.contains(q, na=False) |
            base["artists"].astype(str).str.lower().str.contains(q, na=False)
        )
        options_df = base[mask].nlargest(100, "popularity")
    else:
        options_df = base.nlargest(30, "popularity")

    # Keep currently selected value in dropdown options, even if not in top-30.
    if current_value_str is not None and (options_df["track_id"] == current_value_str).sum() == 0:
        keep = base[base["track_id"] == current_value_str]
        if not keep.empty:
            options_df = pd.concat([options_df, keep]).drop_duplicates("track_id", keep="first")

    options = [
        {
            "label": f"{row.track_name}  —  {row.artists}  (pop {int(row.popularity)})",
            "value": row.track_id,
        }
        for row in options_df.itertuples()
    ]
    # Keep dropdown value stable; similar list should only refresh when user
    # explicitly changes dropdown (or button sets it).
    next_value = current_value_str
    return options, next_value


@callback(
    Output("similar-tracks-container", "children"),
    Input("similar-track-dropdown", "value"),
    State("keyword", "value"),
    State("selected-genres-store", "data"),
    State("explicit", "value"),
    State("liked-only", "value"),
    State("tempo-range", "value"),
    State("popularity-range", "value"),
    State("brush-bounds-store", "data"),
    State("liked-tracks-store", "data"),
)
def update_similar_tracks(track_id, keyword, genre_values, explicit_mode, liked_filter_values, tempo_bounds, pop_bounds, bounds, liked_tracks):
    if not track_id:
        return html.Div(
            "Select a track above to discover audio-similar but underrated songs.",
            style={"fontSize": "12px", "color": "#aaa", "padding": "8px 0", "lineHeight": "1.5"},
        )

    filtered_df = _compute_filtered_df(
        keyword,
        genre_values,
        explicit_mode,
        tempo_bounds,
        pop_bounds,
        liked_filter_values,
        liked_tracks,
    )
    selected_df = _compute_selected_df(filtered_df, bounds)
    pool = selected_df if selected_df is not None and len(selected_df) > 0 else filtered_df
    required = ["track_id", "track_name", "artists", "track_genre", "popularity", *AUDIO_FEATURES]
    missing = [c for c in required if c not in pool.columns]
    if missing:
        return html.Div("Selected data missing required columns.", style={"fontSize": "12px", "color": "#c00"})

    track_id_str = str(track_id)
    matches = pool[pool["track_id"].astype(str) == track_id_str]
    if matches.empty:
        # Fallback for edge cases where selected set changed after choosing a track
        matches = data[data["track_id"].astype(str) == track_id_str]
    if matches.empty:
        return html.Div("Track not found.", style={"fontSize": "12px", "color": "#c00"})

    ref = matches.iloc[0]

    work = pool[required].copy()
    work["track_id"] = work["track_id"].astype(str)
    for c in ["popularity", *AUDIO_FEATURES]:
        work[c] = pd.to_numeric(work[c], errors="coerce")
    work = work.dropna(subset=["track_id", "popularity", *AUDIO_FEATURES]).drop_duplicates("track_id")

    ref_rows = work[work["track_id"] == track_id_str]
    if ref_rows.empty:
        return html.Div("Reference track is not in current selection.", style={"fontSize": "12px", "color": "#c00"})

    ref_pop = int(ref_rows.iloc[0]["popularity"])
    ref_norm = ((ref_rows.iloc[0][AUDIO_FEATURES] - _feat_min) / _feat_rng).to_numpy(dtype=float)
    work_norm = ((work[AUDIO_FEATURES] - _feat_min) / _feat_rng).to_numpy(dtype=float)
    dists = np.linalg.norm(work_norm - ref_norm, axis=1)

    candidates = work.copy()
    candidates["_dist"] = dists
    candidates = (
        candidates[
            (candidates["track_id"] != track_id_str) &
            (candidates["popularity"] < ref_pop)
        ]
        .nsmallest(10, "_dist")
        [["track_id", "track_name", "artists", "track_genre", "popularity", "energy", "valence", "danceability"]]
    )

    if candidates.empty:
        return html.Div("No similar lower-popularity tracks found.", style={"fontSize": "12px", "color": "#888"})

    candidates = candidates.copy()
    liked_set = {str(x) for x in (liked_tracks or [])}
    for col in ["energy", "valence", "danceability"]:
        candidates[col] = candidates[col].round(2)

    rows = []
    for _, row in candidates.iterrows():
        cand_id = str(row["track_id"])
        is_liked = cand_id in liked_set
        rows.append(
            html.Div(
                style={
                    "padding": "9px 10px",
                    "borderBottom": "1px solid #f0f2f5",
                    "fontSize": "12px",
                },
                children=[
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "gap": "10px"},
                        children=[
                            html.Button(
                                row["track_name"],
                                id={"type": "similar-open", "track_id": cand_id},
                                n_clicks=0,
                                style={
                                    "fontWeight": "600",
                                    "color": "#1a1a2e",
                                    "overflow": "hidden",
                                    "textOverflow": "ellipsis",
                                    "whiteSpace": "nowrap",
                                    "flex": "1",
                                    "textAlign": "left",
                                    "background": "transparent",
                                    "border": "none",
                                    "padding": 0,
                                    "cursor": "pointer",
                                },
                            ),
                            html.Button(
                                "★" if is_liked else "☆",
                                id={"type": "similar-like", "track_id": cand_id},
                                n_clicks=0,
                                title="Like this track",
                                style={
                                    "border": "none",
                                    "background": "transparent",
                                    "cursor": "pointer",
                                    "fontSize": "18px",
                                    "lineHeight": "1",
                                    "padding": "0 2px",
                                    "color": "#f4b400" if is_liked else "#bcc3cc",
                                },
                            ),
                        ],
                    ),
                    html.Div(
                        f"{row['artists']}  ·  {row['track_genre']}",
                        style={"color": "#888", "fontSize": "11px", "marginTop": "1px"},
                    ),
                    html.Div(
                        [
                            html.Span(
                                f"Pop {int(row['popularity'])}",
                                style={**BADGE, "backgroundColor": "#e8f5e9", "color": "#2d6a4f", "fontSize": "10px"},
                            ),
                            html.Span(
                                f"E {row['energy']}  V {row['valence']}  D {row['danceability']}",
                                style={"fontSize": "10px", "color": "#aaa"},
                            ),
                        ],
                        style={"marginTop": "3px", "display": "flex", "alignItems": "center", "gap": "4px"},
                    ),
                ],
            )
        )

    return html.Div(
        [
            html.Div(
                f"Similar to: {ref['track_name']} (pop {ref_pop})",
                style={"fontSize": "11px", "color": "#888", "marginBottom": "6px",
                       "fontStyle": "italic", "borderLeft": f"3px solid {GREEN}",
                       "paddingLeft": "8px"},
            ),
            html.Div(rows, style={"borderRadius": "10px", "border": "1px solid #f0f2f5", "overflow": "hidden"}),
        ]
    )


if __name__ == "__main__":
    app.run(debug=True)
