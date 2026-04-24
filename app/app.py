import dash
from dash import dcc, html, Input, Output, State, callback_context, no_update
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import base64, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_processing import (
    load_and_process, score_to_color, score_to_grade,
    DOMAIN_COLORS, BADGE_RULES, get_country_name
)

# ── Load data ─────────────────────────────────────────────────────────────────
DATA        = load_and_process()
hierarchy   = DATA["hierarchy"]
metadata_df = DATA["metadata"]
df_sub      = DATA["df_sub"]
df_dom      = DATA["df_dom"]
df_comp     = DATA["df_composite"]
df_full     = DATA["df_full"]
df_raw      = DATA["df_raw"]
badges_map  = DATA["badges"]

COUNTRIES   = df_comp["Country"].tolist()
DOMAIN_COLS = [c for c in df_dom.columns  if c not in ("Country","CountryName","ISO")]
SUB_COLS    = [c for c in df_sub.columns  if c not in ("Country","CountryName","ISO")]
BADGE_BY_ID = {b["id"]: b for b in BADGE_RULES}
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Mobile-aware chart heights ────────────────────────────────────────────────
# Plotly charts use config responsive=True + we set autosize in layout

# ── Chart helpers ─────────────────────────────────────────────────────────────

def build_leaderboard():
    df = df_comp.sort_values("Composite_Index", ascending=False).reset_index(drop=True)

    # EU baseline for arrow indicators
    eu_row   = df_comp[df_comp["Country"] == "EU"]
    eu_score = eu_row["Composite_Index"].values[0] if not eu_row.empty else None

    rows = []
    for i, row in df.iterrows():
        rank  = i + 1
        medal = {1:"🥇", 2:"🥈", 3:"🥉"}.get(rank, str(rank))
        color = score_to_color(row["Composite_Index"])
        chips = [
            html.Span(
                BADGE_BY_ID[b]["label"],
                style={"backgroundColor": BADGE_BY_ID[b]["color"],
                       "color":"#fff","borderRadius":"10px","padding":"2px 6px",
                       "fontSize":"0.68rem","marginRight":"3px","display":"inline-block",
                       "marginBottom":"2px"}
            )
            for b in badges_map.get(row["Country"], [])
        ]

        # EU comparison arrow
        if eu_score is not None and row["Country"] != "EU":
            diff  = row["Composite_Index"] - eu_score
            arrow = html.Span(
                f" ▲ +{diff:.2f}" if diff >= 0 else f" ▼ {diff:.2f}",
                style={"fontSize":"0.68rem","fontWeight":"700",
                       "color":"#2e7d32" if diff >= 0 else "#c62828",
                       "marginLeft":"4px"}
            )
        else:
            arrow = html.Span(" EU avg", style={"fontSize":"0.65rem","color":"#888","marginLeft":"4px"})

        rows.append(
            dbc.ListGroupItem(
                dbc.Row([
                    dbc.Col(html.Span(medal, style={"fontSize":"1.2rem"}), width=1),
                    dbc.Col([
                        html.Div([
                            html.Strong(row["CountryName"], style={"fontSize":"0.9rem"}),
                            arrow,
                        ], style={"marginBottom":"2px"}),
                        html.Div(chips, style={"lineHeight":"1.6"}),
                    ], width=8),
                    dbc.Col(
                        html.Span(f"{row['Composite_Index']:.2f}",
                                  className="lb-score",
                                  style={"backgroundColor":color,"color":"#fff",
                                         "borderRadius":"8px","padding":"3px 8px",
                                         "fontWeight":"700","fontSize":"0.82rem"}),
                        width=3, className="text-end"
                    ),
                ], align="center", className="g-1"),
                id={"type":"leaderboard-item","index":row["Country"]},
                action=True,
                style={"cursor":"pointer","borderLeft":f"4px solid {color}","padding":"0.5rem 0.75rem"}
            )
        )
    return dbc.ListGroup(rows, flush=True)


def build_domain_score_cards(country_code):
    row = df_dom[df_dom["Country"] == country_code]
    if row.empty:
        return html.Div("No data")
    row = row.iloc[0]
    cards = []
    for dom in DOMAIN_COLS:
        score = row[dom] if dom in row else np.nan
        color = DOMAIN_COLORS.get(dom, "#888")
        bg    = score_to_color(score)
        grade = score_to_grade(score)
        cards.append(
            dbc.Col(
                dbc.Card([
                    dbc.CardBody([
                        html.Div(dom, style={"fontSize":"0.68rem","color":"#666",
                                             "fontWeight":"600","marginBottom":"4px","lineHeight":"1.3"}),
                        html.Div(f"{score:.2f}" if not pd.isna(score) else "N/A",
                                 style={"fontSize":"1.4rem","fontWeight":"800","color":bg}),
                        html.Div(grade, style={"fontSize":"0.82rem","color":bg,"fontWeight":"700"}),
                    ], style={"padding":"0.6rem"})
                ], style={"borderTop":f"4px solid {color}","borderRadius":"10px",
                          "boxShadow":"0 2px 8px rgba(0,0,0,0.08)"}),
                xs=6, sm=4, md=3, className="mb-2"
            )
        )
    return dbc.Row(cards, className="g-2")


def build_radar(country_codes, level="Domain"):
    df_r    = df_dom  if level == "Domain" else df_sub
    dims    = DOMAIN_COLS if level == "Domain" else SUB_COLS
    fig     = go.Figure()
    palette = px.colors.qualitative.Bold
    for i, cc in enumerate(country_codes):
        row = df_r[df_r["Country"] == cc]
        if row.empty:
            continue
        vals = [float(row.iloc[0][d]) if d in row.columns and not pd.isna(row.iloc[0][d]) else 0
                for d in dims]
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]], theta=dims + [dims[0]],
            fill="toself", name=get_country_name(cc),
            line=dict(color=palette[i % len(palette)]),
        ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0,1],
                                   tickfont=dict(size=8), gridcolor="#ddd")),
        showlegend=True,
        legend=dict(orientation="h", y=-0.28, x=0.5, xanchor="center", font=dict(size=11)),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=20, b=70, l=30, r=30),
        autosize=True, height=380,
    )
    return fig


