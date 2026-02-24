# charts/song_list.py
from __future__ import annotations

import pandas as pd
from dash import dash_table


def make_song_list_table(
    df: pd.DataFrame,
    *,
    max_rows: int = 5000,
) -> dash_table.DataTable:
    """
    Create a sortable Dash DataTable for track listing.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataset (already filtered/selected).
    max_rows : int
        Limit rows rendered for performance.
    table_height_px : int
        Fixed height with vertical scroll.

    Returns
    -------
    dash_table.DataTable
    """
    # Choose columns (only keep what you want to show)
    # Adjust these names if your dataset uses different ones.
    wanted = [
        "track_name",
        "artists",
        "track_genre",
        "popularity",
        "energy",
        "valence",
        "danceability",
    ]
    cols = [c for c in wanted if c in df.columns]

    # Ensure we don't crash when df is empty
    if df is None or len(df) == 0 or len(cols) == 0:
        data = []
    else:
        view = df[cols].copy()

        # Safe numeric rounding for nicer display
        for c in ["energy", "valence", "danceability"]:
            if c in view.columns:
                view[c] = pd.to_numeric(view[c], errors="coerce").round(3)

        if "popularity" in view.columns:
            view["popularity"] = pd.to_numeric(view["popularity"], errors="coerce").fillna(0).astype(int)

        data = view.head(max_rows).to_dict("records")

    # Column definitions (with types for better sorting)
    column_defs = []
    for c in cols:
        if c in {"popularity"}:
            column_defs.append({"name": "Popularity", "id": c, "type": "numeric"})
        elif c in {"energy", "valence", "danceability"}:
            column_defs.append({"name": c.capitalize(), "id": c, "type": "numeric"})
        elif c == "track_name":
            column_defs.append({"name": "Title", "id": c, "type": "text"})
        elif c == "artists":
            column_defs.append({"name": "Artist", "id": c, "type": "text"})
        elif c == "track_genre":
            column_defs.append({"name": "Genre", "id": c, "type": "text"})
        else:
            column_defs.append({"name": c, "id": c})

    # Popularity as a "bar" using DataTable style_data_conditional
    style_conditional = []
    if "popularity" in cols:
        # Create a simple horizontal bar via background gradient
        # Works because popularity is 0-100
        style_conditional.extend(
            [
                {
                    "if": {"column_id": "popularity"},
                    "textAlign": "left",
                    "padding": "6px 10px",
                },
                # Gradient bar per cell
                # Dash DataTable supports `filter_query` rules; we use ranges.
            ]
        )

        # 0..100 step rules (coarse, but good enough visually)
        for p in range(0, 101, 5):
            style_conditional.append(
                {
                    "if": {"filter_query": f"{{popularity}} >= {p}", "column_id": "popularity"},
                    "background": f"linear-gradient(90deg, #4c7dff {p}%, transparent {p}%)",
                }
            )

    table = dash_table.DataTable(
        id="song-table",
        data=data,
        columns=column_defs,
        sort_action="native",        # <- click headers to sort
        sort_mode="multi",           # <- allow multi-column sort with shift-click
        page_action="native",
        page_size=10,          # <- use scroll instead of pages
        style_table={
            "width": "100%",
            "overflowX": "auto",
            "borderRadius": "0px",
            "border": "1px solid #e9e9ef",
        },
        style_header={
            "fontWeight": "600",
            "backgroundColor": "#39d3ee8d",
            "borderBottom": "1px solid #e9e9ef",
            "padding": "10px",
            "fontSize": "9px",
        },
        style_cell={
            "padding": "9px",
            "fontSize": "9px",
            "backgroundColor": "white",
            "borderBottom": "1px solid #f0f0f6",
            "whiteSpace": "nowrap",
            "overflow": "hidden",
            "textOverflow": "ellipsis",
            "maxWidth": 0,
        },
        style_data_conditional=style_conditional,
        tooltip_data=[
            {k: {"value": str(v), "type": "markdown"} for k, v in row.items()} for row in data
        ],
        tooltip_duration=None,
    )
    return table