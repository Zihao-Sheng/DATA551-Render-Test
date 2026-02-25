import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dash import Dash, html, dcc, Input, Output, callback, ctx, no_update
import pandas as pd
import numpy as np
import dash_vega_components as dvc

import altair as alt
alt.data_transformers.disable_max_rows()

from charts.scatter import make_scatter
from charts.genre_bar import make_genre_bar
from charts.distribution import make_distribution
from charts.profile import make_audio_profile
from charts.song_list import make_song_list_table
from filter import filter_tracks

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "raw" / "dataset.csv"
data = pd.read_csv(DATA_PATH)

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
TOP_GENRES = list(data["track_genre"].value_counts().head(15).index)
GENRE_OPTIONS = [{"label": g, "value": g} for g in TOP_GENRES]

app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server

GREEN = "#1DB954"
DARK_GREEN = "#168d3e"
PAGE = {
    "fontFamily": "'Inter', system-ui, -apple-system, Segoe UI, Roboto, Arial",
    "backgroundColor": "#f0f2f5",
    "minHeight": "100vh",
    "padding": "0",
}
CARD = {
    "backgroundColor": "white",
    "borderRadius": "16px",
    "padding": "18px",
    "boxShadow": "0 1px 6px rgba(0,0,0,0.07)",
    "marginBottom": "14px",
}
SECTION_TITLE = {
    "fontSize": "14px",
    "fontWeight": "700",
    "color": "#1a1a2e",
    "marginTop": 0,
    "marginBottom": "12px",
    "letterSpacing": "-0.2px",
}
FILTER_LABEL = {
    "fontSize": "11px",
    "fontWeight": "600",
    "color": "#888",
    "textTransform": "uppercase",
    "letterSpacing": "0.7px",
    "marginTop": "14px",
    "marginBottom": "6px",
}
INPUT_STYLE = {
    "width": "100%",
    "padding": "9px 12px",
    "borderRadius": "10px",
    "border": "1px solid #e2e5ea",
    "outline": "none",
    "fontSize": "13px",
    "boxSizing": "border-box",
}
BADGE = {
    "display": "inline-block",
    "padding": "3px 10px",
    "borderRadius": "20px",
    "fontSize": "12px",
    "fontWeight": "600",
    "marginRight": "6px",
}