def _build_tree(country_code):
    """Build a collapsible Domain > Subdomain > Indicator tree for a country's modal."""
    row_dom  = df_dom[df_dom["Country"]  == country_code]
    row_sub  = df_sub[df_sub["Country"]  == country_code]
    row_full = df_full[df_full["Country"] == country_code]

    # EU baseline
    eu_dom  = df_dom[df_dom["Country"]  == "EU"].iloc[0]  if "EU" in df_dom["Country"].values  else None
    eu_sub  = df_sub[df_sub["Country"]  == "EU"].iloc[0]  if "EU" in df_sub["Country"].values  else None

    accordion_items = []

    for dom in DOMAIN_COLS:
        dom_color = DOMAIN_COLORS.get(dom, "#4361EE")
        dom_score = float(row_dom.iloc[0][dom]) if not row_dom.empty and dom in row_dom.columns else None
        dom_grade = score_to_grade(dom_score) if dom_score is not None else "N/A"
        dom_bar_c = score_to_color(dom_score) if dom_score is not None else "#ccc"

        # EU diff for domain
        if eu_dom is not None and dom in eu_dom.index and country_code != "EU" and dom_score is not None:
            diff = dom_score - float(eu_dom[dom])
            eu_arrow = html.Span(
                f" ▲ +{diff:.2f}" if diff >= 0 else f" ▼ {diff:.2f}",
                style={"fontSize":"0.72rem","fontWeight":"700",
                       "color":"#2e7d32" if diff >= 0 else "#c62828","marginLeft":"6px"}
            )
        else:
            eu_arrow = html.Span()

        # Domain header label
        dom_label = html.Div([
            dbc.Progress(value=round((dom_score or 0)*100), style={"height":"6px","marginBottom":"4px"},
                         color=("success" if (dom_score or 0)>=0.67 else "warning" if (dom_score or 0)>=0.34 else "danger")),
            dbc.Row([
                dbc.Col(html.Span(dom, style={"fontWeight":"700","fontSize":"0.9rem"}), width=7),
                dbc.Col([
                    html.Span(dom_grade, style={"fontWeight":"900","fontSize":"1rem","color":dom_bar_c}),
                    html.Span(f" {dom_score:.2f}" if dom_score else "", style={"fontSize":"0.78rem","color":"#888"}),
                    eu_arrow,
                ], width=5, className="text-end"),
            ], align="center"),
        ], style={"width":"100%"})

        # Subdomains inside this domain
        sub_children = []
        subs_in_dom = hierarchy[hierarchy["Domain"] == dom]["Subdomain"].unique()
        for sub in subs_in_dom:
            sub_score = float(row_sub.iloc[0][sub]) if not row_sub.empty and sub in row_sub.columns else None
            sub_grade = score_to_grade(sub_score) if sub_score is not None else "N/A"
            sub_bar_c = score_to_color(sub_score) if sub_score is not None else "#ccc"

            # EU diff for subdomain
            if eu_sub is not None and sub in eu_sub.index and country_code != "EU" and sub_score is not None:
                sdiff = sub_score - float(eu_sub[sub])
                sub_eu = html.Span(
                    f" ▲ +{sdiff:.2f}" if sdiff >= 0 else f" ▼ {sdiff:.2f}",
                    style={"fontSize":"0.68rem","fontWeight":"700",
                           "color":"#2e7d32" if sdiff >= 0 else "#c62828","marginLeft":"4px"}
                )
            else:
                sub_eu = html.Span()

            # Indicators inside this subdomain
            inds_in_sub = hierarchy[(hierarchy["Domain"]==dom) & (hierarchy["Subdomain"]==sub)]["Indicator"].tolist()
            ind_rows = []
            for ind in inds_in_sub:
                ind_val = float(row_full.iloc[0][ind]) if not row_full.empty and ind in row_full.columns and not pd.isna(row_full.iloc[0][ind]) else None
                ind_color = score_to_color(ind_val) if ind_val is not None else "#ccc"
                ind_rows.append(
                    html.Div([
                        dbc.Row([
                            dbc.Col(
                                html.Span(ind, style={"fontSize":"0.75rem","color":"#555"}),
                                width=9
                            ),
                            dbc.Col(
                                html.Span(
                                    f"{ind_val:.2f}" if ind_val is not None else "N/A",
                                    style={"fontSize":"0.75rem","fontWeight":"700","color":ind_color}
                                ),
                                width=3, className="text-end"
                            ),
                        ], align="center", className="g-0"),
                    ], style={"padding":"3px 0","borderBottom":"1px solid #f0f0f0"})
                )

            sub_children.append(
                dbc.Card([
                    dbc.CardHeader(
                        dbc.Row([
                            dbc.Col(html.Span(f"  {sub}", style={"fontSize":"0.82rem","fontWeight":"600","color":"#333"}), width=7),
                            dbc.Col([
                                html.Span(sub_grade, style={"fontWeight":"800","fontSize":"0.9rem","color":sub_bar_c}),
                                html.Span(f" {sub_score:.2f}" if sub_score else "", style={"fontSize":"0.72rem","color":"#888"}),
                                sub_eu,
                            ], width=5, className="text-end"),
                        ], align="center"),
                        style={"padding":"6px 12px","backgroundColor":"#f8f9fa","cursor":"default"}
                    ),
                    dbc.CardBody(ind_rows, style={"padding":"8px 16px"}),
                ], style={"marginBottom":"6px","border":"1px solid #e9ecef","borderRadius":"8px",
                          "borderLeft":f"3px solid {dom_color}"})
            )

        accordion_items.append(
            dbc.AccordionItem(
                html.Div(sub_children),
                title=dom_label,
                item_id=f"tree-{dom}",
            )
        )

    return dbc.Accordion(accordion_items, start_collapsed=True, flush=False,
                         style={"borderRadius":"10px"})


