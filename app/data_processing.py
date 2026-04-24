import pandas as pd
import numpy as np
import pycountry
import os

# Local: files are one level up (D:\Social Indicators\)
# HF Space / Docker: files are in the same directory as this script
_script_dir   = os.path.dirname(os.path.abspath(__file__))
_parent_dir   = os.path.dirname(_script_dir)
BASE_DIR = _parent_dir if os.path.exists(os.path.join(_parent_dir, "Metadata.xlsx")) else _script_dir

COUNTRY_NAMES = {
    "EU": "European Union", "BE": "Belgium", "BG": "Bulgaria", "CZ": "Czechia",
    "DK": "Denmark", "DE": "Germany", "EE": "Estonia", "IE": "Ireland",
    "EL": "Greece", "ES": "Spain", "FR": "France", "HR": "Croatia",
    "IT": "Italy", "CY": "Cyprus", "LV": "Latvia", "LT": "Lithuania",
    "LU": "Luxembourg", "HU": "Hungary", "MT": "Malta", "NL": "Netherlands",
    "AT": "Austria", "PL": "Poland", "PT": "Portugal", "RO": "Romania",
    "SI": "Slovenia", "SK": "Slovakia", "FI": "Finland", "SE": "Sweden",
    "UK": "United Kingdom", "NO": "Norway", "CH": "Switzerland",
}

ISO_MAP = {
    "EL": "GRC", "UK": "GBR", "EU": "EUU", "BE": "BEL", "BG": "BGR",
    "CZ": "CZE", "DK": "DNK", "DE": "DEU", "EE": "EST", "IE": "IRL",
    "ES": "ESP", "FR": "FRA", "HR": "HRV", "IT": "ITA", "CY": "CYP",
    "LV": "LVA", "LT": "LTU", "LU": "LUX", "HU": "HUN", "MT": "MLT",
    "NL": "NLD", "AT": "AUT", "PL": "POL", "PT": "PRT", "RO": "ROU",
    "SI": "SVN", "SK": "SVK", "FI": "FIN", "SE": "SWE", "NO": "NOR",
    "CH": "CHE",
}

DOMAIN_COLORS = {
    "Legitimacy": "#4361EE",
    "Fairness": "#7209B7",
    "Citizenship": "#F72585",
    "Social Cohesion": "#4CC9F0",
    "the Relationship between Citizen and State": "#3A0CA3",
    "Resilience to Crises": "#4CAF50",
}

BADGE_RULES = [
    {"id": "top_composite", "label": "🥇 Top Performer", "color": "#FFD700",
     "desc": "Highest composite index among all countries"},
    {"id": "eu_champion", "label": "🇪🇺 EU Champion", "color": "#003399",
     "desc": "Scores above EU average on all domains"},
    {"id": "most_balanced", "label": "⚖️ Most Balanced", "color": "#4CAF50",
     "desc": "Lowest standard deviation across domains"},
    {"id": "legitimacy_leader", "label": "🏛️ Legitimacy Leader", "color": "#4361EE",
     "desc": "Top score in Legitimacy domain"},
    {"id": "resilience_champion", "label": "💪 Resilience Champion", "color": "#F72585",
     "desc": "Top score in Resilience to Crises domain"},
    {"id": "cohesion_star", "label": "🤝 Cohesion Star", "color": "#4CC9F0",
     "desc": "Top score in Social Cohesion domain"},
]


def get_iso_alpha(country):
    if country in ISO_MAP:
        return ISO_MAP[country]
    try:
        return pycountry.countries.lookup(country).alpha_3
    except:
        return None


def get_country_name(code):
    return COUNTRY_NAMES.get(code, code)


def score_to_color(score):
    """Map 0-1 score to traffic-light color hex."""
    if pd.isna(score):
        return "#CCCCCC"
    if score >= 0.67:
        return "#4CAF50"   # green
    elif score >= 0.34:
        return "#FFC107"   # amber
    else:
        return "#F44336"   # red


def score_to_grade(score):
    if pd.isna(score):
        return "N/A"
    if score >= 0.80:
        return "A"
    elif score >= 0.60:
        return "B"
    elif score >= 0.40:
        return "C"
    elif score >= 0.20:
        return "D"
    else:
        return "F"