app.layout = html.Div(
    style=PAGE,
    children=[
        html.Div(
            style={
                "background": f"linear-gradient(135deg, #0d2016 0%, #1a3a22 100%)",
                "padding": "18px 28px",
                "marginBottom": "0",
            },
            children=html.Div(
                style={"maxWidth": "1760px", "margin": "0 auto",
                       "display": "flex", "justifyContent": "space-between", "alignItems": "center"},
                children=[
                    html.Div([
                        html.Div(
                            [

                                html.Span(
                                    "Spotify Track Insights Explorer",
                                    style={"fontSize": "20px", "fontWeight": "700", "color": "white", "letterSpacing": "-0.4px"},
                                ),
                            ]
                        ),
                        html.Div(
                            "Explore audio features, genres, and popularity across 114k+ tracks",
                            style={"fontSize": "12px", "color": "#8fba9a", "marginTop": "3px"},
                        ),
                    ]),
                    html.Div(
                        id="header-stats",
                        style={"display": "flex", "gap": "8px", "alignItems": "center"},
                    ),
                ],
            ),
        ),

        html.Div(
            style={
                "maxWidth": "1760px",
                "margin": "0 auto",
                "padding": "16px",
                "display": "grid",
                "gridTemplateColumns": "270px 1fr 320px",
                "gap": "16px",
                "alignItems": "start",
            },
            children=[

                html.Div(
                    style={**CARD, "marginBottom": 0},
                    children=[
                        html.Div("Filters", style={**SECTION_TITLE, "color": GREEN}),

                        html.Div("Search Tracks", style=FILTER_LABEL),
                        dcc.Input(
                            id="keyword",
                            type="text",
                            placeholder="Track name or artist…",
                            debounce=True,
                            style=INPUT_STYLE,
                        ),

                        html.Div("Genre", style=FILTER_LABEL),
                        html.Div(
                            dcc.Checklist(
                                id="genre",
                                options=GENRE_OPTIONS,
                                value=[],
                                style={"rowGap": "5px", "display": "grid"},
                                labelStyle={"display": "flex", "alignItems": "center", "gap": "8px", "fontSize": "13px"},
                                inputStyle={"accentColor": GREEN},
                            ),
                            style={"maxHeight": "240px", "overflowY": "auto", "paddingRight": "4px"},
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
                            labelStyle={"display": "flex", "alignItems": "center", "gap": "8px", "fontSize": "13px"},
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
                            style={"fontSize": "12px", "color": "#888", "marginTop": "16px",
                                   "padding": "10px 12px", "backgroundColor": "#f8f9fa",
                                   "borderRadius": "10px", "lineHeight": "1.6"},
                        ),
                    ],
                ),

                html.Div(
                    children=[
                        html.Div(
                            style=CARD,
                            children=[
                                html.Div(
                                    style={"display": "flex", "justifyContent": "space-between", "alignItems": "flex-start"},
                                    children=[
                                        html.Div([
                                            html.H4("Energy vs Valence", style=SECTION_TITLE),
                                            html.Div(id="scatter-meta", style={"fontSize": "12px", "color": "#888", "marginBottom": "8px"}),
                                        ]),
                                        dcc.RadioItems(
                                            id="toolbox-mode",
                                            options=[
                                                {"label": " Brush", "value": "brush"},
                                                {"label": " Pan/Zoom", "value": "pan"},
                                            ],
                                            value="brush",
                                            inline=True,
                                            style={"fontSize": "12px", "color": "#555"},
                                            labelStyle={"marginLeft": "10px", "cursor": "pointer"},
                                            inputStyle={"accentColor": GREEN},
                                        ),
                                    ],
                                ),
                                dvc.Vega(
                                    id="scatter",
                                    spec={},
                                    opt={"renderer": "svg", "actions": False},
                                    signalsToObserve=["brush_selection"],
                                    style={"width": "100%"},
                                ),
                            ],
                        ),

                        html.Div(
                            style=CARD,
                            children=[
                                html.H4("Top Genres by Popularity", style=SECTION_TITLE),
                                dvc.Vega(
                                    id="genre-bar",
                                    spec={},
                                    opt={"renderer": "svg", "actions": False},
                                    style={"width": "100%"},
                                ),
                            ],
                        ),

                        html.Div(
                            style=CARD,
                            children=[
                                html.H4("Feature Density — Selected Tracks", style=SECTION_TITLE),
                                dvc.Vega(
                                    id="distribution",
                                    spec={},
                                    opt={"renderer": "svg", "actions": False},
                                    style={"width": "100%"},
                                ),
                            ],
                        ),

                        html.Div(
                            style=CARD,
                            children=[
                                html.H4("Track List", style=SECTION_TITLE),
                                html.Div(id="song-list-container"),
                            ],
                        ),
                    ],
                ),

                html.Div(
                    children=[
                        html.Div(
                            style=CARD,
                            children=[
                                html.H4("Avg Audio Profile", style=SECTION_TITLE),
                                html.Div(
                                    style={"fontSize": "11px", "color": "#888", "marginBottom": "10px"},
                                    children="Mean values for selected / filtered tracks.",
                                ),
                                dvc.Vega(
                                    id="audio-profile",
                                    spec={},
                                    opt={"renderer": "svg", "actions": False},
                                    style={"width": "100%"},
                                ),
                            ],
                        ),

                        html.Div(
                            style=CARD,
                            children=[
                                html.H4("Discover Similar Tracks", style=SECTION_TITLE),
                                html.Div(
                                    "Pick a popular track from your selection — we'll find "
                                    "audio-similar but less-discovered songs.",
                                    style={"fontSize": "11px", "color": "#888", "marginBottom": "10px", "lineHeight": "1.5"},
                                ),
                                dcc.Dropdown(
                                    id="similar-track-dropdown",
                                    placeholder="Select a reference track…",
                                    options=[],
                                    value=None,
                                    clearable=True,
                                    style={"fontSize": "12px", "marginBottom": "12px"},
                                ),
                                html.Div(id="similar-tracks-container"),
                            ],
                        ),
                    ],
                ),
            ],
        ),

        dcc.Store(id="brush-bounds-store"),
        dcc.Store(id="selected-data-store"),
    ],
)


@callback(
    Output("scatter", "spec"),
    Output("scatter-meta", "children"),
    Output("header-stats", "children"),
    Output("filter-hint", "children"),
    Output("brush-bounds-store", "data"),
    Output("selected-data-store", "data"),
    Input("toolbox-mode", "value"),
    Input("keyword", "value"),
    Input("genre", "value"),
    Input("explicit", "value"),
    Input("tempo-range", "value"),
    Input("popularity-range", "value"),
    Input("scatter", "signalData"),
)
def update_scatter_and_stores(mode, keyword, genre_values, explicit_mode, tempo_bounds, pop_bounds, signal_data):
    explicit_val = {"explicit": True, "clean": False}.get(explicit_mode)

    genre_set = set(genre_values) if genre_values else None

    filtered_df = filter_tracks(
        data,
        keyword=keyword or None,
        genres=genre_set,
        tempo_range=tempo_bounds,
        popularity_range=pop_bounds,
        explicit=explicit_val,
        copy=False,
    )

    triggered = ctx.triggered_id

    brush = (signal_data or {}).get("brush_selection")
    if brush and "energy" in brush and "valence" in brush:
        e0, e1 = brush["energy"]
        v0, v1 = brush["valence"]
        bounds = {"energy": [e0, e1], "valence": [v0, v1]}
        selected_df = filtered_df[
            (filtered_df["energy"] >= e0) & (filtered_df["energy"] <= e1) &
            (filtered_df["valence"] >= v0) & (filtered_df["valence"] <= v1)
        ]
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

    n_shown = min(n_filtered, 2000)
    sampled = n_filtered > 2000
    meta_text = (
        f"Showing {n_shown:,}" + (" sampled" if sampled else "") +
        f" of {n_filtered:,} filtered · " +
        ("Brush to select a region" if mode == "brush" else "Pan & zoom enabled")
    )

    if triggered == "scatter":
        spec_out = no_update
    else:
        chart, _ = make_scatter(
            filtered_df,
            mode=mode,
            max_points=2000,
            topk_genres=10,
            selection_name="brush_selection",
            width=540,
            height=380,
        )
        spec_out = chart.to_dict()
        bounds = None
        selected_df = filtered_df

    selected_records = selected_df.head(5000).to_dict("records")

    return spec_out, meta_text, stats_children, filter_hint, bounds, selected_records