def build_bar(col, df_source, title, use_traffic_light=True):
    n      = len(df_source)
    height = max(300, min(900, n * 28 + 80))   # dynamic: ~28px per country
    df_p   = df_source.sort_values(col)
    colors = [score_to_color(v) for v in df_p[col]] if use_traffic_light else ["#4361EE"]*len(df_p)
    fig = go.Figure(go.Bar(
        y=df_p["CountryName"], x=df_p[col], orientation="h",
        marker=dict(color=colors, line=dict(width=0), opacity=0.85),
        text=[f"{v:.2f}" for v in df_p[col]], textposition="auto",
        hovertemplate="%{y}: %{x:.2f}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        height=height,
        yaxis_tickfont=dict(size=10),
        xaxis=dict(range=[0,1], title="Score"),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FAFAFA",
        margin=dict(l=10, r=10, t=40, b=30),
        autosize=True,
    )
    return fig


def build_map(df_map, col, title):
    fig = px.choropleth(
        df_map, locations="ISO", color=col,
        hover_name="CountryName",
        hover_data={col:":.2f","ISO":False},
        color_continuous_scale=["#F44336","#FFC107","#4CAF50"],
        range_color=[0,1], scope="europe", title=title,
    )
    fig.update_geos(projection_type="mercator", center={"lat":54,"lon":15},
                    fitbounds="locations", visible=False)
    fig.update_layout(
        margin={"r":0,"t":40,"l":0,"b":0},
        height=620,
        coloraxis_colorbar=dict(
            title="Score", ticks="outside", tickformat=".2f",
            tickvals=[0,0.34,0.67,1],
            ticktext=["Low","Med-Low","Med-High","High"],
            thickness=12, len=0.6,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        autosize=True,
    )
    return fig


# ── App ───────────────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.FLATLY,
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap",
    ],
    suppress_callback_exceptions=True,
    meta_tags=[
        {"name": "viewport",
         "content": "width=device-width, initial-scale=1, shrink-to-fit=no"}
    ],
)
app.title = "Social Contract Dashboard"
server    = app.server

# ── Country filter factory ────────────────────────────────────────────────────
def country_filter(tab_id):
    return dbc.Card([
        dbc.CardBody([
            dbc.Label("Filter Countries", style={"fontWeight":"700","fontSize":"0.8rem"}),
            dcc.Dropdown(
                id=f"countries-{tab_id}",
                options=[{"label": get_country_name(c), "value": c} for c in COUNTRIES],
                value=COUNTRIES,
                multi=True,
                clearable=False,
                style={"fontSize":"0.85rem"},
                optionHeight=32,
            ),
        ])
    ], style={"borderRadius":"10px","marginBottom":"1rem",
              "boxShadow":"0 1px 6px rgba(0,0,0,0.07)","border":"none"})

# ── Country modal ─────────────────────────────────────────────────────────────
COUNTRY_MODAL = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle(id="modal-title"), close_button=True),
    dbc.ModalBody(id="modal-body"),
], id="country-modal", size="xl", scrollable=True, is_open=False,
   style={"zIndex":"1060"})

# ── Navbar ────────────────────────────────────────────────────────────────────
NAVBAR = dbc.Navbar(
    dbc.Container([
        html.Img(
            src="https://github.com/urbanhobbit/CS-Index-01/raw/main/Logo%20CO3.png",
            height="40px", style={"marginRight":"12px"}
        ),
        dbc.NavbarBrand(html.Div([
            html.Div("Social Contract Indicators",
                     className="navbar-brand-text",
                     style={"fontWeight":"800","fontSize":"1rem","lineHeight":"1.1"}),
            html.Div("CO3 – Resilient Social Contracts",
                     className="navbar-brand-text-sub",
                     style={"fontSize":"0.72rem","color":"#FCA311","fontWeight":"600"}),
        ])),
    ], fluid=True),
    color="#14213D", dark=True, sticky="top",
    style={"boxShadow":"0 2px 8px rgba(0,0,0,0.2)"}
)

# ── Domain info ───────────────────────────────────────────────────────────────
_DOMAIN_INFO = [
    {
        "name": "Legitimacy", "icon": "🏛️", "color": "#4361EE",
        "desc": ("Measures citizens' trust in democratic institutions, political participation, "
                 "satisfaction with EU governance, and the perceived effectiveness of representative bodies."),
        "subs": "Political Participation · Role of the EP · Role of CSOs · Trust · Efficacy · EU Image",
    },
    {
        "name": "Fairness", "icon": "⚖️", "color": "#7209B7",
        "desc": ("Captures perceptions of electoral integrity, equality before the law, social mobility, "
                 "and fairness in public support — especially in the context of the COVID-19 pandemic."),
        "subs": "Electoral Integrity · Equality · Social Mobility · Pandemic Support · Justice & Law",
    },
    {
        "name": "Citizenship", "icon": "🪪", "color": "#F72585",
        "desc": ("Examines the sense of European and national identity, awareness of citizenship rights, "
                 "and the degree to which EU values are respected in daily life."),
        "subs": "Feeling of Citizenship · Citizenship Rights · Respect for EU Values",
    },
    {
        "name": "Social Cohesion", "icon": "🤝", "color": "#4CC9F0",
        "desc": ("Reflects the strength of social bonds within and across societies — covering perceptions "
                 "of gender equality and exposure to or experience of discrimination."),
        "subs": "Gender Equality · Discrimination",
    },
    {
        "name": "Citizen–State Relations", "icon": "🔗", "color": "#3A0CA3",
        "desc": ("Assesses the quality of interaction between citizens and public institutions — including "
                 "national identity, satisfaction with public administration, and attitudes toward defense policy."),
        "subs": "Identity · Policy · Public Administration · Defense Policy",
    },
    {
        "name": "Resilience to Crises", "icon": "💪", "color": "#4CAF50",
        "desc": ("Evaluates how citizens and the EU respond to major challenges such as COVID-19, "
                 "immigration pressures, and disinformation, and their confidence in collective EU action."),
        "subs": "COVID-19 · Immigration · Disinformation · EU Response · Confidence in the EU",
    },
]

def _domain_card(d):
    return dbc.Col(
        dbc.Card([
            dbc.CardBody([
                html.Div(
                    [html.Span(d["icon"], style={"fontSize":"1.5rem","marginRight":"8px"}),
                     html.Span(d["name"], style={"fontWeight":"800","fontSize":"0.95rem","color":d["color"]})],
                    style={"display":"flex","alignItems":"center","marginBottom":"8px"}
                ),
                html.P(d["desc"],
                       style={"fontSize":"0.81rem","color":"#555","marginBottom":"6px","lineHeight":"1.5"}),
                html.Div(d["subs"],
                         style={"fontSize":"0.69rem","color":"#999","fontStyle":"italic","lineHeight":"1.4"}),
            ], style={"padding":"0.85rem"})
        ], style={
            "borderRadius":"12px","border":"none",
            "borderTop":f"4px solid {d['color']}",
            "boxShadow":"0 2px 10px rgba(0,0,0,0.07)",
            "height":"100%",
        }),
        xs=12, sm=6, md=4, className="mb-3"   # ← xs=12: full width on mobile
    )

# ── Tab contents ──────────────────────────────────────────────────────────────