def load_and_process():
    metadata_df = pd.read_excel(os.path.join(BASE_DIR, "Metadata.xlsx"))
    df_raw = pd.read_excel(os.path.join(BASE_DIR, "SC Indicators Data Prep.xlsx"),
                           sheet_name=0, header=None)

    domain_row = df_raw.iloc[0]
    subdomain_row = df_raw.iloc[1]
    indicator_row = df_raw.iloc[2]
    data = df_raw.iloc[3:].reset_index(drop=True)
    data.columns = indicator_row
    data.insert(0, "Country", df_raw.iloc[3:, 0].values)
    if "COUNTRY" in data.columns:
        data = data.drop(columns=["COUNTRY"])

    hierarchy = pd.DataFrame({
        "Domain": domain_row.iloc[1:].values,
        "Subdomain": subdomain_row.iloc[1:].values,
        "Indicator": indicator_row.iloc[1:].values
    })

    all_indicators = hierarchy["Indicator"].tolist()
    df_numeric = data[all_indicators].apply(pd.to_numeric, errors="coerce")

    # Normalize indicators
    df_norm = df_numeric.copy()
    for col in df_norm.columns:
        mn, mx = df_norm[col].min(), df_norm[col].max()
        if mx > mn:
            df_norm[col] = (df_norm[col] - mn) / (mx - mn)

    df_full = pd.concat([data[["Country"]], df_norm], axis=1)
    df_raw_full = pd.concat([data[["Country"]], df_numeric], axis=1)

    # Subdomain indices
    subdomain_indices = {}
    for sub in hierarchy["Subdomain"].unique():
        inds = hierarchy[hierarchy["Subdomain"] == sub]["Indicator"].tolist()
        subdomain_indices[sub] = df_norm[inds].mean(axis=1, skipna=True)
    df_sub = pd.DataFrame(subdomain_indices)
    df_sub.insert(0, "Country", data["Country"].values)
    for col in df_sub.columns[1:]:
        mn, mx = df_sub[col].min(), df_sub[col].max()
        if mx > mn:
            df_sub[col] = (df_sub[col] - mn) / (mx - mn)

    # Domain indices
    domain_indices = {}
    for dom in hierarchy["Domain"].unique():
        subs = hierarchy[hierarchy["Domain"] == dom]["Subdomain"].unique()
        existing = [s for s in subs if s in df_sub.columns]
        if existing:
            domain_indices[dom] = df_sub[existing].mean(axis=1, skipna=True)
    df_dom = pd.DataFrame(domain_indices)
    df_dom.insert(0, "Country", data["Country"].values)
    for col in df_dom.columns[1:]:
        mn, mx = df_dom[col].min(), df_dom[col].max()
        if mx > mn:
            df_dom[col] = (df_dom[col] - mn) / (mx - mn)

    # Composite index
    df_composite = df_dom.copy()
    df_composite["Composite_Index"] = df_composite.iloc[:, 1:].mean(axis=1, skipna=True)
    mn, mx = df_composite["Composite_Index"].min(), df_composite["Composite_Index"].max()
    if mx > mn:
        df_composite["Composite_Index"] = (df_composite["Composite_Index"] - mn) / (mx - mn)

    # Add display names and ISO codes
    for df_ in [df_sub, df_dom, df_composite, df_full, df_raw_full]:
        df_["CountryName"] = df_["Country"].apply(get_country_name)
        df_["ISO"] = df_["Country"].apply(get_iso_alpha)

    # Compute badges
    badges = compute_badges(df_dom, df_composite)

    return {
        "hierarchy": hierarchy,
        "metadata": metadata_df,
        "df_sub": df_sub,
        "df_dom": df_dom,
        "df_composite": df_composite,
        "df_full": df_full,
        "df_raw": df_raw_full,
        "badges": badges,
    }


def compute_badges(df_dom, df_composite):
    badges = {c: [] for c in df_composite["Country"]}
    domain_cols = [c for c in df_dom.columns if c not in ("Country", "CountryName", "ISO")]

    # Top composite
    top = df_composite.loc[df_composite["Composite_Index"].idxmax(), "Country"]
    badges[top].append("top_composite")

    # EU champion: above EU on all domains
    if "EU" in df_dom["Country"].values:
        eu_row = df_dom[df_dom["Country"] == "EU"].iloc[0]
        for _, row in df_dom.iterrows():
            c = row["Country"]
            if c == "EU":
                continue
            if all(row[d] >= eu_row[d] for d in domain_cols if d in row.index and not pd.isna(row[d])):
                badges[c].append("eu_champion")

    # Most balanced (lowest std across domains)
    stds = df_dom.set_index("Country")[domain_cols].std(axis=1)
    most_balanced = stds.idxmin()
    badges[most_balanced].append("most_balanced")

    # Domain leaders
    domain_badge_map = {
        "Legitimacy": "legitimacy_leader",
        "Resilience to Crises": "resilience_champion",
        "Social Cohesion": "cohesion_star",
    }
    for dom, badge_id in domain_badge_map.items():
        if dom in df_dom.columns:
            leader = df_dom.loc[df_dom[dom].idxmax(), "Country"]
            badges[leader].append(badge_id)

    return badges
