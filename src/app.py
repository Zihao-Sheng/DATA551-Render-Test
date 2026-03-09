import sys
from pathlib import Path
from functools import lru_cache
import copy
sys.path.insert(0, str(Path(__file__).parent))

from dash import Dash, html, dcc, Input, Output, State, callback, ctx, no_update, ALL
import pandas as pd
import numpy as np
import dash_vega_components as dvc
import plotly.graph_objects as go

import altair as alt
alt.data_transformers.disable_max_rows()

from charts.scatter import make_scatter, BRIGHT_PALETTE, OTHER_COLOR
from charts.genre_bar import make_genre_bar
from charts.distribution import make_distribution
from charts.profile import make_audio_profile
from charts.tempo_dist import make_tempo_distribution
from charts.mood_quadrant import make_mood_quadrant
from charts.song_list import make_song_list_table
from filter import filter_tracks

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "raw" / "dataset.csv"
REQUIRED_COLUMNS = [
    "track_id",
    "artists",
    "track_name",
    "track_genre",
    "popularity",
    "explicit",
    "tempo",
    "danceability",
    "energy",
    "valence",
    "acousticness",
    "speechiness",
    "liveness",
    "instrumentalness",
]
DTYPE_MAP = {
    "track_id": "string",
    "artists": "string",
    "track_name": "string",
    "track_genre": "string",
    "popularity": "int16",
    "explicit": "boolean",
    "tempo": "float32",
    "danceability": "float32",
    "energy": "float32",
    "valence": "float32",
    "acousticness": "float32",
    "speechiness": "float32",
    "liveness": "float32",
    "instrumentalness": "float32",
}
data = pd.read_csv(DATA_PATH, usecols=REQUIRED_COLUMNS, dtype=DTYPE_MAP)
data["_track_name_lc"] = data["track_name"].astype(str).str.lower()
data["_artists_lc"] = data["artists"].astype(str).str.lower()
data["track_id"] = data["track_id"].astype(str)
_track_id_idx = data.set_index("track_id", drop=False, verify_integrity=False)
TRACK_LOOKUP = {
    (str(r["track_name"]).strip().lower(), str(r["artists"]).strip().lower()): str(r["track_id"]).strip()
    for _, r in data[["track_name", "artists", "track_id"]].dropna().drop_duplicates("track_id").iterrows()
}

AUDIO_FEATURES = [
    "danceability", "energy", "valence",
    "acousticness", "speechiness", "liveness", "instrumentalness",
]
_feat_min = data[AUDIO_FEATURES].min()
_feat_max = data[AUDIO_FEATURES].max()
_feat_rng = (_feat_max - _feat_min).replace(0, 1)
data_norm = (data[AUDIO_FEATURES] - _feat_min) / _feat_rng
NORM_FEATURES = [f"_n_{c}" for c in AUDIO_FEATURES]
for c in AUDIO_FEATURES:
    data[f"_n_{c}"] = pd.to_numeric(data_norm[c], errors="coerce").astype("float32")

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
    "fontSize": "10px",
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
    "fontSize": "12px",
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

            # Fallback for environments where signal payload omits track_id
            # but still carries track text fields.
            tn = node.get("track_name")
            ar = node.get("artists")
            if tn is not None and ar is not None:
                key = (str(tn).strip().lower(), str(ar).strip().lower())
                tid = TRACK_LOOKUP.get(key)
                if tid:
                    return _norm(tid)

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

    # Prefer the named point-selection payload; fallback to scanning all signal data.
    found = _walk(point_payload) if point_payload is not None else None
    if found:
        return found
    return _walk(signal_data)


def _extract_track_payload_from_scatter_signal(signal_data):
    """
    Best-effort parser for Vega point-selection payload with extra fields.
    Returns a dict containing at least track_id when found.
    """
    if not signal_data:
        return None

    point_payload = signal_data.get("track_pick")
    if point_payload is None:
        for k, v in (signal_data or {}).items():
            if isinstance(k, str) and "track_pick" in k:
                point_payload = v
                break

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
        if not isinstance(fields, list) or not isinstance(values, list):
            return None
        mapping = {}
        for idx, f in enumerate(fields):
            if not (isinstance(f, dict) and idx < len(values)):
                continue
            field_name = f.get("field")
            if field_name in {"_row_id", "track_id", "track_name", "artists", "track_genre"}:
                mapping[field_name] = _norm(values[idx])
        if mapping.get("_row_id") or mapping.get("track_id"):
            return mapping
        return None

    def _walk(node):
        if isinstance(node, dict):
            if (node.get("_row_id") is not None) or (node.get("track_id") is not None):
                payload = {
                    "_row_id": _norm(node.get("_row_id")),
                    "track_id": _norm(node.get("track_id")),
                    "track_name": _norm(node.get("track_name")),
                    "artists": _norm(node.get("artists")),
                    "track_genre": _norm(node.get("track_genre")),
                }
                if payload["_row_id"] or payload["track_id"]:
                    return payload

            fv = _from_fields_values(node.get("fields"), node.get("values"))
            if fv:
                return fv

            values_node = node.get("values")
            if isinstance(values_node, list):
                for item in values_node:
                    found = _walk(item)
                    if found:
                        return found

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

    found = _walk(point_payload) if point_payload is not None else None
    if found:
        return found
    return _walk(signal_data)


def _get_track_row_by_index(row_index):
    if row_index is None:
        return None
    try:
        idx = int(row_index)
    except Exception:
        return None
    if idx not in data.index:
        return None
    row = data.loc[idx].copy()
    for c in ["popularity", "tempo", *PROFILE_AXES]:
        if c in row.index:
            row[c] = pd.to_numeric(row[c], errors="coerce")
    return row


def _get_track_row(track_id: str, *, track_name: str | None = None, artists: str | None = None, track_genre: str | None = None):
    if not track_id:
        return None
    tid = str(track_id).strip()
    if not tid:
        return None
    if tid not in _track_id_idx.index:
        return None
    rows = _track_id_idx.loc[tid]
    if isinstance(rows, pd.DataFrame):
        candidates = rows.copy()
        # Disambiguate duplicated track_id rows using the selected point metadata.
        for col, val in (
            ("track_name", track_name),
            ("artists", artists),
            ("track_genre", track_genre),
        ):
            if val is None or col not in candidates.columns:
                continue
            match = candidates[candidates[col].astype(str).str.strip().str.lower() == str(val).strip().lower()]
            if len(match) > 0:
                candidates = match
        row = candidates.iloc[0].copy()
    else:
        row = rows.copy()
    for c in ["popularity", "tempo", *PROFILE_AXES]:
        if c in row.index:
            row[c] = pd.to_numeric(row[c], errors="coerce")
    return row


def _build_genre_color_map(top_genres):
    top = [str(g) for g in (top_genres or [])]
    legend_order = top + ["Other"]
    palette = BRIGHT_PALETTE[: len(legend_order) - 1] + [OTHER_COLOR]
    return {g: c for g, c in zip(legend_order, palette)}


def _color_for_genre(track_genre: str, genre_color_map):
    if isinstance(genre_color_map, dict) and genre_color_map:
        g = str(track_genre or "")
        return genre_color_map.get(g, genre_color_map.get("Other", OTHER_COLOR))
    return OTHER_COLOR