TAB_HOME = dbc.Container([
    html.Div(style={"height":"1.2rem"}),

    # Hero
    dbc.Row([
        dbc.Col([
            html.H2("What is the Social Contract Index?",
                    style={"fontWeight":"800","color":"#14213D","marginBottom":"0.7rem",
                           "fontSize":"clamp(1.2rem, 4vw, 1.8rem)"}),
            html.P(
                "The Social Contract Indicators Dashboard is part of CO3 — a Horizon Europe "
                "research project building resilient social contracts for democratic societies. "
                "It tracks how EU member states perform across six core dimensions of the "
                "relationship between citizens, states, and the EU.",
                style={"color":"#555","lineHeight":"1.7","fontSize":"0.95rem","marginBottom":"1rem"}
            ),
            html.P(
                "All scores are normalised to a 0–1 scale. Higher values indicate stronger "
                "performance relative to the EU sample. Scores are colour-coded: "
                "🟢 ≥ 0.67  🟡 0.34–0.67  🔴 < 0.34.",
                style={"color":"#666","fontSize":"0.86rem","lineHeight":"1.6",
                       "backgroundColor":"#F0F4FF","padding":"10px 14px",
                       "borderRadius":"8px","borderLeft":"4px solid #4361EE"}
            ),
        ], md=8, className="mb-3"),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div("🔍 How to use this dashboard",
                             style={"fontWeight":"700","fontSize":"0.88rem",
                                    "marginBottom":"8px","color":"#14213D"}),
                    html.Ul([
                        html.Li("📊 Bar Charts — compare countries on any index"),
                        html.Li("🗺️ Map — geographic view of scores"),
                        html.Li("🔵 Scatter — correlate two indices"),
                        html.Li("🕸️ Radar — multi-country profile overlay"),
                        html.Li("📈 Indicators — drill into individual survey items"),
                        html.Li("📖 Metadata — question wording & sources"),
                    ], style={"fontSize":"0.8rem","color":"#555","paddingLeft":"1.1rem",
                              "lineHeight":"1.9","marginBottom":"0"}),
                ])
            ], style={"borderRadius":"12px","border":"none",
                      "boxShadow":"0 2px 10px rgba(0,0,0,0.07)",
                      "backgroundColor":"#FFFBF0","borderLeft":"4px solid #FCA311"}),
        ], md=4, className="mb-3"),
    ]),

    html.Hr(style={"borderColor":"#E0E0E0","margin":"0.5rem 0 1.2rem 0"}),

    # 6 Domain cards
    html.H4("Six Dimensions of the Social Contract",
            style={"fontWeight":"800","color":"#14213D","marginBottom":"0.4rem",
                   "fontSize":"clamp(1rem, 3vw, 1.4rem)"}),
    html.P("Explore each dimension in depth using the tabs above.",
           style={"color":"#888","marginBottom":"1rem","fontSize":"0.86rem"}),
    dbc.Row([_domain_card(d) for d in _DOMAIN_INFO], className="mb-1"),

    html.Hr(style={"borderColor":"#E0E0E0","margin":"0.8rem 0 1.2rem 0"}),

    # KPI cards
    dbc.Row(id="kpi-cards", className="mb-3"),

    # Leaderboard
    html.H4("🏆 Country Leaderboard",
            style={"fontWeight":"800","color":"#14213D","marginBottom":"0.4rem",
                   "fontSize":"clamp(1rem, 3vw, 1.3rem)"}),
    html.P("Tap any country to open its full profile.",
           style={"color":"#888","marginBottom":"0.8rem","fontSize":"0.86rem"}),
    dbc.Row([
        # On mobile: leaderboard takes full width, radar below
        dbc.Col(build_leaderboard(), xs=12, md=5,
                style={"maxHeight":"580px","overflowY":"auto","marginBottom":"1rem"}),
        dbc.Col([
            html.Div("Select a country from the leaderboard to see its radar",
                     id="leaderboard-hint",
                     style={"color":"#bbb","fontStyle":"italic","marginBottom":"6px","fontSize":"0.82rem"}),
            dcc.Graph(id="leaderboard-radar",
                      config={"displayModeBar":False, "responsive":True},
                      style={"borderRadius":"12px"}),
        ], xs=12, md=7),
    ]),

    html.Div(style={"height":"2rem"}),

    # ── Domain Progress Bar Section ───────────────────────────────────────────
    html.Hr(style={"borderColor":"#E0E0E0","margin":"0.5rem 0 1.2rem 0"}),
    html.H4("📊 Country Domain Scorecard",
            style={"fontWeight":"800","color":"#14213D","marginBottom":"0.3rem",
                   "fontSize":"clamp(1rem, 3vw, 1.3rem)"}),
    html.P("Select a country to see its score across all six dimensions.",
           style={"color":"#888","marginBottom":"0.8rem","fontSize":"0.86rem"}),
    dbc.Row([
        dbc.Col(
            dcc.Dropdown(
                id="scorecard-country",
                options=[{"label": get_country_name(c), "value": c} for c in COUNTRIES],
                value="EU",
                clearable=False,
                style={"fontSize":"0.9rem"},
            ),
            xs=12, sm=6, md=4, className="mb-3"
        )
    ]),
    html.Div(id="domain-progress-bars"),

    html.Div(style={"height":"2rem"}),
], fluid=True, style={"maxWidth":"1400px"})


TAB_BAR = dbc.Container([
    html.Div(style={"height":"0.8rem"}),
    country_filter("bar"),
    dbc.Row([
        dbc.Col([
            dbc.Label("Index Level", style={"fontSize":"0.85rem"}),
            dcc.Dropdown(
                id="bar-level",
                options=[{"label":"Composite","value":"composite"},
                         {"label":"Domain","value":"domain"},
                         {"label":"Subdomain","value":"subdomain"}],
                value="composite", clearable=False,
            ),
        ], xs=12, sm=6, md=3, className="mb-2"),
        dbc.Col([
            dbc.Label("Select Index", style={"fontSize":"0.85rem"}),
            dcc.Dropdown(id="bar-index-select", clearable=False),
        ], xs=12, sm=6, md=5, className="mb-2"),
    ], className="mb-2"),
    dcc.Graph(id="bar-chart", config={"displayModeBar":False, "responsive":True}),
], fluid=True, style={"maxWidth":"1400px"})