@callback(
    Output("genre-bar", "spec"),
    Input("selected-data-store", "data"),
)
def update_genre_bar(selected_records):
    if not selected_records:
        df = pd.DataFrame()
    else:
        df = pd.DataFrame(selected_records)
    chart = make_genre_bar(df, top_n=12, width=480, height=280)
    return chart.to_dict()


@callback(
    Output("distribution", "spec"),
    Input("selected-data-store", "data"),
)
def update_distribution(selected_records):
    if not selected_records:
        df = pd.DataFrame()
    else:
        df = pd.DataFrame(selected_records)
    chart = make_distribution(df, max_points=2000, width=480, height=190)
    return chart.to_dict()


@callback(
    Output("audio-profile", "spec"),
    Input("selected-data-store", "data"),
)
def update_audio_profile(selected_records):
    if not selected_records:
        df = pd.DataFrame()
    else:
        df = pd.DataFrame(selected_records)
    chart = make_audio_profile(df, width=260, height=240)
    return chart.to_dict()


@callback(
    Output("song-list-container", "children"),
    Input("selected-data-store", "data"),
)
def update_song_list(selected_records):
    if not selected_records:
        return html.Div(
            "No tracks match your filters.",
            style={"fontSize": "13px", "color": "#888", "padding": "16px 0"},
        )
    df = pd.DataFrame(selected_records)
    return make_song_list_table(df, max_rows=5000)


@callback(
    Output("similar-track-dropdown", "options"),
    Output("similar-track-dropdown", "value"),
    Input("selected-data-store", "data"),
)
def update_similar_dropdown(selected_records):
    if not selected_records:
        return [], None

    df = pd.DataFrame(selected_records)
    needed = ["track_id", "track_name", "artists", "popularity"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        return [], None

    top30 = df.nlargest(30, "popularity")[needed].drop_duplicates("track_id")
    options = [
        {
            "label": f"{row.track_name}  —  {row.artists}  (pop {int(row.popularity)})",
            "value": row.track_id,
        }
        for row in top30.itertuples()
    ]
    return options, None


@callback(
    Output("similar-tracks-container", "children"),
    Input("similar-track-dropdown", "value"),
)
def update_similar_tracks(track_id):
    if not track_id:
        return html.Div(
            "Select a track above to discover audio-similar but underrated songs.",
            style={"fontSize": "12px", "color": "#aaa", "padding": "8px 0", "lineHeight": "1.5"},
        )

    matches = data[data["track_id"] == track_id]
    if matches.empty:
        return html.Div("Track not found.", style={"fontSize": "12px", "color": "#c00"})

    ref = matches.iloc[0]
    ref_pop = int(ref["popularity"])
    ref_norm = data_norm.loc[matches.index[0]]

    dists = np.sqrt(((data_norm - ref_norm) ** 2).sum(axis=1))
    candidates = data.copy()
    candidates["_dist"] = dists.values
    candidates = (
        candidates[
            (candidates["track_id"] != track_id) &
            (candidates["popularity"] < ref_pop)
        ]
        .nsmallest(10, "_dist")
        [["track_name", "artists", "track_genre", "popularity", "energy", "valence", "danceability"]]
    )

    if candidates.empty:
        return html.Div("No similar lower-popularity tracks found.", style={"fontSize": "12px", "color": "#888"})

    candidates = candidates.copy()
    for col in ["energy", "valence", "danceability"]:
        candidates[col] = candidates[col].round(2)

    rows = []
    for _, row in candidates.iterrows():
        rows.append(
            html.Div(
                style={
                    "padding": "9px 10px",
                    "borderBottom": "1px solid #f0f2f5",
                    "fontSize": "12px",
                },
                children=[
                    html.Div(
                        row["track_name"],
                        style={"fontWeight": "600", "color": "#1a1a2e", "overflow": "hidden",
                               "textOverflow": "ellipsis", "whiteSpace": "nowrap"},
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
