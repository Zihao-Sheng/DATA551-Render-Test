# charts/song_list.py
from __future__ import annotations

import pandas as pd
from dash import dash_table


def make_song_list_table(
    df: pd.DataFrame,
    *,
    max_rows: int = 5000,
    liked_track_ids: list[str] | None = None,
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
    liked_set = {str(x) for x in (liked_track_ids or [])}

    wanted = [
        "track_id",
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

        if "track_id" in view.columns:
            view["track_id"] = view["track_id"].astype(str)

        # A clickable star column for like/unlike actions.
        view.insert(0, "liked", view["track_id"].map(lambda tid: "★" if tid in liked_set else "☆"))
        data = view.head(max_rows).to_dict("records")

    # Column definitions (with types for better sorting)
    column_defs = []
    display_cols = ["liked"] + cols
    for c in display_cols:
        if c == "track_id":
            column_defs.append({"name": "track_id", "id": c, "type": "text"})
        elif c == "liked":
            column_defs.append({"name": "★", "id": c, "type": "text"})
        elif c in {"popularity"}:
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

    # Visual polish to match dashboard cards
    style_conditional = [
        {"if": {"row_index": "odd"}, "backgroundColor": "#fbfcfd"},
        {"if": {"state": "active"}, "backgroundColor": "#eef8f1", "border": "1px solid #b9e3c6"},
        {"if": {"state": "selected"}, "backgroundColor": "#e6f5eb", "border": "1px solid #8fd3a7"},
        {"if": {"column_id": "liked"}, "textAlign": "center", "fontSize": "16px", "padding": "0"},
        {"if": {"filter_query": "{liked} = '★'"}, "column_id": "liked", "color": "#f4b400"},
        {"if": {"column_id": "track_name"}, "fontWeight": "600", "color": "#1f2937"},
        {"if": {"column_id": "artists"}, "color": "#4b5563"},
    ]
    if "popularity" in cols:
        # Replicate compact in-cell progress bars (no visible numbers)
        style_conditional.extend(
            [
                {
                    "if": {"column_id": "popularity"},
                    "textAlign": "left",
                    "color": "transparent",
                    "fontSize": "0px",
                    "padding": "4px 6px",
                    "backgroundColor": "white",
                    "backgroundRepeat": "no-repeat",
                    "backgroundPosition": "center",
                    "backgroundSize": "100% 8px",
                },
            ]
        )
        for p in range(0, 101, 5):
            end = 12 + int(p * 0.76)  # keep left/right inset inside the cell
            style_conditional.append(
                {
                    "if": {"filter_query": f"{{popularity}} >= {p}", "column_id": "popularity"},
                    "backgroundImage": (
                        f"linear-gradient(90deg, "
                        f"transparent 0%, "
                        f"transparent 8%, "
                        f"#67b567 8%, "
                        f"#67b567 {end}%, "
                        f"#dce8dc {end}%, "
                        f"#dce8dc 92%, "
                        f"transparent 92%, "
                        f"transparent 100%)"
                    ),
                }
            )

    table = dash_table.DataTable(
        id="song-table",
        data=data,
        columns=column_defs,
        hidden_columns=["track_id"],
        sort_action="native",        # <- click headers to sort
        sort_mode="multi",           # <- allow multi-column sort with shift-click
        page_action="native",
        page_size=15,          # <- use scroll instead of pages
        fill_width=True,
        style_as_list_view=True,
        style_table={
            "width": "100%",
            "maxWidth": "1050px",
            "margin": "0 auto",
            "overflowX": "hidden",
            "borderRadius": "2px",
            "border": "1px solid #d7dde6",
        },
        style_header={
            "fontFamily": "'Segoe UI', system-ui, -apple-system, Roboto, Arial",
            "fontWeight": "700",
            "backgroundColor": "#edf1f4",
            "color": "#1f2937",
            "borderBottom": "1px solid #d7dde6",
            "padding": "10px 10px",
            "fontSize": "12px",
            "letterSpacing": "0.1px",
            "whiteSpace": "nowrap",
            "textOverflow": "ellipsis",
            "overflow": "hidden",
        },
        style_cell={
            "padding": "6px 6px",
            "fontSize": "11px",
            "backgroundColor": "white",
            "borderBottom": "1px solid #f1f5f9",
            "whiteSpace": "nowrap",
            "overflow": "hidden",
            "textOverflow": "ellipsis",
            "minWidth": "80px",
            "width": "80px",
            "maxWidth": "80px",
        },
        style_cell_conditional=[
            {"if": {"column_id": "liked"}, "width": "42px", "minWidth": "42px", "maxWidth": "42px"},
            {"if": {"column_id": "track_name"}, "width": "180px", "minWidth": "180px", "maxWidth": "180px"},
            {"if": {"column_id": "artists"}, "width": "220px", "minWidth": "220px", "maxWidth": "220px"},
            {"if": {"column_id": "track_genre"}, "width": "130px", "minWidth": "130px", "maxWidth": "130px"},
            {"if": {"column_id": "popularity"}, "width": "110px", "minWidth": "110px", "maxWidth": "110px"},
            {"if": {"column_id": "energy"}, "width": "85px", "minWidth": "85px", "maxWidth": "85px"},
            {"if": {"column_id": "valence"}, "width": "85px", "minWidth": "85px", "maxWidth": "85px"},
            {"if": {"column_id": "danceability"}, "width": "100px", "minWidth": "100px", "maxWidth": "100px"},
        ],
        style_data_conditional=style_conditional,
        css=[
            {"selector": ".dash-spreadsheet-menu", "rule": "display:flex; justify-content:center;"},
            {"selector": ".previous-next-container", "rule": "float:none; margin: 0 auto;"},
        ],
        tooltip_data=[
            {k: {"value": str(v), "type": "markdown"} for k, v in row.items()} for row in data
        ],
        tooltip_duration=None,
    )
    return table