TAB_MAP = dbc.Container([
    html.Div(style={"height":"0.8rem"}),
    dbc.Row([
        dbc.Col([
            dbc.Label("Index Level", style={"fontSize":"0.85rem"}),
            dcc.RadioItems(
                id="map-level",
                options=[{"label":"Composite","value":"composite"},
                         {"label":"Domain","value":"domain"},
                         {"label":"Subdomain","value":"subdomain"}],
                value="composite", inline=True,
                inputStyle={"marginRight":"4px"}, labelStyle={"marginRight":"12px","fontSize":"0.85rem"},
            ),
        ], xs=12, md=6, className="mb-2"),
        dbc.Col([dcc.Dropdown(id="map-index-select", clearable=False)], xs=12, md=6, className="mb-2"),
    ], className="mb-2"),
    dcc.Graph(id="map-chart",
              config={"displayModeBar":False, "responsive":True},
              style={"minHeight":"600px"}),
], fluid=True, style={"maxWidth":"1400px"})


TAB_SCATTER = dbc.Container([
    html.Div(style={"height":"0.8rem"}),
    country_filter("scatter"),
    dbc.Row([
        dbc.Col([
            dbc.Label("Index Level", style={"fontSize":"0.85rem"}),
            dcc.RadioItems(
                id="scatter-level",
                options=[{"label":"Domain","value":"domain"},
                         {"label":"Subdomain","value":"subdomain"}],
                value="domain", inline=True,
                inputStyle={"marginRight":"4px"}, labelStyle={"marginRight":"12px","fontSize":"0.85rem"},
            ),
        ], xs=12, className="mb-2"),
        dbc.Col([
            dbc.Label("X Axis", style={"fontSize":"0.85rem"}),
            dcc.Dropdown(id="scatter-x", clearable=False),
        ], xs=12, sm=6, md=5, className="mb-2"),
        dbc.Col([
            dbc.Label("Y Axis", style={"fontSize":"0.85rem"}),
            dcc.Dropdown(id="scatter-y", clearable=False),
        ], xs=12, sm=6, md=5, className="mb-2"),
        dbc.Col([
            dbc.Checklist(id="scatter-regline",
                          options=[{"label":"Regression line","value":"reg"}],
                          value=[], switch=True,
                          style={"marginTop":"1.6rem","fontSize":"0.85rem"})
        ], xs=12, md=2, className="mb-2"),
    ], className="mb-2"),
    dcc.Graph(id="scatter-chart", config={"displayModeBar":False, "responsive":True}),
], fluid=True, style={"maxWidth":"1400px"})


TAB_RADAR = dbc.Container([
    html.Div(style={"height":"0.8rem"}),
    dbc.Row([
        dbc.Col([
            dbc.Label("Countries to compare", style={"fontSize":"0.85rem"}),
            dcc.Dropdown(
                id="radar-countries",
                options=[{"label":get_country_name(c),"value":c} for c in COUNTRIES],
                value=["EU","DE","FR"], multi=True, clearable=False,
                optionHeight=32,
            ),
        ], xs=12, md=8, className="mb-2"),
        dbc.Col([
            dbc.Label("Level", style={"fontSize":"0.85rem"}),
            dcc.RadioItems(
                id="radar-level",
                options=[{"label":"Domain","value":"Domain"},
                         {"label":"Subdomain","value":"Subdomain"}],
                value="Domain", inline=True,
                inputStyle={"marginRight":"4px"}, labelStyle={"marginRight":"12px","fontSize":"0.85rem"},
            ),
        ], xs=12, md=4, className="mb-2"),
    ], className="mb-2"),
    dcc.Graph(id="radar-chart", config={"displayModeBar":False, "responsive":True}),
], fluid=True, style={"maxWidth":"1400px"})


TAB_INDICATORS = dbc.Container([
    html.Div(style={"height":"0.8rem"}),
    country_filter("ind"),
    dbc.Row([
        dbc.Col([
            dbc.Label("Domain", style={"fontSize":"0.85rem"}),
            dcc.Dropdown(
                id="ind-domain",
                options=[{"label":d,"value":d} for d in hierarchy["Domain"].unique()],
                value=hierarchy["Domain"].unique()[0], clearable=False,
            ),
        ], xs=12, md=4, className="mb-2"),
        dbc.Col([
            dbc.Label("Subdomain", style={"fontSize":"0.85rem"}),
            dcc.Dropdown(id="ind-subdomain", clearable=False),
        ], xs=12, md=4, className="mb-2"),
        dbc.Col([
            dbc.Label("Indicator", style={"fontSize":"0.85rem"}),
            dcc.Dropdown(id="ind-indicator", clearable=False),
        ], xs=12, md=4, className="mb-2"),
    ]),
    dbc.Row([
        dbc.Col([
            dbc.RadioItems(
                id="ind-normraw",
                options=[{"label":"Normalized","value":"norm"},{"label":"Raw","value":"raw"}],
                value="norm", inline=True,
                inputStyle={"marginRight":"4px"}, labelStyle={"marginRight":"12px","fontSize":"0.85rem"},
            )
        ])
    ], className="mb-2"),
    dcc.Graph(id="ind-chart", config={"displayModeBar":False, "responsive":True}),
], fluid=True, style={"maxWidth":"1400px"})


TAB_METADATA = dbc.Container([
    html.Div(style={"height":"0.8rem"}),
    html.P("Browse source, question wording and response scale for each indicator.",
           style={"color":"#666","marginBottom":"1rem","fontSize":"0.88rem"}),
    dbc.Row([
        dbc.Col([
            dbc.Label("Domain", style={"fontSize":"0.85rem"}),
            dcc.Dropdown(
                id="meta-domain",
                options=[{"label":d,"value":d} for d in metadata_df["Domain"].unique()],
                value=metadata_df["Domain"].unique()[0], clearable=False,
            ),
        ], xs=12, sm=6, md=3, className="mb-2"),
        dbc.Col([
            dbc.Label("Subdomain", style={"fontSize":"0.85rem"}),
            dcc.Dropdown(id="meta-subdomain", clearable=False),
        ], xs=12, sm=6, md=3, className="mb-2"),
        dbc.Col([
            dbc.Label("Indicator", style={"fontSize":"0.85rem"}),
            dcc.Dropdown(id="meta-indicator", clearable=False),
        ], xs=12, md=6, className="mb-2"),
    ], className="mb-3"),
    html.Div(id="meta-card"),
], fluid=True, style={"maxWidth":"1400px"})


TAB_MANUAL = dbc.Container([
    html.Div(style={"height":"1.2rem"}),
    dbc.Card([
        dbc.CardBody([
            html.H5("📖 User Manual", style={"fontWeight":"700","marginBottom":"1rem"}),
            html.P("Download the full PDF user manual for the Social Contract Indicators Dashboard."),
            html.Div(id="manual-download-area"),
            html.Hr(),
            html.P([
                "Project website: ",
                html.A("co3socialcontract.eu", href="https://www.co3socialcontract.eu", target="_blank"),
            ], style={"color":"#666","fontSize":"0.88rem"}),
        ])
    ], style={"borderRadius":"12px","boxShadow":"0 2px 12px rgba(0,0,0,0.07)","border":"none",
              "maxWidth":"520px"}),
], fluid=True, style={"maxWidth":"1400px"})


