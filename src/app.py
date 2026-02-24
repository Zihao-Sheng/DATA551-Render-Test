# app.py
from dash import Dash, html, dcc, Input, Output, callback, ctx, no_update
import pandas as pd
from pathlib import Path
import dash_vega_components as dvc

from charts.scatter import make_scatter
from filter import filter_tracks
from charts.song_list import make_song_list_table

# ---------------- Data ----------------
ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "raw" / "dataset.csv"
data = pd.read_csv(DATA_PATH)

# ---------------- App ----------------
app = Dash(__name__)
server = app.server  # for deployment later

# ---------------- Styles ----------------
PAGE = {
    "fontFamily": "system-ui, -apple-system, Segoe UI, Roboto, Arial",
    "backgroundColor": "#f6f7f6",
    "minHeight": "100vh",
    "padding": "0px",
}

HEADER = {
    "backgroundColor": "white",
    "borderRadius": "12px",
    "padding": "16px 20px",
    "marginBottom": "16px",
    "border": "1px solid #e9e9ef",
}

GRID = {
    "display": "grid",
    "gridTemplateColumns": "280px 1fr 320px",
    "gap": "16px",
    "alignItems": "start",
}

CARD = {
    "backgroundColor": "white",
    "borderRadius": "20px",
    "padding": "16px",
    "border": "1px solid #e9e9ef",
}

PLACEHOLDER = {
    "height": "320px",
    "background": "#f0f1f6",
    "borderRadius": "10px",
    "display": "flex",
    "alignItems": "center",
    "justifyContent": "center",
    "color": "#999",
    "fontSize": "14px",
}


# ---------------- Filter constants ----------------
TEMPO_MIN, TEMPO_MAX = 0, 250
POP_MIN, POP_MAX = 0, 100

# Left sidebar genre options (top N by frequency for usability)
TOP_GENRE_OPTIONS = list(data["track_genre"].value_counts().head(12).index)
GENRE_OPTIONS = [{"label": g, "value": g} for g in TOP_GENRE_OPTIONS]

# ---------------- Layout ----------------
app.layout = html.Div(
    style=PAGE,
    children=[
        # Header
        html.Div(
            style=HEADER,
            children=[html.H3("Playlist Editor Dashboard", style={"margin": 0})],
        ),

        # Stores for brush bounds + selected rows (full filtered selection)
        dcc.Store(id="brush-bounds-store"),
        dcc.Store(id="selected-data-store"),

        # GRID
        html.Div(
            style=GRID,
            children=[
                # -------- Left column (Filters) --------
                html.Div(
                    style=CARD,
                    children=[
                        html.Div(
                            [
                                html.Div("Filters", style={"fontWeight": 700, "marginBottom": "10px"}),

                                html.Div(
                                    "Search Tracks",
                                    style={"fontSize": "12px", "color": "#666", "marginBottom": "6px"},
                                ),
                                dcc.Input(
                                    id="keyword",
                                    type="text",
                                    placeholder="Type a keyword…",
                                    style={
                                        "width": "100%",
                                        "padding": "10px 12px",
                                        "borderRadius": "10px",
                                        "border": "1px solid #e9e9ef",
                                        "outline": "none",
                                        "marginBottom": "14px",
                                    },
                                ),

                                html.Div(
                                    "Genre",
                                    style={"fontSize": "12px", "color": "#666", "marginBottom": "6px"},
                                ),
                                dcc.Checklist(
                                    id="genre",
                                    options=GENRE_OPTIONS,
                                    value=[],
                                    style={"display": "grid", "gridTemplateColumns": "1fr", "rowGap": "6px"},
                                    labelStyle={"display": "flex", "alignItems": "center", "gap": "8px"},
                                ),
                                html.Div(
                                    "Showing top genres only (for now).",
                                    style={"fontSize": "11px", "color": "#888", "marginTop": "6px", "marginBottom": "14px"},
                                ),

                                html.Div(
                                    "Explicit Content",
                                    style={"fontSize": "12px", "color": "#666", "marginBottom": "6px"},
                                ),
                                dcc.RadioItems(
                                    id="explicit",
                                    options=[
                                        {"label": " All Tracks", "value": "all"},
                                        {"label": " Explicit only", "value": "explicit"},
                                        {"label": " Clean only", "value": "clean"},
                                    ],
                                    value="all",
                                    style={"display": "grid", "rowGap": "6px", "marginBottom": "14px"},
                                    labelStyle={"display": "flex", "alignItems": "center", "gap": "8px"},
                                ),

                                html.Div(
                                    "Tempo",
                                    style={"fontSize": "12px", "color": "#666", "marginBottom": "6px"},
                                ),
                                dcc.RangeSlider(
                                    id="tempo-range",
                                    min=TEMPO_MIN,
                                    max=TEMPO_MAX,
                                    step=1,
                                    value=[TEMPO_MIN, TEMPO_MAX],
                                    tooltip={"placement": "bottom", "always_visible": False},
                                ),
                                html.Div(style={"height": "14px"}),

                                html.Div(
                                    "Popularity",
                                    style={"fontSize": "12px", "color": "#666", "marginBottom": "6px"},
                                ),
                                dcc.RangeSlider(
                                    id="popularity-range",
                                    min=POP_MIN,
                                    max=POP_MAX,
                                    step=1,
                                    value=[POP_MIN, POP_MAX],
                                    tooltip={"placement": "bottom", "always_visible": False},
                                ),

                                html.Div(
                                    id="filter-hint",
                                    style={"fontSize": "11px", "color": "#888", "marginTop": "12px"},
                                ),
                            ]
                        )
                    ],
                ),

                # -------- Middle column --------
                html.Div(
                    children=[
                        html.Div(
                            style={**CARD, "marginBottom": "16px"},
                            children=[
                                html.H4("Track Overview", style={"marginTop": 0}),

                                # Toolbox button (radio toggle)
                                dcc.RadioItems(
                                    id="toolbox-mode",
                                    options=[
                                        {"label": " Brush select", "value": "brush"},
                                        {"label": " Pan/Zoom", "value": "pan"},
                                    ],
                                    value="brush",
                                    inline=True,
                                    style={"fontSize": "12px", "color": "#444", "marginBottom": "6px"},
                                ),

                                html.Div(
                                    id="scatter-meta",
                                    style={"fontSize": "12px", "color": "#666", "marginBottom": "8px"},
                                ),

                                html.Div(
                                    style={
                                        "width": "100%",
                                        "height": "450px",
                                        "overflow": "hidden",
                                        "borderRadius": "12px",
                                        "background": "#fff",
                                    },
                                    children=[
                                        dvc.Vega(
                                            id="scatter",
                                            spec={},  # filled by callback
                                            opt={"renderer": "svg", "actions": False},
                                            signalsToObserve=["brush_selection"],
                                            style={"width": "100%", "height": "100%"},
                                        )
                                    ],
                                ),
                            ],
                        ),

                        html.Div(
                            "Distribution Plot Placeholder",
                            style={**PLACEHOLDER, "height": "320px", "marginBottom": "16px"},
                        ),
                        html.Div(
                            style={**CARD, "marginBottom": "16px"},
                            children=[
                                html.H4("Track List", style={"marginTop": 0}),
                                html.Div(id="song-list-container"),
                            ],
                        ),
                    ],
                ),

                # -------- Right column --------
                html.Div(
                    style=CARD,
                    children=[
                        html.Div("Comparer Placeholder", style={**PLACEHOLDER, "height": "300px"}),
                        html.Div("Recommendation Placeholder", style={**PLACEHOLDER, "height": "600px"}),
                    ],
                ),
            ],
        ),
    ],
)

