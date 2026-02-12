from dash import Dash, html
import pandas as pd
from pathlib import Path
import altair as alt

# importing data, note that this is raw data for now
# please change this after data is processed
ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "raw" / "dataset.csv"

data = pd.read_csv(DATA_PATH)

#initializing app
app = Dash(__name__)

#style setters, please change the argument value to set the style of each sections
PAGE = {
    "fontFamily" : "system-ui, -apple-system, Segoe UI, Roboto, Arial",
    "backgroundColor": "#f6f7f6",
    "minHeight": "100vh",
    "padding": "0px",
}

HEADER = {
    "backgroundColor":"white",
    "borderRadius": "12px",
    "padding": "16px 20px",
    "marginBottom": "16px",
    "border": "1px solid #e9e9ef"
}

#This is for the overall structure setting
GRID = {
    "display": "grid",
    "gridTemplateColumns": "280px 1fr 320px", #change here to set the size of each column
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
    "fontSize": "14px"
}

# This is only a test plot as placeholder

sample_data=data.sample(n=300,random_state=42)

Scatter = alt.Chart(
        sample_data
    ).mark_point(
        opacity=0.5
    ).encode(
        x=alt.X("energy:Q",title="Energy"),
        y=alt.Y("valence:Q",title="Valence"),
        color=alt.Color("track_genre:N",title="Genre",legend=None),
        size=alt.Size("popularity:Q", title="Popularity", scale=alt.Scale(range=[20,200])),
        tooltip=["track_name:N", "artists:N", "track_genre:N", "popularity:Q"]
    ).properties(width=480,height=400).interactive()

Scatter = Scatter.configure(
    autosize=alt.AutoSizeParams(type="fit", contains="padding")
).interactive()

#all placeholders should eventually be replaved by features
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
                            "Filter Placeholder",
                            style={**PLACEHOLDER, "height": "1000px"}
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
                                            srcDoc=Scatter.to_html(),
                                            style={
                                                "width": "100%",
                                                "height": "100%",
                                                "border": "0",
                                            },
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
                        html.Div(
                            "Comparer Placeholder",
                            style={**PLACEHOLDER, "height": "300px"}
                        ),
                        html.Div(
                            "Recommandation Placeholder",
                            style={**PLACEHOLDER, "height": "600px"}
                        ),
                    ],
                ),
            ],
        ),
    ],
)


if __name__=="__main__":
    app.run(debug=True)