# ── Main layout ───────────────────────────────────────────────────────────────
app.layout = html.Div([
    NAVBAR,
    COUNTRY_MODAL,

    dbc.Tabs([
        dbc.Tab(TAB_HOME,       label="🏠 Overview",   tab_id="tab-home"),
        dbc.Tab(TAB_BAR,        label="📊 Bar",         tab_id="tab-bar"),
        dbc.Tab(TAB_MAP,        label="🗺️ Map",         tab_id="tab-map"),
        dbc.Tab(TAB_SCATTER,    label="🔵 Scatter",     tab_id="tab-scatter"),
        dbc.Tab(TAB_RADAR,      label="🕸️ Radar",       tab_id="tab-radar"),
        dbc.Tab(TAB_INDICATORS, label="📈 Indicators",  tab_id="tab-indicators"),
        dbc.Tab(TAB_METADATA,   label="📖 Metadata",    tab_id="tab-metadata"),
        dbc.Tab(TAB_MANUAL,     label="📄 Manual",      tab_id="tab-manual"),
    ], id="main-tabs", active_tab="tab-home"),

    html.Div(
        "Developed by Istanbul Bilgi University Team – 2025  |  CO3 Project",
        style={"textAlign":"center","color":"#aaa","fontSize":"0.8rem",
               "padding":"1.2rem 0","backgroundColor":"#f8f9fa","marginTop":"1.5rem"}
    ),
], style={"fontFamily":"'Inter', sans-serif","backgroundColor":"#F8F9FA"})


# ══ Callbacks ═════════════════════════════════════════════════════════════════

@app.callback(Output("kpi-cards","children"), Input("kpi-cards","id"))
def render_kpi(_):
    top  = df_comp.loc[df_comp["Composite_Index"].idxmax()]
    eu   = df_comp[df_comp["Country"]=="EU"]
    eu_s = eu["Composite_Index"].values[0] if not eu.empty else np.nan
    n_c  = len([c for c in COUNTRIES if c != "EU"])

    def card(icon, label, value, sub, color):
        return dbc.Col(
            dbc.Card([dbc.CardBody([
                html.Div(icon, style={"fontSize":"1.6rem","marginBottom":"2px"}),
                html.Div(label, style={"fontSize":"0.68rem","color":"#888","fontWeight":"600",
                                       "textTransform":"uppercase","letterSpacing":"0.05em"}),
                html.Div(value, className="kpi-value",
                         style={"fontSize":"1.7rem","fontWeight":"800","color":color,"lineHeight":"1.1"}),
                html.Div(sub,   style={"fontSize":"0.74rem","color":"#777","marginTop":"3px"}),
            ], style={"padding":"0.85rem"})],
            style={"borderRadius":"14px","boxShadow":"0 2px 12px rgba(0,0,0,0.07)","border":"none"}),
            xs=6, md=3, className="mb-2"
        )

    return [
        card("🌍", "Countries",   str(n_c),           "EU member states + others",            "#14213D"),
        card("📊", "Indicators",  str(len(hierarchy)), "Across 6 domains",                     "#4361EE"),
        card("🥇", "Top Country", top["CountryName"],  f"Score: {top['Composite_Index']:.2f}", "#FCA311"),
        card("🇪🇺", "EU Average", f"{eu_s:.2f}" if not pd.isna(eu_s) else "N/A",
             "Composite index", "#4CAF50"),
    ]


@app.callback(
    Output("leaderboard-radar","figure"),
    Output("leaderboard-hint","style"),
    Output("country-modal","is_open"),
    Output("modal-title","children"),
    Output("modal-body","children"),
    Input({"type":"leaderboard-item","index":dash.ALL},"n_clicks"),
    State("country-modal","is_open"),
    prevent_initial_call=True,
)
def leaderboard_click(n_clicks_list, is_open):
    ctx = callback_context
    if not ctx.triggered:
        return no_update, no_update, no_update, no_update, no_update
    import json
    cc = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])["index"]

    radar_fig  = build_radar([cc, "EU"], level="Domain")
    comp_row   = df_comp[df_comp["Country"] == cc].iloc[0]
    comp_score = comp_row["Composite_Index"]
    chips = [
        dbc.Badge(BADGE_BY_ID[b]["label"],
                  style={"backgroundColor":BADGE_BY_ID[b]["color"],
                         "marginRight":"5px","fontSize":"0.78rem"},
                  pill=True)
        for b in badges_map.get(cc, [])
    ]

    sub_vals   = [float(df_sub[df_sub["Country"]==cc].iloc[0][s])
                  if s in df_sub.columns and not df_sub[df_sub["Country"]==cc].empty
                  else 0 for s in SUB_COLS]
    sub_colors = [score_to_color(v) for v in sub_vals]
    sub_fig = go.Figure(go.Bar(
        x=SUB_COLS, y=sub_vals, marker_color=sub_colors,
        text=[f"{v:.2f}" for v in sub_vals], textposition="auto",
    ))
    sub_fig.update_layout(
        xaxis_tickangle=-40, yaxis=dict(range=[0,1]),
        height=280, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FAFAFA",
        margin=dict(l=10,r=10,t=10,b=110),
        autosize=True,
    )

    modal_body = html.Div([
        dbc.Row([
            dbc.Col([
                html.Div("Composite Score",
                         style={"fontSize":"0.78rem","color":"#888","fontWeight":"600"}),
                html.Div(
                    f"{comp_score:.2f}  {score_to_grade(comp_score)}",
                    style={"fontSize":"2.2rem","fontWeight":"800",
                           "color":score_to_color(comp_score),"lineHeight":"1.1"}
                ),
                html.Div(chips, style={"marginTop":"8px"}),
            ], xs=12, md=4, className="mb-3"),
            dbc.Col(
                dcc.Graph(figure=build_radar([cc,"EU"],"Domain"),
                          config={"displayModeBar":False,"responsive":True},
                          style={"height":"280px"}),
                xs=12, md=8, className="mb-3"
            ),
        ]),
        html.Hr(),
        html.H6("Domain & Subdomain Breakdown", style={"fontWeight":"700","marginBottom":"10px"}),
        _build_tree(cc),
    ])

    return radar_fig, {"display":"none"}, True, get_country_name(cc), modal_body