# ---------------- Callbacks ----------------
@callback(
    Output("scatter", "spec"),
    Output("scatter-meta", "children"),
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
def update_scatter_and_selection(
    mode, keyword, genre_values, explicit_mode, tempo_bounds, pop_bounds, signal_data
):
    # ---- explicit mapping ----
    if explicit_mode == "explicit":
        explicit_val = True
    elif explicit_mode == "clean":
        explicit_val = False
    else:
        explicit_val = None

    # ---- slider -> [lo_or_None, hi_or_None] ----
    tempo_range = [
        None if tempo_bounds[0] == TEMPO_MIN else tempo_bounds[0],
        None if tempo_bounds[1] == TEMPO_MAX else tempo_bounds[1],
    ]
    popularity_range = [
        None if pop_bounds[0] == POP_MIN else pop_bounds[0],
        None if pop_bounds[1] == POP_MAX else pop_bounds[1],
    ]

    # ---- genre list -> set/None ----
    genre_set = set(genre_values) if genre_values else None

    # ---- full filtered data ----
    filtered_df = filter_tracks(
        data,
        keyword=keyword,
        genres=genre_set,
        tempo_range=tempo_range,
        popularity_range=popularity_range,
        explicit=explicit_val,
        copy=False,
    )

    triggered = ctx.triggered_id

    # ---- parse brush bounds ----
    brush = (signal_data or {}).get("brush_selection")
    if brush and "energy" in brush and "valence" in brush:
        e0, e1 = brush["energy"]
        v0, v1 = brush["valence"]
        bounds = {"energy": [e0, e1], "valence": [v0, v1]}

        selected_df = filtered_df[
            (filtered_df["energy"] >= e0)
            & (filtered_df["energy"] <= e1)
            & (filtered_df["valence"] >= v0)
            & (filtered_df["valence"] <= v1)
        ]
    else:
        bounds = None
        selected_df = filtered_df

    filter_hint = f"Filtered: {len(filtered_df)} tracks"

    n_total = len(filtered_df)
    n_shown = min(n_total, 500)
    sampled = n_total > 500

    meta_text = (
        f"Plotted: {n_shown} of {n_total} tracks"
        + (" (sampled)" if sampled else "")
        + f" · Mode: {'Brush' if mode == 'brush' else 'Pan/Zoom'}"
        + f" · Selected: {len(selected_df)}"
    )

    # IMPORTANT: don't redraw spec when brushing
    if triggered == "scatter":
        spec_out = no_update
    else:
        chart, _meta = make_scatter(
            filtered_df,
            mode=mode,
            max_points=500,
            topk_genres=10,
            selection_name="brush_selection",
            width=520,
            height=400,
        )
        spec_out = chart.to_dict()

        # reset selection when filters/mode change
        bounds = None
        selected_df = filtered_df
        meta_text = (
            f"Plotted: {min(len(filtered_df), 500)} of {len(filtered_df)} tracks"
            + (" (sampled)" if len(filtered_df) > 500 else "")
            + f" · Colored by Top 10 genres + Other"
            + f" · Mode: {'Brush' if mode == 'brush' else 'Pan/Zoom'}"
            + f" · Selected: {len(selected_df)}"
        )

    selected_records = selected_df.head(5000).to_dict("records")

    return spec_out, meta_text, filter_hint, bounds, selected_records


@callback(
    Output("song-list-container", "children"),
    Input("selected-data-store", "data"),
)
def update_song_list(selected_records):
    if not selected_records:
        return html.Div(
            "No tracks selected.",
            style={"fontSize": "12px", "color": "#666", "padding": "10px"},
        )

    df = pd.DataFrame(selected_records)
    return make_song_list_table(df, max_rows=5000)

if __name__ == "__main__":
    app.run(debug=True)