@lru_cache(maxsize=2048)
def _build_primary_radar_dict(values_key, color_key, compare_mode_key):
    theta = ["Energy", "Valence", "Dance", "Acoustic", "Speech", "Live"]
    values = [float(v) for v in values_key]
    fig = go.Figure(
        data=[
            go.Scatterpolar(
                r=values + [values[0]],
                theta=theta + [theta[0]],
                name=("Locked Track" if compare_mode_key else "Track"),
                fill="toself",
                line=dict(color=color_key, width=2),
                fillcolor=color_key,
                opacity=0.35,
                hovertemplate="%{theta}: %{r:.2f}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        margin=dict(l=32, r=24, t=2, b=2),
        showlegend=False,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.97,
            xanchor="left",
            x=1.01,
            font=dict(size=8),
            bgcolor="rgba(255,255,255,0.0)",
        ),
        paper_bgcolor="white",
        polar=dict(
            bgcolor="white",
            radialaxis=dict(visible=True, range=[0, 1], tickfont=dict(size=7), gridcolor="#e6ebf2"),
            angularaxis=dict(tickfont=dict(size=7)),
        ),
    )
    return fig.to_dict()


@lru_cache(maxsize=2048)
def _build_compare_trace_dict(values_key, color_key):
    theta = ["Energy", "Valence", "Dance", "Acoustic", "Speech", "Live"]
    values = [float(v) for v in values_key]
    return go.Scatterpolar(
        r=values + [values[0]],
        theta=theta + [theta[0]],
        name="Compared Track",
        fill="none",
        line=dict(color=color_key or "#666", width=2, dash="dot"),
        opacity=0.95,
        hovertemplate="%{theta}: %{r:.2f}<extra></extra>",
    ).to_plotly_json()


def _normalize_key_seq(values):
    return tuple(sorted(str(v) for v in (values or []) if str(v)))


def _normalize_bounds(bounds, default_lo, default_hi):
    if isinstance(bounds, (list, tuple)) and len(bounds) == 2:
        lo = default_lo if bounds[0] is None else bounds[0]
        hi = default_hi if bounds[1] is None else bounds[1]
        return float(lo), float(hi)
    return float(default_lo), float(default_hi)


@lru_cache(maxsize=256)
def _compute_filtered_index_cached(
    keyword_key,
    genre_key,
    explicit_mode_key,
    tempo_lo,
    tempo_hi,
    pop_lo,
    pop_hi,
    liked_only,
    liked_key,
):
    explicit_val = {"explicit": True, "clean": False}.get(explicit_mode_key)
    genre_set = set(genre_key) if genre_key else None
    filtered = filter_tracks(
        data,
        keyword=keyword_key or None,
        genres=genre_set,
        tempo_range=[tempo_lo, tempo_hi],
        popularity_range=[pop_lo, pop_hi],
        explicit=explicit_val,
        copy=False,
    )
    if not liked_only:
        return tuple(filtered.index.tolist())

    liked_set = set(liked_key)
    if not liked_set or "track_id" not in filtered.columns:
        return tuple()
    return tuple(filtered[filtered["track_id"].isin(liked_set)].index.tolist())


def _compute_filtered_df(
    keyword,
    genre_values,
    explicit_mode,
    tempo_bounds,
    pop_bounds,
    liked_filter_values=None,
    liked_tracks=None,
):
    keyword_key = (keyword or "").strip().lower()
    genre_key = _normalize_key_seq(genre_values)
    tempo_lo, tempo_hi = _normalize_bounds(tempo_bounds, TEMPO_MIN, TEMPO_MAX)
    pop_lo, pop_hi = _normalize_bounds(pop_bounds, POP_MIN, POP_MAX)
    liked_only = bool(liked_filter_values and "liked" in liked_filter_values)
    liked_key = _normalize_key_seq(liked_tracks) if liked_only else tuple()

    idx = _compute_filtered_index_cached(
        keyword_key,
        genre_key,
        explicit_mode if explicit_mode in {"all", "explicit", "clean"} else str(explicit_mode or "all"),
        tempo_lo,
        tempo_hi,
        pop_lo,
        pop_hi,
        liked_only,
        liked_key,
    )
    if not idx:
        return data.iloc[0:0]
    return data.loc[list(idx)]


def _compute_selected_df(filtered_df, bounds):
    if not bounds:
        return filtered_df
    e0, e1 = bounds["energy"]
    v0, v1 = bounds["valence"]
    return filtered_df[
        (filtered_df["energy"] >= e0) & (filtered_df["energy"] <= e1) &
        (filtered_df["valence"] >= v0) & (filtered_df["valence"] <= v1)
    ]


def _df_from_filtered_index(filtered_index_data):
    idx = list(filtered_index_data or [])
    if not idx:
        return data.iloc[0:0]
    return data.loc[idx]


def _selected_index_key(selected_index_data):
    return tuple(int(i) for i in (selected_index_data or []))


def _build_pool_from_ids(pool_ids):
    if not pool_ids:
        return data.iloc[0:0]
    rows = _track_id_idx.loc[list(pool_ids)]
    if isinstance(rows, pd.Series):
        return rows.to_frame().T
    return rows


@lru_cache(maxsize=128)
def _pool_track_ids_from_selected_index_cached(selected_index_tuple):
    if not selected_index_tuple:
        return tuple()
    idx = [int(i) for i in selected_index_tuple]
    if len(idx) == 0:
        return tuple()
    track_ids = data.loc[idx, "track_id"].astype(str)
    return tuple(pd.unique(track_ids))


def _compute_similar_records_from_pool(pool_df, track_id_str):
    required = [
        "track_id", "track_name", "artists", "track_genre", "popularity",
        "energy", "valence", "danceability", *NORM_FEATURES
    ]
    missing = [c for c in required if c not in pool_df.columns]
    if missing:
        return {"status": "missing", "missing": missing}

    work = pool_df[required].copy()
    work["track_id"] = work["track_id"].astype(str)
    work["popularity"] = pd.to_numeric(work["popularity"], errors="coerce")
    for c in ["energy", "valence", "danceability"]:
        work[c] = pd.to_numeric(work[c], errors="coerce")
    for c in NORM_FEATURES:
        work[c] = pd.to_numeric(work[c], errors="coerce")
    work = work.dropna(subset=["track_id", "popularity", *NORM_FEATURES]).drop_duplicates("track_id")

    ref_rows = work[work["track_id"] == track_id_str]
    if ref_rows.empty:
        return {"status": "ref_not_in_pool"}

    ref = ref_rows.iloc[0]
    ref_pop = int(ref["popularity"])
    ref_name = str(ref.get("track_name", "Unknown"))
    ref_norm = ref[NORM_FEATURES].to_numpy(dtype=float)
    work_norm = work[NORM_FEATURES].to_numpy(dtype=float)
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
    records = tuple(
        (
            str(r.track_id),
            str(r.track_name),
            str(r.artists),
            str(r.track_genre),
            float(r.popularity),
            float(r.energy),
            float(r.valence),
            float(r.danceability),
        )
        for r in candidates.itertuples()
    )
    return {"status": "ok", "ref_name": ref_name, "ref_pop": ref_pop, "records": records}


@lru_cache(maxsize=64)
def _compute_similar_records_cached(track_id_str, pool_ids_tuple):
    pool_df = _build_pool_from_ids(pool_ids_tuple)
    return _compute_similar_records_from_pool(pool_df, track_id_str)


@lru_cache(maxsize=96)
def _genre_bar_spec_cached(selected_index_key):
    df = _df_from_filtered_index(selected_index_key)
    return make_genre_bar(df, top_n=10, width=290, height=320, swap_axes=True).to_dict()


@lru_cache(maxsize=96)
def _distribution_spec_cached(selected_index_key):
    df = _df_from_filtered_index(selected_index_key)
    # Heavier chart on Render: use lower sampling cap for smoother first paint/interactions.
    return make_distribution(df, max_points=1200, width=290, height=300, swap_axes=False).to_dict()


@lru_cache(maxsize=96)
def _audio_profile_spec_cached(selected_index_key):
    df = _df_from_filtered_index(selected_index_key)
    return make_audio_profile(df, width=290, height=320, swap_axes=True).to_dict()


@lru_cache(maxsize=96)
def _tempo_distribution_spec_cached(selected_index_key):
    df = _df_from_filtered_index(selected_index_key)
    return make_tempo_distribution(df, width=290, height=240).to_dict()


@lru_cache(maxsize=96)
def _mood_quadrant_spec_cached(selected_index_key):
    df = _df_from_filtered_index(selected_index_key)
    return make_mood_quadrant(df, width=290, height=250).to_dict()


@lru_cache(maxsize=96)
def _popularity_hist_spec_cached(selected_index_key):
    df = _df_from_filtered_index(selected_index_key)
    if df is None or len(df) == 0 or "popularity" not in df.columns:
        chart = (
            alt.Chart(pd.DataFrame({"label": ["No data"], "value": [1]}))
            .mark_text(fontSize=12, color="#8898a9")
            .encode(text="label:N")
            .properties(width=290, height=220)
        )
        return chart.to_dict()

    work = df[["popularity"]].copy()
    work["popularity"] = pd.to_numeric(work["popularity"], errors="coerce").clip(0, 100)
    work = work.dropna()
    if work.empty:
        chart = (
            alt.Chart(pd.DataFrame({"label": ["No data"], "value": [1]}))
            .mark_text(fontSize=12, color="#8898a9")
            .encode(text="label:N")
            .properties(width=290, height=220)
        )
        return chart.to_dict()

    chart = (
        alt.Chart(work)
        .mark_bar(
            cornerRadiusTopLeft=4,
            cornerRadiusTopRight=4,
            color="#7CBF8E",
            opacity=0.9,
            stroke="#ffffff",
            strokeWidth=0.6,
        )
        .encode(
            x=alt.X(
                "popularity:Q",
                bin=alt.Bin(maxbins=16),
                title="Popularity",
                scale=alt.Scale(domain=[0, 100]),
                axis=alt.Axis(grid=False),
            ),
            y=alt.Y("count():Q", title="Track Count", axis=alt.Axis(grid=True, gridOpacity=0.2)),
            tooltip=[
                alt.Tooltip("count():Q", title="Tracks"),
            ],
        )
        .properties(width=290, height=240)
        .configure_view(stroke=None)
        .configure_axis(labelFontSize=10, titleFontSize=11, gridOpacity=0.2)
    )
    return chart.to_dict()

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
                        html.Button(
                            "›",
                            id="filter-toggle-btn",
                            n_clicks=0,
                            title="Expand filters",
                            className="filter-toggle-btn",
                        ),
                        html.Div(
                            style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "gap": "8px"},
                            children=[
                                html.Div("Filters", style={**SECTION_TITLE, "color": TITLE_GREEN, "marginBottom": 0}),
                                html.Button(
                                    "Reset All",
                                    id="reset-all-btn",
                                    n_clicks=0,
                                    style={
                                        "border": "1px solid #dbe5df",
                                        "backgroundColor": "#f7f9f8",
                                        "color": "#60756a",
                                        "fontSize": "10px",
                                        "fontWeight": "600",
                                        "padding": "4px 8px",
                                        "borderRadius": "8px",
                                        "cursor": "pointer",
                                        "whiteSpace": "nowrap",
                                    },
                                ),
                            ],
                        ),

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
                            style={"fontSize": "12px"},
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
                            labelStyle={"display": "flex", "alignItems": "center", "gap": "7px", "fontSize": "13px"},
                            inputStyle={"accentColor": GREEN},
                        ),

                        html.Div("Liked", style=FILTER_LABEL),
                        dcc.Checklist(
                            id="liked-only",
                            options=[{"label": " Liked only", "value": "liked"}],
                            value=[],
                            style={"rowGap": "5px", "display": "grid"},
                            labelStyle={"display": "flex", "alignItems": "center", "gap": "7px", "fontSize": "13px"},
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
                            style={"fontSize": "12px", "color": "#888", "marginTop": "12px",
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
                        dcc.Tabs(
                            id="main-view-tabs",
                            value="insights",
                            style={"marginBottom": "6px"},
                            children=[
                                dcc.Tab(
                                    label="Insights",
                                    value="insights",
                                    style={"fontSize": "11px", "padding": "6px 10px", "borderColor": "#d7e7dd"},
                                    selected_style={
                                        "fontSize": "11px",
                                        "padding": "6px 10px",
                                        "borderColor": "#d7e7dd",
                                        "backgroundColor": "#eef8f1",
                                        "color": "#2d6a4f",
                                        "fontWeight": "700",
                                    },
                                    children=html.Div(
                                        id="insights-pane",
                                        className="main-tab-pane",
                                        children=[
                                            html.Div(
                                                id="scatter-card",
                                                style={
                                                    **CARD,
                                                    "marginBottom": 0,
                                                    "height": "calc(var(--left-panel-h, var(--viewport-h, 0px)) - var(--insights-top-offset, 106px))",
                                                    "minHeight": "0",
                                                },
                                                children=[
                                                    html.Div(
                                                        style={"display": "flex", "justifyContent": "space-between", "alignItems": "flex-start"},
                                                        children=[
                                                            html.Div([
                                                                html.H4("Energy vs Valence", style=SECTION_TITLE),
                                                                html.Div(id="scatter-meta", style={"fontSize": "10px", "color": "#888", "marginBottom": "5px"}),
                                                                html.Div(
                                                                    "Tip: click one point to open profile; brush an area to define selected tracks.",
                                                                    style={"fontSize": "9px", "color": "#8a98a6", "marginBottom": "4px"},
                                                                ),
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
                                                    html.Div(
                                                        style={"display": "flex", "gap": "8px", "marginTop": "8px", "flexWrap": "wrap"},
                                                        children=[
                                                            html.Button(
                                                                "Top Genres",
                                                                id="show-genre-card-btn",
                                                                n_clicks=0,
                                                                className="insights-detail-btn",
                                                                style={
                                                                    "border": "1px solid #2f7f58",
                                                                    "backgroundColor": "#2f7f58",
                                                                    "color": "#ffffff",
                                                                    "fontSize": "11px",
                                                                    "fontWeight": "700",
                                                                    "padding": "6px 11px",
                                                                    "borderRadius": "10px",
                                                                    "cursor": "pointer",
                                                                    "boxShadow": "0 2px 8px rgba(47, 127, 88, 0.28)",
                                                                },
                                                            ),
                                                            html.Button(
                                                                "Feature Density",
                                                                id="show-density-card-btn",
                                                                n_clicks=0,
                                                                className="insights-detail-btn",
                                                                style={
                                                                    "border": "1px solid #2f7f58",
                                                                    "backgroundColor": "#2f7f58",
                                                                    "color": "#ffffff",
                                                                    "fontSize": "11px",
                                                                    "fontWeight": "700",
                                                                    "padding": "6px 11px",
                                                                    "borderRadius": "10px",
                                                                    "cursor": "pointer",
                                                                    "boxShadow": "0 2px 8px rgba(47, 127, 88, 0.28)",
                                                                },
                                                            ),
                                                            html.Button(
                                                                "Avg Audio Profile",
                                                                id="show-audio-card-btn",
                                                                n_clicks=0,
                                                                className="insights-detail-btn",
                                                                style={
                                                                    "border": "1px solid #2f7f58",
                                                                    "backgroundColor": "#2f7f58",
                                                                    "color": "#ffffff",
                                                                    "fontSize": "11px",
                                                                    "fontWeight": "700",
                                                                    "padding": "6px 11px",
                                                                    "borderRadius": "10px",
                                                                    "cursor": "pointer",
                                                                    "boxShadow": "0 2px 8px rgba(47, 127, 88, 0.28)",
                                                                },
                                                            ),
                                                            html.Button(
                                                                "Popularity Histogram",
                                                                id="show-pop-hist-card-btn",
                                                                n_clicks=0,
                                                                className="insights-detail-btn",
                                                                style={
                                                                    "border": "1px solid #2f7f58",
                                                                    "backgroundColor": "#2f7f58",
                                                                    "color": "#ffffff",
                                                                    "fontSize": "11px",
                                                                    "fontWeight": "700",
                                                                    "padding": "6px 11px",
                                                                    "borderRadius": "10px",
                                                                    "cursor": "pointer",
                                                                    "boxShadow": "0 2px 8px rgba(47, 127, 88, 0.28)",
                                                                },
                                                            ),
                                                            html.Button(
                                                                "Tempo Distribution",
                                                                id="show-genre-mix-card-btn",
                                                                n_clicks=0,
                                                                className="insights-detail-btn",
                                                                style={
                                                                    "border": "1px solid #2f7f58",
                                                                    "backgroundColor": "#2f7f58",
                                                                    "color": "#ffffff",
                                                                    "fontSize": "11px",
                                                                    "fontWeight": "700",
                                                                    "padding": "6px 11px",
                                                                    "borderRadius": "10px",
                                                                    "cursor": "pointer",
                                                                    "boxShadow": "0 2px 8px rgba(47, 127, 88, 0.28)",
                                                                },
                                                            ),
                                                            html.Button(
                                                                "Mood Quadrant",
                                                                id="show-delta-card-btn",
                                                                n_clicks=0,
                                                                className="insights-detail-btn",
                                                                style={
                                                                    "border": "1px solid #2f7f58",
                                                                    "backgroundColor": "#2f7f58",
                                                                    "color": "#ffffff",
                                                                    "fontSize": "11px",
                                                                    "fontWeight": "700",
                                                                    "padding": "6px 11px",
                                                                    "borderRadius": "10px",
                                                                    "cursor": "pointer",
                                                                    "boxShadow": "0 2px 8px rgba(47, 127, 88, 0.28)",
                                                                },
                                                            ),
                                                        ],
                                                    ),
                                                    html.Div(
                                                        style={
                                                            "display": "grid",
                                                            "gridTemplateColumns": "30% 70%",
                                                            "gap": "10px",
                                                            "alignItems": "end",
                                                            "minHeight": "510px",
                                                            "marginTop": "6px",
                                                        },
                                                        children=[
                                                            html.Div(
                                                                id="insights-popup-column",
                                                                style={
                                                                    "minHeight": "420px",
                                                                    "display": "flex",
                                                                    "alignItems": "flex-start",
                                                                    "alignSelf": "start",
                                                                    "paddingTop": "10px",
                                                                },
                                                                children=[
                                                                    html.Div(
                                                                        id="insights-genre-card",
                                                                        style={**CARD, "marginBottom": 0, "minWidth": 0, "display": "none", "width": "100%"},
                                                                        children=[
                                                                            html.H4("Top Genres by Popularity", style=SECTION_TITLE),
                                                                            html.Div(
                                                                                style={"fontSize": "9px", "color": "#888", "marginBottom": "7px"},
                                                                                children="Top genres ranked by mean popularity; color indicates mean energy.",
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
                                                                        id="insights-audio-card",
                                                                        style={**CARD, "marginBottom": 0, "minWidth": 0, "display": "none", "width": "100%"},
                                                                        children=[
                                                                            html.H4("Avg Audio Profile", style=SECTION_TITLE),
                                                                            html.Div(
                                                                                style={"fontSize": "9px", "color": "#888", "marginBottom": "7px"},
                                                                                children="Mean values of key audio features for the current selection.",
                                                                            ),
                                                                            dvc.Vega(
                                                                                id="audio-profile",
                                                                                spec={},
                                                                                opt={"renderer": "svg", "actions": False},
                                                                                style={"width": "100%", "maxWidth": "100%", "minWidth": 0, "overflow": "hidden"},
                                                                            ),
                                                                        ],
                                                                    ),
                                                                    html.Div(
                                                                        id="insights-density-card",
                                                                        style={**CARD, "display": "none", "width": "100%"},
                                                                        children=[
                                                                            html.H4("Feature Density — Selected Tracks", style=SECTION_TITLE),
                                                                            html.Div(
                                                                                style={"fontSize": "9px", "color": "#888", "marginBottom": "7px"},
                                                                                children="Overlaid density curves of key audio features in the selection.",
                                                                            ),
                                                                            html.Div(
                                                                                dvc.Vega(
                                                                                    id="distribution",
                                                                                    spec={},
                                                                                    opt={"renderer": "svg", "actions": False},
                                                                                    style={"width": "100%", "maxWidth": "100%"},
                                                                                ),
                                                                                style={"display": "flex", "justifyContent": "center"},
                                                                            ),
                                                                        ],
                                                                    ),
                                                                    html.Div(
                                                                        id="insights-genre-mix-card",
                                                                        style={**CARD, "display": "none", "width": "100%"},
                                                                        children=[
                                                                            html.H4("Tempo Distribution", style=SECTION_TITLE),
                                                                            html.Div(
                                                                                style={"fontSize": "9px", "color": "#888", "marginBottom": "7px"},
                                                                                children="Tempo (BPM) distribution for selected tracks, with median reference line.",
                                                                            ),
                                                                            dvc.Vega(
                                                                                id="tempo-dist",
                                                                                spec={},
                                                                                opt={"renderer": "svg", "actions": False},
                                                                                style={"width": "100%", "maxWidth": "100%", "minWidth": 0, "overflow": "hidden"},
                                                                            ),
                                                                        ],
                                                                    ),
                                                                    html.Div(
                                                                        id="insights-pop-hist-card",
                                                                        style={**CARD, "display": "none", "width": "100%"},
                                                                        children=[
                                                                            html.H4("Popularity Histogram", style=SECTION_TITLE),
                                                                            html.Div(
                                                                                style={"fontSize": "9px", "color": "#888", "marginBottom": "7px"},
                                                                                children="Histogram of popularity scores (0-100) for the current selection.",
                                                                            ),
                                                                            dvc.Vega(
                                                                                id="pop-hist",
                                                                                spec={},
                                                                                opt={"renderer": "svg", "actions": False},
                                                                                style={"width": "100%", "maxWidth": "100%", "minWidth": 0, "overflow": "hidden"},
                                                                            ),
                                                                        ],
                                                                    ),
                                                                    html.Div(
                                                                        id="insights-delta-card",
                                                                        style={**CARD, "display": "none", "width": "100%"},
                                                                        children=[
                                                                            html.H4("Mood Quadrant", style=SECTION_TITLE),
                                                                            html.Div(
                                                                                style={"fontSize": "9px", "color": "#888", "marginBottom": "7px"},
                                                                                children="5x5 energy-valence heatmap showing mood concentration across the selection.",
                                                                            ),
                                                                            dvc.Vega(
                                                                                id="mood-quad",
                                                                                spec={},
                                                                                opt={"renderer": "svg", "actions": False},
                                                                                style={"width": "100%", "maxWidth": "100%", "minWidth": 0, "overflow": "hidden"},
                                                                            ),
                                                                        ],
                                                                    ),
                                                                ],
                                                            ),
                                                            html.Div(
                                                                dvc.Vega(
                                                                    id="scatter",
                                                                    spec={},
                                                                    opt={"renderer": "svg", "actions": False},
                                                                    signalsToObserve=[
                                                                        "brush_selection",
                                                                        "track_pick",
                                                                        "track_pick_tuple",
                                                                        "track_pick_toggle",
                                                                        "track_pick_modify",
                                                                        "track_pick_store",
                                                                    ],
                                                                    style={"width": "auto", "maxWidth": "100%", "display": "inline-block"},
                                                                ),
                                                                style={
                                                                    "display": "flex",
                                                                    "justifyContent": "flex-end",
                                                                    "alignItems": "flex-end",
                                                                    "width": "100%",
                                                                    "minHeight": "510px",
                                                                    "paddingBottom": "10px",
                                                                },
                                                            ),
                                                        ],
                                                    ),
                                            ],
                                        ),
                                        ],
                                    ),
                                ),
                                dcc.Tab(
                                    label="Track List",
                                    value="tracklist",
                                    style={"fontSize": "11px", "padding": "6px 10px", "borderColor": "#d7e7dd"},
                                    selected_style={
                                        "fontSize": "11px",
                                        "padding": "6px 10px",
                                        "borderColor": "#d7e7dd",
                                        "backgroundColor": "#eef8f1",
                                        "color": "#2d6a4f",
                                        "fontWeight": "700",
                                    },
                                    children=html.Div(
                                        id="tracklist-pane",
                                        className="main-tab-pane",
                                        children=[
                                            html.Div(
                                                style={**CARD, "minWidth": 0, "marginBottom": 0, "marginTop": "4px", "padding": "8px 10px"},
                                                children=[
                                                    html.Div(
                                                        "Click the star before Title to like/unlike a track.",
                                                        style={"fontSize": "9px", "color": "#888", "marginBottom": "4px"},
                                                    ),
                                                    html.Div(
                                                        id="song-list-container",
                                                        children=make_song_list_table(data.head(0), max_rows=0, liked_track_ids=[]),
                                                    ),
                                                ],
                                            ),
                                        ],
                                    ),
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
                                html.Div(
                                    style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "gap": "8px"},
                                    children=[
                                        html.H4("Track Profile", style={**SECTION_TITLE, "marginBottom": 0}),
                                        html.Button(
                                            "Compare: Off",
                                            id="compare-toggle-btn",
                                            n_clicks=0,
                                            style={
                                                "border": "1px solid #dbe5df",
                                                "backgroundColor": "#f7f9f8",
                                                "color": "#60756a",
                                                "fontSize": "10px",
                                                "fontWeight": "600",
                                                "padding": "4px 7px",
                                                "borderRadius": "8px",
                                                "cursor": "pointer",
                                                "whiteSpace": "nowrap",
                                            },
                                        ),
                                    ],
                                ),
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
            ],
        ),

        dcc.Store(id="brush-bounds-store"),
        dcc.Store(id="filtered-index-store", data=[]),
        dcc.Store(id="selected-index-store", data=[]),
        dcc.Store(id="selected-genres-store", data=[]),
        dcc.Store(id="liked-tracks-store", data=[], storage_type="local"),
        dcc.Store(id="selected-track-store", data=None),
        dcc.Store(id="scatter-genre-color-map-store", data={}),
        dcc.Store(id="filter-panel-open-store", data=False),
        dcc.Store(id="compare-mode-store", data=False),
        dcc.Store(id="locked-track-store", data=None),
        dcc.Store(id="main-view-prev-store", data="insights"),
        dcc.Store(id="insights-detail-store", data="density"),
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
    Output("filter-panel-open-store", "data"),
    Input("filter-toggle-btn", "n_clicks"),
    State("filter-panel-open-store", "data"),
    prevent_initial_call=True,
)
def toggle_filter_panel(_n_clicks, is_open):
    return not bool(is_open)


@callback(
    Output("left-panel", "className"),
    Output("filter-toggle-btn", "children"),
    Output("filter-toggle-btn", "title"),
    Input("filter-panel-open-store", "data"),
)
def render_filter_panel_state(is_open):
    if is_open:
        return "left-panel open", "‹", "Collapse filters"
    return "left-panel", "›", "Expand filters"


@callback(
    Output("keyword", "value", allow_duplicate=True),
    Output("selected-genres-store", "data", allow_duplicate=True),
    Output("genre-picker", "value", allow_duplicate=True),
    Output("explicit", "value", allow_duplicate=True),
    Output("liked-only", "value", allow_duplicate=True),
    Output("tempo-range", "value", allow_duplicate=True),
    Output("popularity-range", "value", allow_duplicate=True),
    Output("toolbox-mode", "value", allow_duplicate=True),
    Output("brush-bounds-store", "data", allow_duplicate=True),
    Output("selected-track-store", "data", allow_duplicate=True),
    Output("compare-mode-store", "data", allow_duplicate=True),
    Output("locked-track-store", "data", allow_duplicate=True),
    Output("similar-track-dropdown", "value", allow_duplicate=True),
    Output("main-view-tabs", "value", allow_duplicate=True),
    Output("insights-detail-store", "data", allow_duplicate=True),
    Input("reset-all-btn", "n_clicks"),
    prevent_initial_call=True,
)
def reset_all_controls(n_clicks):
    if not n_clicks:
        return (
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
        )
    return (
        "",
        [],
        None,
        "all",
        [],
        [TEMPO_MIN, TEMPO_MAX],
        [POP_MIN, POP_MAX],
        "brush",
        None,
        None,
        False,
        None,
        None,
        "insights",
        None,
    )


@callback(
    Output("insights-detail-store", "data"),
    Input("show-genre-card-btn", "n_clicks"),
    Input("show-audio-card-btn", "n_clicks"),
    Input("show-density-card-btn", "n_clicks"),
    Input("show-genre-mix-card-btn", "n_clicks"),
    Input("show-pop-hist-card-btn", "n_clicks"),
    Input("show-delta-card-btn", "n_clicks"),
    State("insights-detail-store", "data"),
    prevent_initial_call=True,
)
def choose_insights_detail(_genre_clicks, _audio_clicks, _density_clicks, _genre_mix_clicks, _pop_hist_clicks, _delta_clicks, current_value):
    trig = ctx.triggered_id
    mapping = {
        "show-genre-card-btn": "genre",
        "show-audio-card-btn": "audio",
        "show-density-card-btn": "density",
        "show-genre-mix-card-btn": "genre_mix",
        "show-pop-hist-card-btn": "pop_hist",
        "show-delta-card-btn": "delta",
    }
    picked = mapping.get(trig)
    if not picked:
        return no_update
    return None if current_value == picked else picked


@callback(
    Output("insights-genre-card", "style"),
    Output("insights-audio-card", "style"),
    Output("insights-density-card", "style"),
    Output("insights-genre-mix-card", "style"),
    Output("insights-pop-hist-card", "style"),
    Output("insights-delta-card", "style"),
    Input("insights-detail-store", "data"),
)
def render_insights_detail_cards(active_detail):
    popup_base = {
        "width": "100%",
        "boxShadow": "0 4px 14px rgba(0,0,0,0.12)",
    }
    hidden = {**popup_base, "display": "none"}
    active_popup = {
        **popup_base,
        "animation": "insights-slit-pop 300ms cubic-bezier(0.16, 1, 0.3, 1)",
        "transformOrigin": "center top",
    }
    genre_style = hidden
    audio_style = hidden
    density_style = hidden
    genre_mix_style = hidden
    pop_hist_style = hidden
    delta_style = hidden

    if active_detail == "genre":
        genre_style = {**CARD, "marginBottom": 0, "minWidth": 0, **active_popup}
    elif active_detail == "audio":
        audio_style = {**CARD, "marginBottom": 0, "minWidth": 0, **active_popup}
    elif active_detail == "density":
        density_style = {**CARD, **active_popup}
    elif active_detail == "genre_mix":
        genre_mix_style = {**CARD, **active_popup}
    elif active_detail == "pop_hist":
        pop_hist_style = {**CARD, **active_popup}
    elif active_detail == "delta":
        delta_style = {**CARD, **active_popup}

    return genre_style, audio_style, density_style, genre_mix_style, pop_hist_style, delta_style


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
    Output("filtered-index-store", "data"),
    Input("keyword", "value"),
    Input("selected-genres-store", "data"),
    Input("explicit", "value"),
    Input("liked-only", "value"),
    Input("tempo-range", "value"),
    Input("popularity-range", "value"),
    Input("liked-tracks-store", "data"),
)
def update_filtered_index_store(keyword, genre_values, explicit_mode, liked_filter_values, tempo_bounds, pop_bounds, liked_tracks):
    filtered_df = _compute_filtered_df(
        keyword,
        genre_values,
        explicit_mode,
        tempo_bounds,
        pop_bounds,
        liked_filter_values,
        liked_tracks,
    )
    return filtered_df.index.tolist()


@callback(
    Output("scatter", "spec"),
    Output("scatter-meta", "children"),
    Output("header-stats", "children"),
    Output("filter-hint", "children"),
    Output("brush-bounds-store", "data"),
    Output("selected-index-store", "data"),
    Output("scatter-genre-color-map-store", "data"),
    Input("toolbox-mode", "value"),
    Input("filtered-index-store", "data"),
    Input("scatter", "signalData"),
    State("brush-bounds-store", "data"),
    State("selected-index-store", "data"),
)
def update_scatter_and_stores(
    mode,
    filtered_index_data,
    signal_data,
    previous_bounds,
    previous_selected_index,
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
            return no_update, no_update, no_update, no_update, previous_bounds, no_update, no_update

    filtered_df = _df_from_filtered_index(filtered_index_data)

    brush = (signal_data or {}).get("brush_selection")
    if brush and "energy" in brush and "valence" in brush:
        e0, e1 = brush["energy"]
        v0, v1 = brush["valence"]
        bounds = {"energy": [e0, e1], "valence": [v0, v1]}
        selected_df = _compute_selected_df(filtered_df, bounds)
    else:
        # Clearing brush should immediately clear selection:
        # selected set falls back to all filtered tracks.
        bounds = None
        selected_df = filtered_df

    n_total = len(data)
    n_filtered = len(filtered_df)
    n_selected = len(selected_df)

    stats_children = [
        html.Span(f"Total  {n_total:,}", style={**BADGE, "backgroundColor": "#e8f5e9", "color": "#2d6a4f"}),
        html.Span(f"Filtered  {n_filtered:,}", style={**BADGE, "backgroundColor": "#fff3e0", "color": "#a0522d"}),
    ]
    if n_selected != n_filtered:
        stats_children.append(
            html.Span(f"Selected  {n_selected:,}", style={**BADGE, "backgroundColor": "#e3f2fd", "color": "#1565c0"})
        )

    filter_hint = [
        html.Div(f"{n_filtered:,} tracks after filters", style={"marginBottom": "2px"}),
        html.Div(
            (f"{n_selected:,} tracks selected (brush active)" if bounds and (n_selected != n_filtered) else "Brush on scatterplot to select."),
            style={"color": GREEN if bounds and (n_selected != n_filtered) else "#888"},
        ),
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
        genre_color_map_out = no_update
    else:
        scatter_max_points = 450 if n_filtered > 60000 else 500
        chart, scatter_meta = make_scatter(
            filtered_df,
            mode=mode,
            max_points=scatter_max_points,
            topk_genres=10,
            selection_name="brush_selection",
            point_selection_name="track_pick",
            width=470,
            height=470,
        )
        spec_out = chart.to_dict()
        genre_color_map_out = _build_genre_color_map(scatter_meta.get("top_genres", []))
        bounds = None
        selected_df = filtered_df

    selected_index = selected_df.index.tolist() if selected_df is not None else []
    selected_out = no_update if list(previous_selected_index or []) == selected_index else selected_index

    if previous_bounds == bounds:
        bounds_out = no_update
    else:
        bounds_out = bounds

    return spec_out, meta_text, stats_children, filter_hint, bounds_out, selected_out, genre_color_map_out


@callback(
    Output("genre-bar", "spec"),
    Input("selected-index-store", "data"),
    Input("insights-detail-store", "data"),
)
def update_genre_bar(selected_index_data, _active_detail):
    if _active_detail != "genre":
        return no_update
    return _genre_bar_spec_cached(_selected_index_key(selected_index_data))


@callback(
    Output("distribution", "spec"),
    Input("selected-index-store", "data"),
    Input("insights-detail-store", "data"),
)
def update_distribution(selected_index_data, _active_detail):
    if _active_detail != "density":
        return no_update
    return _distribution_spec_cached(_selected_index_key(selected_index_data))


@callback(
    Output("audio-profile", "spec"),
    Input("selected-index-store", "data"),
    Input("insights-detail-store", "data"),
)
def update_audio_profile(selected_index_data, _active_detail):
    if _active_detail != "audio":
        return no_update
    return _audio_profile_spec_cached(_selected_index_key(selected_index_data))


@callback(
    Output("tempo-dist", "spec"),
    Input("selected-index-store", "data"),
    Input("insights-detail-store", "data"),
)
def update_tempo_distribution(selected_index_data, _active_detail):
    if _active_detail != "genre_mix":
        return no_update
    return _tempo_distribution_spec_cached(_selected_index_key(selected_index_data))


@callback(
    Output("pop-hist", "spec"),
    Input("selected-index-store", "data"),
    Input("insights-detail-store", "data"),
)
def update_popularity_histogram(selected_index_data, _active_detail):
    if _active_detail != "pop_hist":
        return no_update
    return _popularity_hist_spec_cached(_selected_index_key(selected_index_data))


@callback(
    Output("mood-quad", "spec"),
    Input("selected-index-store", "data"),
    Input("insights-detail-store", "data"),
)
def update_mood_quadrant(selected_index_data, _active_detail):
    if _active_detail != "delta":
        return no_update
    return _mood_quadrant_spec_cached(_selected_index_key(selected_index_data))


@callback(
    Output("song-list-container", "children"),
    Input("selected-index-store", "data"),
    Input("liked-tracks-store", "data"),
)
def update_song_list(selected_index_data, liked_tracks):
    df = _df_from_filtered_index(selected_index_data)
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
    payload = {}

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
                row_data = visible_rows[row_idx]
                track_id = str(row_data.get("track_id", "")).strip()
                payload = {
                    "track_name": row_data.get("track_name"),
                    "artists": row_data.get("artists"),
                    "track_genre": row_data.get("track_genre"),
                }
                source = "song-table"
    elif triggered == "scatter":
        extracted = _extract_track_payload_from_scatter_signal(signal_data) or {}
        row_id = str(extracted.get("_row_id", "")).strip()
        row_from_idx = _get_track_row_by_index(row_id) if row_id else None
        if row_from_idx is not None:
            track_id = str(row_from_idx.get("track_id", "")).strip()
            payload = {
                "row_index": int(row_id),
                "track_name": row_from_idx.get("track_name"),
                "artists": row_from_idx.get("artists"),
                "track_genre": row_from_idx.get("track_genre"),
            }
        else:
            track_id = str(extracted.get("track_id", "")).strip()
            payload = {
                "track_name": extracted.get("track_name"),
                "artists": extracted.get("artists"),
                "track_genre": extracted.get("track_genre"),
            }
        source = "scatter"

    if not track_id:
        return no_update
    if current_selected:
        same_track = str(current_selected.get("track_id")) == track_id
        prev_row = current_selected.get("row_index")
        new_row = payload.get("row_index")
        same_row = (prev_row is None and new_row is None) or (prev_row == new_row)
        if same_track and same_row:
            return no_update
    return {"track_id": track_id, "source": source, **payload}


@callback(
    Output("compare-mode-store", "data"),
    Output("locked-track-store", "data"),
    Input("compare-toggle-btn", "n_clicks"),
    State("compare-mode-store", "data"),
    State("selected-track-store", "data"),
    prevent_initial_call=True,
)
def toggle_compare_mode(_n, compare_mode, selected_track):
    is_on = bool(compare_mode)
    if not is_on:
        track_id = str((selected_track or {}).get("track_id", "")).strip()
        if not track_id:
            return no_update, no_update
        return True, dict(selected_track or {})
    return False, None


@callback(
    Output("compare-toggle-btn", "children"),
    Output("compare-toggle-btn", "style"),
    Input("compare-mode-store", "data"),
)
def render_compare_button(compare_mode):
    is_on = bool(compare_mode)
    base = {
        "border": "1px solid #dbe5df",
        "fontSize": "10px",
        "fontWeight": "600",
        "padding": "4px 7px",
        "borderRadius": "8px",
        "cursor": "pointer",
        "whiteSpace": "nowrap",
    }
    if is_on:
        return "Compare: On", {**base, "backgroundColor": "#e9f7ef", "color": "#2d6a4f", "border": "1px solid #bfe4cd"}
    return "Compare: Off", {**base, "backgroundColor": "#f7f9f8", "color": "#60756a"}


@callback(
    Output("main-view-prev-store", "data"),
    Output("insights-pane", "className"),
    Output("tracklist-pane", "className"),
    Input("main-view-tabs", "value"),
    State("main-view-prev-store", "data"),
)
def animate_main_tabs(current_tab, prev_tab):
    prev = str(prev_tab or "")
    curr = str(current_tab or "")

    insights_cls = "main-tab-pane"
    tracklist_cls = "main-tab-pane"

    if prev == "tracklist" and curr == "insights":
        insights_cls = "main-tab-pane anim-enter-left"
    elif prev == "insights" and curr == "tracklist":
        tracklist_cls = "main-tab-pane anim-enter-right"

    return curr or prev or "insights", insights_cls, tracklist_cls


@callback(
    Output("song-profile-container", "children"),
    Input("selected-track-store", "data"),
    Input("scatter-genre-color-map-store", "data"),
    Input("compare-mode-store", "data"),
    Input("locked-track-store", "data"),
    State("liked-tracks-store", "data"),
)
def render_song_profile(
    selected_track,
    genre_color_map,
    compare_mode,
    locked_track,
    liked_tracks,
):
    selected_id = str((selected_track or {}).get("track_id", "")).strip()
    locked_id = str((locked_track or {}).get("track_id", "")).strip()
    compare_on = bool(compare_mode)
    primary_track = (locked_track or {}) if (compare_on and locked_id) else (selected_track or {})
    track_id = str(primary_track.get("track_id", "")).strip()
    if not track_id:
        return html.Div("No song selected yet.", style={"fontSize": "12px", "color": "#9aa1ab"})

    primary_row_index = primary_track.get("row_index")
    row = _get_track_row_by_index(primary_row_index)
    if row is None:
        row = _get_track_row(
            track_id,
            track_name=primary_track.get("track_name"),
            artists=primary_track.get("artists"),
            track_genre=primary_track.get("track_genre"),
        )
    if row is None:
        return html.Div("Track not found in dataset.", style={"fontSize": "12px", "color": "#c00"})

    liked_set = {str(x) for x in (liked_tracks or [])}
    is_liked = track_id in liked_set
    genre_color = _color_for_genre(str(row.get("track_genre", "")), genre_color_map)

    compare_row = None
    compare_genre_color = None
    if compare_on and selected_id and selected_id != track_id:
        compare_row_index = (selected_track or {}).get("row_index")
        compare_row = _get_track_row_by_index(compare_row_index)
        if compare_row is None:
            compare_row = _get_track_row(
                selected_id,
                track_name=(selected_track or {}).get("track_name"),
                artists=(selected_track or {}).get("artists"),
                track_genre=(selected_track or {}).get("track_genre"),
            )
        if compare_row is not None:
            compare_genre_color = _color_for_genre(str(compare_row.get("track_genre", "")), genre_color_map)

    values = [float(row.get(c, 0) if pd.notna(row.get(c, np.nan)) else 0.0) for c in PROFILE_AXES]
    primary_key = tuple(round(v, 4) for v in values)
    fig_dict = copy.deepcopy(_build_primary_radar_dict(primary_key, str(genre_color), bool(compare_on)))
    has_compare = False
    if compare_row is not None:
        cvals = [float(compare_row.get(c, 0) if pd.notna(compare_row.get(c, np.nan)) else 0.0) for c in PROFILE_AXES]
        compare_key = tuple(round(v, 4) for v in cvals)
        fig_dict["data"].append(_build_compare_trace_dict(compare_key, str(compare_genre_color or "#666")))
        has_compare = True
    fig_dict.setdefault("layout", {})["showlegend"] = bool(has_compare)
    fig = go.Figure(fig_dict)

    pop = int(row["popularity"]) if pd.notna(row.get("popularity", np.nan)) else 0
    tempo = int(row["tempo"]) if pd.notna(row.get("tempo", np.nan)) else 0
    explicit_text = "Explicit" if bool(row.get("explicit", False)) else "Clean"
    pop_text = f"Pop {pop}"
    tempo_text = f"Tempo {tempo}"
    explicit_badge_text = explicit_text
    badge_font_size = "10px"
    left_col_flex = "0 0 22%"
    radar_width = "78%"
    if compare_row is not None:
        cpop = int(compare_row["popularity"]) if pd.notna(compare_row.get("popularity", np.nan)) else 0
        ctempo = int(compare_row["tempo"]) if pd.notna(compare_row.get("tempo", np.nan)) else 0
        cexplicit_text = "Explicit" if bool(compare_row.get("explicit", False)) else "Clean"
        pop_text = f"Pop {pop} vs {cpop}"
        tempo_text = f"Tempo {tempo} vs {ctempo}"
        explicit_badge_text = f"{explicit_text} vs {cexplicit_text}"
        badge_font_size = "9px"
        left_col_flex = "0 0 26%"
        radar_width = "74%"

    return html.Div(
        [
            html.Div(
                style={
                    "display": "grid",
                    "gridTemplateColumns": "minmax(0, 1fr) auto",
                    "alignItems": "start",
                    "columnGap": "8px",
                    "minHeight": "52px",
                },
                children=[
                    html.Div(
                        [
                            html.Div(str(row.get("track_name", "Unknown")), style={"fontSize": "15px", "fontWeight": "700", "color": "#1a1a2e"}),
                            html.Div(
                                f"{row.get('artists', 'Unknown')}  ·  {row.get('track_genre', 'Unknown')}",
                                style={"fontSize": "11px", "color": "#6b7280", "marginTop": "1px"},
                            ),
                            html.Div(
                                (
                                    f"Compare with: {compare_row.get('track_name', 'Unknown')}  ·  {compare_row.get('artists', 'Unknown')}"
                                    if compare_row is not None else ""
                                ),
                                style={
                                    "fontSize": "10px",
                                    "color": "#8a98a6",
                                    "marginTop": "2px",
                                    "fontStyle": "italic",
                                    "display": "block",
                                    "maxWidth": "100%",
                                    "whiteSpace": "nowrap",
                                    "overflow": "hidden",
                                    "textOverflow": "ellipsis",
                                    "height": "14px",
                                    "lineHeight": "14px",
                                },
                            ),
                        ],
                        style={"minWidth": 0, "flex": "1 1 auto", "overflow": "hidden"},
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
                                    html.Span(
                                        pop_text,
                                        style={
                                            **BADGE,
                                            "backgroundColor": "#e8f5e9",
                                            "color": "#2d6a4f",
                                            "fontSize": badge_font_size,
                                            "padding": "2px 6px",
                                            "whiteSpace": "nowrap",
                                        },
                                    ),
                                    html.Span(
                                        tempo_text,
                                        style={
                                            **BADGE,
                                            "backgroundColor": "#e7f0ff",
                                            "color": "#1d4ed8",
                                            "fontSize": badge_font_size,
                                            "padding": "2px 6px",
                                            "whiteSpace": "nowrap",
                                        },
                                    ),
                                    html.Span(
                                        explicit_badge_text,
                                        style={
                                            **BADGE,
                                            "backgroundColor": "#fff4e6",
                                            "color": "#9a3412",
                                            "fontSize": badge_font_size,
                                            "padding": "2px 6px",
                                            "whiteSpace": "nowrap",
                                        },
                                    ),
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
                            "flex": left_col_flex,
                        },
                    ),
                    dcc.Graph(
                        figure=fig,
                        config={"displayModeBar": False, "staticPlot": True},
                        style={"height": "152px", "width": radar_width, "minWidth": "240px", "marginLeft": "0px"},
                    ),
                ],
                style={"display": "flex", "flexWrap": "nowrap", "alignItems": "center", "gap": "2px"},
            ),
        ],
        style={"display": "grid", "rowGap": "4px"},
    )


@callback(
    Output({"type": "profile-like", "track_id": ALL}, "children"),
    Output({"type": "profile-like", "track_id": ALL}, "style"),
    Input("liked-tracks-store", "data"),
    State({"type": "profile-like", "track_id": ALL}, "id"),
)
def sync_profile_like_button(liked_tracks, profile_like_ids):
    ids = list(profile_like_ids or [])
    if not ids:
        return [], []

    liked_set = {str(x) for x in (liked_tracks or [])}
    children = []
    styles = []
    for item in ids:
        tid = str((item or {}).get("track_id", "")).strip()
        is_liked = tid in liked_set
        children.append("★" if is_liked else "☆")
        styles.append(
            {
                "border": "none",
                "background": "transparent",
                "cursor": "pointer",
                "fontSize": "20px",
                "lineHeight": "1",
                "padding": 0,
                "color": "#f4b400" if is_liked else "#bcc3cc",
            }
        )
    return children, styles


@callback(
    Output("similar-track-dropdown", "value", allow_duplicate=True),
    Input("profile-show-similar-btn", "n_clicks"),
    State("selected-track-store", "data"),
    State("compare-mode-store", "data"),
    State("locked-track-store", "data"),
    prevent_initial_call=True,
)
def push_profile_track_to_similar(_clicks, selected_track, compare_mode, locked_track):
    if _clicks in (None, 0):
        return no_update
    compare_on = bool(compare_mode)
    locked_id = str((locked_track or {}).get("track_id", "")).strip()
    selected_id = str((selected_track or {}).get("track_id", "")).strip()
    track_id = locked_id if (compare_on and locked_id) else selected_id
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
    Input("selected-index-store", "data"),
    Input("similar-track-dropdown", "search_value"),
    State("similar-track-dropdown", "value"),
)
def update_similar_dropdown(selected_index_data, search_value, current_value):
    selected_df = _df_from_filtered_index(selected_index_data)
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
    State("selected-index-store", "data"),
    Input("liked-tracks-store", "data"),
)
def update_similar_tracks(track_id, selected_index_data, liked_tracks):
    if not track_id:
        return html.Div(
            "Select a track above to discover audio-similar but underrated songs.",
            style={"fontSize": "12px", "color": "#aaa", "padding": "8px 0", "lineHeight": "1.5"},
        )

    selected_index_tuple = tuple(int(i) for i in (selected_index_data or []))
    if not selected_index_tuple:
        return html.Div("Reference track is not in current selection.", style={"fontSize": "12px", "color": "#c00"})

    track_id_str = str(track_id).strip()
    if not track_id_str:
        return html.Div("Track not found.", style={"fontSize": "12px", "color": "#c00"})

    # Cache pool track-id extraction and similarity ranking for common interactive pool sizes.
    if len(selected_index_tuple) <= 5000:
        pool_ids = _pool_track_ids_from_selected_index_cached(selected_index_tuple)
        if not pool_ids:
            return html.Div("Reference track is not in current selection.", style={"fontSize": "12px", "color": "#c00"})
        sim_out = _compute_similar_records_cached(track_id_str, pool_ids)
    else:
        pool = _df_from_filtered_index(selected_index_tuple)
        if pool is None or len(pool) == 0:
            return html.Div("Reference track is not in current selection.", style={"fontSize": "12px", "color": "#c00"})
        sim_out = _compute_similar_records_from_pool(pool, track_id_str)

    if sim_out.get("status") == "missing":
        return html.Div("Selected data missing required columns.", style={"fontSize": "12px", "color": "#c00"})
    if sim_out.get("status") == "ref_not_in_pool":
        return html.Div("Reference track is not in current selection.", style={"fontSize": "12px", "color": "#c00"})
    if sim_out.get("status") != "ok":
        return html.Div("Track not found.", style={"fontSize": "12px", "color": "#c00"})

    ref_name = sim_out.get("ref_name", "Unknown")
    ref_pop = int(sim_out.get("ref_pop", 0))
    records = sim_out.get("records", tuple())
    if not records:
        return html.Div("No similar lower-popularity tracks found.", style={"fontSize": "12px", "color": "#888"})

    candidates = pd.DataFrame(
        records,
        columns=["track_id", "track_name", "artists", "track_genre", "popularity", "energy", "valence", "danceability"],
    )
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
                f"Similar to: {ref_name} (pop {ref_pop})",
                style={"fontSize": "11px", "color": "#888", "marginBottom": "6px",
                       "fontStyle": "italic", "borderLeft": f"3px solid {GREEN}",
                       "paddingLeft": "8px"},
            ),
            html.Div(rows, style={"borderRadius": "10px", "border": "1px solid #f0f2f5", "overflow": "hidden"}),
        ]
    )


if __name__ == "__main__":
    app.run(debug=True)