@app.callback(
    Output("bar-index-select","options"),
    Output("bar-index-select","value"),
    Input("bar-level","value"),
)
def bar_select_options(level):
    if level == "composite":
        return [{"label":"Composite Index","value":"Composite_Index"}], "Composite_Index"
    cols = DOMAIN_COLS if level == "domain" else SUB_COLS
    return [{"label":c,"value":c} for c in cols], cols[0]


@app.callback(
    Output("bar-chart","figure"),
    Input("bar-level","value"),
    Input("bar-index-select","value"),
    Input("countries-bar","value"),
)
def update_bar(level, col, countries):
    if not col or not countries:
        return go.Figure()
    df_s = df_comp if level=="composite" else (df_dom if level=="domain" else df_sub)
    return build_bar(col, df_s[df_s["Country"].isin(countries)], col)


@app.callback(
    Output("map-index-select","options"),
    Output("map-index-select","value"),
    Output("map-index-select","style"),
    Input("map-level","value"),
)
def map_select_options(level):
    if level == "composite":
        return [], "Composite_Index", {"display":"none"}
    cols = DOMAIN_COLS if level=="domain" else SUB_COLS
    return [{"label":c,"value":c} for c in cols], cols[0], {}


@app.callback(
    Output("map-chart","figure"),
    Input("map-level","value"),
    Input("map-index-select","value"),
)
def update_map(level, col):
    if level == "composite":
        return build_map(df_comp[["Country","CountryName","ISO","Composite_Index"]],
                         "Composite_Index", "Composite Index")
    col = col or (DOMAIN_COLS[0] if level=="domain" else SUB_COLS[0])
    df_s = df_dom if level=="domain" else df_sub
    return build_map(df_s[["Country","CountryName","ISO",col]], col, col)


@app.callback(
    Output("scatter-x","options"), Output("scatter-x","value"),
    Output("scatter-y","options"), Output("scatter-y","value"),
    Input("scatter-level","value"),
)
def scatter_axes(level):
    cols = DOMAIN_COLS if level=="domain" else SUB_COLS
    opts = [{"label":c,"value":c} for c in cols]
    return opts, cols[0], opts, cols[1] if len(cols)>1 else cols[0]


@app.callback(
    Output("scatter-chart","figure"),
    Input("scatter-level","value"),
    Input("scatter-x","value"),
    Input("scatter-y","value"),
    Input("scatter-regline","value"),
    Input("countries-scatter","value"),
)
def update_scatter(level, x_col, y_col, reg, countries):
    df_s = df_dom if level=="domain" else df_sub
    if not x_col or not y_col or not countries:
        return go.Figure()
    df_f = df_s[df_s["Country"].isin(countries)]
    fig  = px.scatter(
        df_f, x=x_col, y=y_col, text="CountryName",
        color=np.where(df_f["Country"]=="EU","EU","Other"),
        color_discrete_map={"EU":"#FCA311","Other":"#4361EE"},
        hover_data={"CountryName":True, x_col:":.2f", y_col:":.2f"},
    )
    fig.update_traces(textposition="top center", marker=dict(size=12), textfont=dict(size=10))
    fig.update_layout(
        height=520, showlegend=False,
        xaxis=dict(range=[0,1], tickformat=".2f"),
        yaxis=dict(range=[0,1], tickformat=".2f"),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FAFAFA",
        autosize=True, margin=dict(l=40,r=20,t=30,b=40),
    )
    if "reg" in (reg or []):
        xv = df_f[x_col].astype(float); yv = df_f[y_col].astype(float)
        mask = xv.notna() & yv.notna(); xv, yv = xv[mask], yv[mask]
        slope, intercept = np.polyfit(xv, yv, 1)
        lx = np.linspace(xv.min(), xv.max(), 100)
        r2 = np.corrcoef(xv, yv)[0,1]**2
        fig.add_trace(go.Scatter(x=lx, y=slope*lx+intercept, mode="lines",
                                 line=dict(color="#333",dash="dot"), name=f"R²={r2:.2f}"))
        fig.add_annotation(xref="paper", yref="paper", x=0.98, y=0.98,
                           text=f"R² = {r2:.2f}", showarrow=False, font=dict(size=12))
    return fig


@app.callback(
    Output("radar-chart","figure"),
    Input("radar-countries","value"),
    Input("radar-level","value"),
)
def update_radar(countries, level):
    return build_radar(countries or ["EU"], level)


@app.callback(
    Output("ind-subdomain","options"), Output("ind-subdomain","value"),
    Input("ind-domain","value"),
)
def ind_sub(dom):
    subs = hierarchy[hierarchy["Domain"]==dom]["Subdomain"].unique()
    return [{"label":s,"value":s} for s in subs], subs[0]


@app.callback(
    Output("ind-indicator","options"), Output("ind-indicator","value"),
    Input("ind-domain","value"), Input("ind-subdomain","value"),
)
def ind_inds(dom, sub):
    inds = hierarchy[(hierarchy["Domain"]==dom)&(hierarchy["Subdomain"]==sub)]["Indicator"].unique()
    return [{"label":i,"value":i} for i in inds], inds[0]


