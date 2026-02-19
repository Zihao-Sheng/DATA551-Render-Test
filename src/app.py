from dash import Dash, html, dcc, Input, Output
import pandas as pd
from pathlib import Path

from charts.scatter import make_scatter
from filter import filter_tracks  # <- 同级 filter.py


# importing data, note that this is raw data for now
ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "raw" / "dataset.csv"
data = pd.read_csv(DATA_PATH)

# initializing app
app = Dash(__name__)
server = app.server  # for deployment later

# style setters
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

# ---- constants for sliders ----
TEMPO_MIN, TEMPO_MAX = 0, 250
POP_MIN, POP_MAX = 0, 100

# show a manageable genre list in the sidebar (top N by frequency)
TOP_GENRE_OPTIONS = list(data["track_genre"].value_counts().head(12).index)
GENRE_OPTIONS = [{"label": g, "value": g} for g in TOP_GENRE_OPTIONS]


def _bounds_to_set(bounds, min_v, max_v):
    """Convert slider [lo, hi] into {lo_or_None, hi_or_None} for filter_tracks()."""
    lo, hi = bounds
    lo_out = None if lo == min_v else lo
    hi_out = None if hi == max_v else hi
    return {lo_out, hi_out}


# all placeholders should eventually be replaced by features
app.layout = html.Div(
    style=PAGE,
    children=[
        # Header
        html.Div(
            style=HEADER,
            children=[
                html.H3("Playlist Editor Dashboard", style={"margin": 0}),
            ],
        ),

        # GRID Structure
        html.Div(
            style=GRID,
            children=[
                # ---------------- Left Column ----------------
                html.Div(
                    style=CARD,
                    children=[
                        html.Div(
                            [
                                html.Div("Filters", style={"fontWeight": 700, "marginBottom": "10px"}),

                                # Search
                                html.Div("Search Tracks", style={"fontSize": "12px", "color": "#666", "marginBottom": "6px"}),
                                dcc.Input(
                                    id="keyword",
                                    type="text",
                                    placeholder="Type a keyword…",
                                    style={
                                        "width": "100%",
                                        "height": "100%",
                                        "padding": "10px 12px",
                                        "borderRadius": "10px",
                                        "border": "1px solid #e9e9ef",
                                        "outline": "none",
                                        "marginBottom": "14px",
                                    },
                                ),

                                # Genre checklist
                                html.Div("Genre", style={"fontSize": "12px", "color": "#666", "marginBottom": "6px"}),
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

                                # Explicit radio
                                html.Div("Explicit Content", style={"fontSize": "12px", "color": "#666", "marginBottom": "6px"}),
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

                                # Tempo range slider
                                html.Div("Tempo", style={"fontSize": "12px", "color": "#666", "marginBottom": "6px"}),
                                dcc.RangeSlider(
                                    id="tempo-range",
                                    min=TEMPO_MIN,
                                    max=TEMPO_MAX,
                                    step=1,
                                    value=[TEMPO_MIN, TEMPO_MAX],
                                    tooltip={"placement": "bottom", "always_visible": False},
                                ),
                                html.Div(style={"height": "14px"}),

                                # Popularity range slider
                                html.Div("Popularity", style={"fontSize": "12px", "color": "#666", "marginBottom": "6px"}),
                                dcc.RangeSlider(
                                    id="popularity-range",
                                    min=POP_MIN,
                                    max=POP_MAX,
                                    step=1,
                                    value=[POP_MIN, POP_MAX],
                                    tooltip={"placement": "bottom", "always_visible": False},
                                ),

                                # (Optional) a tiny hint row at bottom
                                html.Div(
                                    id="filter-hint",
                                    style={"fontSize": "11px", "color": "#888", "marginTop": "12px"},
                                ),
                            ]
                        )
                    ],
                ),

                # ---------------- Middle Column ----------------
                html.Div(
                    children=[
                        # Scatter Card
                        html.Div(
                            style={**CARD, "marginBottom": "16px"},
                            children=[
                                html.H4("Track Overview", style={"marginTop": 0}),

                                # toolbox: brush vs pan/zoom
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

                                # meta info line
                                html.Div(
                                    id="scatter-meta",
                                    style={"fontSize": "12px", "color": "#666", "marginBottom": "8px"},
                                ),

                                # Square container for scatter
                                html.Div(
                                    style={
                                        "width": "100%",
                                        "height": "450px",
                                        "overflow": "hidden",
                                        "borderRadius": "12px",
                                        "background": "#fff",
                                    },
                                    children=[
                                        html.Iframe(
                                            id="scatter",
                                            srcDoc="",
                                            style={"width": "100%", "height": "100%", "border": "0"},
                                        )
                                    ],
                                ),
                            ],
                        ),

                        # Below scatter placeholders
                        html.Div(
                            "Distribution Plot Placeholder",
                            style={**PLACEHOLDER, "height": "320px", "marginBottom": "16px"},
                        ),
                        html.Div(
                            "Song List Placeholder",
                            style={**PLACEHOLDER, "height": "320px"},
                        ),
                    ],
                ),

                # ---------------- Right Column ----------------
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


@app.callback(
    Output("scatter", "srcDoc"),
    Output("scatter-meta", "children"),
    Output("filter-hint", "children"),
    Input("toolbox-mode", "value"),
    Input("keyword", "value"),
    Input("genre", "value"),
    Input("explicit", "value"),
    Input("tempo-range", "value"),
    Input("popularity-range", "value"),
)
def update_scatter(mode, keyword, genre_values, explicit_mode, tempo_bounds, pop_bounds):
    # map explicit selector -> bool/None for filter_tracks()
    if explicit_mode == "explicit":
        explicit_val = True
    elif explicit_mode == "clean":
        explicit_val = False
    else:
        explicit_val = None  # include both

    # convert sliders -> {lo_or_None, hi_or_None}
    tempo_range = [
        None if tempo_bounds[0] == TEMPO_MIN else tempo_bounds[0],
        None if tempo_bounds[1] == TEMPO_MAX else tempo_bounds[1],
    ]
    popularity_range = [
        None if pop_bounds[0] == POP_MIN else pop_bounds[0],
        None if pop_bounds[1] == POP_MAX else pop_bounds[1],
    ]
    # genres list -> set (or None)
    genre_set = set(genre_values) if genre_values else None

    # apply filtering using your function in filter.py
    filtered = filter_tracks(
        data,
        keyword=keyword,
        genres=genre_set,
        tempo_range=tempo_range,
        popularity_range=popularity_range,
        explicit=explicit_val,
        copy=False,
    )

    # build chart (make_scatter will also downsample if too many points)
    chart, meta = make_scatter(
        filtered,
        mode=mode,
        max_points=500,
        topk_genres=10,
        width=520,
        height=400,
    )

    # meta text shown above scatter
    meta_text = f"Showing {meta['n_shown']} of {meta['n_total']} tracks"
    if meta["sampled"]:
        meta_text += " (sampled for performance)"
    meta_text += f" · Colored by Top {meta['topk_genres']} genres + Other"
    meta_text += " · Mode: Brush" if mode == "brush" else " · Mode: Pan/Zoom"

    # small hint in filter panel (optional)
    hint = f"Filtered result: {len(filtered)} tracks"

    return chart.to_html(), meta_text, hint


if __name__ == "__main__":
    app.run(debug=True)