@app.callback(
    Output("ind-chart","figure"),
    Input("ind-indicator","value"),
    Input("ind-normraw","value"),
    Input("countries-ind","value"),
)
def update_ind(ind, normraw, countries):
    if not ind or not countries:
        return go.Figure()
    df_s = df_full if normraw=="norm" else df_raw
    if ind not in df_s.columns:
        return go.Figure()
    df_f = df_s[df_s["Country"].isin(countries)][["CountryName", ind]].dropna()
    df_f = df_f.sort_values(ind)
    n    = len(df_f)
    h    = max(260, min(800, n * 26 + 70))
    colors = [score_to_color(v) for v in df_f[ind]] if normraw=="norm" else ["#4361EE"]*n
    fig = go.Figure(go.Bar(
        y=df_f["CountryName"], x=df_f[ind], orientation="h",
        marker=dict(color=colors, line=dict(width=0), opacity=0.85),
        text=[f"{v:.2f}" for v in df_f[ind]], textposition="auto",
        hovertemplate="%{y}: %{x:.2f}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=f"{ind} ({'Normalized' if normraw=='norm' else 'Raw'})", font=dict(size=13)),
        height=h, yaxis_tickfont=dict(size=9),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FAFAFA",
        margin=dict(l=10, r=10, t=40, b=30),
        autosize=True,
    )
    return fig


@app.callback(
    Output("meta-subdomain","options"), Output("meta-subdomain","value"),
    Input("meta-domain","value"),
)
def meta_sub(dom):
    subs = metadata_df[metadata_df["Domain"]==dom]["Subdomain"].unique()
    return [{"label":s,"value":s} for s in subs], subs[0]


@app.callback(
    Output("meta-indicator","options"), Output("meta-indicator","value"),
    Input("meta-domain","value"), Input("meta-subdomain","value"),
)
def meta_ind(dom, sub):
    inds = metadata_df[(metadata_df["Domain"]==dom)&(metadata_df["Subdomain"]==sub)]["Indicator"].unique()
    return [{"label":i,"value":i} for i in inds], inds[0]


@app.callback(Output("meta-card","children"),
              Input("meta-domain","value"), Input("meta-subdomain","value"),
              Input("meta-indicator","value"))
def render_meta(dom, sub, ind):
    if not ind:
        return ""
    row = metadata_df[
        (metadata_df["Domain"]==dom) &
        (metadata_df["Subdomain"]==sub) &
        (metadata_df["Indicator"]==ind)
    ]
    if row.empty:
        return dbc.Alert("No metadata found.", color="warning")
    m = row.iloc[0]
    return dbc.Card([dbc.CardBody([
        dbc.Row([
            dbc.Col([
                html.Div([
                    dbc.Badge(m["Domain"],    color="primary",   className="me-2"),
                    dbc.Badge(m["Subdomain"], color="secondary"),
                ], className="mb-3"),
                html.H5(m["Indicator"], style={"fontWeight":"700","fontSize":"1rem"}),
                html.P([html.Strong("Source: "), m["Source"], f"  ({m['Date']})"]),
                html.P([html.Strong("Response Scale: "), m["Response Scale"]]),
                html.P([html.Strong("Link: "),
                        html.A("View source", href=m["Link"], target="_blank")]),
            ], xs=12, md=5, className="mb-3"),
            dbc.Col(
                dbc.Card([
                    dbc.CardHeader("📝 Question", style={"fontWeight":"700","fontSize":"0.88rem"}),
                    dbc.CardBody(html.Em(m["Question"]), style={"fontSize":"0.88rem"}),
                ], style={"borderLeft":"4px solid #FCA311","backgroundColor":"#FFFBF0"}),
                xs=12, md=7
            ),
        ])
    ])], style={"borderRadius":"12px","boxShadow":"0 2px 12px rgba(0,0,0,0.07)","marginBottom":"2rem"})


@app.callback(Output("manual-download-area","children"), Input("manual-download-area","id"))
def render_manual(_):
    pdf_path = os.path.join(BASE_DIR, "Social Contract Indicators Dashboard User Manual.pdf")
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        return html.A(
            dbc.Button("📥 Download Manual (PDF)", color="warning",
                       style={"fontWeight":"700","width":"100%"}),
            href=f"data:application/pdf;base64,{encoded}",
            download="Social_Contract_Indicators_Manual.pdf",
        )
    return dbc.Alert("PDF file not found on server.", color="warning")


@app.callback(Output("domain-progress-bars", "children"), Input("scorecard-country", "value"))
def render_domain_progress(country_code):
    if not country_code:
        return html.Div()

    row = df_dom[df_dom["Country"] == country_code]
    if row.empty:
        return html.Div("No data available.")
    row = row.iloc[0]

    # EU baseline for comparison arrows
    eu_row   = df_dom[df_dom["Country"] == "EU"]
    eu_vals  = eu_row.iloc[0] if not eu_row.empty else None

    bars = []
    for dom in DOMAIN_COLS:
        score     = row[dom] if dom in row.index and not pd.isna(row[dom]) else None
        if score is None:
            continue
        grade     = score_to_grade(score)
        bar_color = score_to_color(score)
        dom_color = DOMAIN_COLORS.get(dom, "#4361EE")
        pct       = round(score * 100)

        # EU comparison
        if eu_vals is not None and dom in eu_vals.index and country_code != "EU":
            diff = score - eu_vals[dom]
            eu_badge = html.Span(
                f"▲ +{diff:.2f} vs EU" if diff >= 0 else f"▼ {diff:.2f} vs EU",
                style={"fontSize":"0.7rem","fontWeight":"700","marginLeft":"8px",
                       "color":"#2e7d32" if diff >= 0 else "#c62828"}
            )
        else:
            eu_badge = html.Span()

        bars.append(
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.Span(dom, style={"fontWeight":"700","fontSize":"0.88rem",
                                                      "color":"#14213D"}),
                                eu_badge,
                            ]),
                        ], xs=8),
                        dbc.Col([
                            html.Span(grade,
                                      style={"fontWeight":"900","fontSize":"1.3rem",
                                             "color": bar_color}),
                            html.Span(f"  {score:.2f}",
                                      style={"fontSize":"0.82rem","color":"#888","marginLeft":"4px"}),
                        ], xs=4, className="text-end"),
                    ], className="mb-2", align="center"),
                    dbc.Progress(
                        value=pct,
                        style={"height":"14px","borderRadius":"7px"},
                        color=("success" if score >= 0.67 else "warning" if score >= 0.34 else "danger"),
                    ),
                ], style={"padding":"0.75rem 1rem"}),
            ], style={"borderLeft":f"5px solid {dom_color}","borderRadius":"10px",
                      "boxShadow":"0 2px 8px rgba(0,0,0,0.06)","marginBottom":"0.6rem"})
        )

    country_name = get_country_name(country_code)
    badges       = badges_map.get(country_code, [])
    badge_chips  = [
        html.Span(BADGE_BY_ID[b]["label"],
                  style={"backgroundColor": BADGE_BY_ID[b]["color"],
                         "color":"#fff","borderRadius":"10px","padding":"3px 8px",
                         "fontSize":"0.75rem","marginRight":"5px","display":"inline-block",
                         "marginBottom":"4px"})
        for b in badges
    ]

    return html.Div([
        html.Div([
            html.H5(country_name, style={"fontWeight":"800","display":"inline","marginRight":"10px"}),
            *badge_chips,
        ], style={"marginBottom":"1rem"}),
        *bars,
    ])


if __name__ == "__main__":
    import os
    debug = os.environ.get("DASH_DEBUG", "true").lower() == "true"
    port  = int(os.environ.get("PORT", 7860))
    app.run(debug=debug, host="0.0.0.0", port=port)
