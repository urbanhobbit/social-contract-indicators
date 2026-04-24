import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import pycountry

st.set_page_config(layout="wide")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700&display=swap');

        html, body, [class*='css'] {
            font-family: 'Open Sans', sans-serif;
            background-color: #FFFFFF;
            color: #14213D;
        }
        .block-container {
            padding-top: 2rem;
        }
        .stRadio > label,
        .stSelectbox label,
        .stCheckbox label {
            color: #14213D;
            font-weight: 600;
        }
        h1, h2, h3, h4 {
            color: #14213D;
        }
        .stButton>button {
            background-color: #FCA311;
            color: white;
            border-radius: 6px;
            border: none;
            padding: 0.5rem 1rem;
            font-weight: bold;
        }
        .stButton>button:hover {
            background-color: #e08e05;
            color: white;
        }
        .stMarkdown h3 {
            font-size: 22px;
            font-weight: 600;
            margin-top: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

logo_html = """
    <div style='display: flex; align-items: center;'>
        <img src='https://github.com/urbanhobbit/CS-Index-01/raw/main/Logo%20CO3.png' width='220' style='margin-right: 25px;'>
        <div>
            <h1 style='color:#14213D; margin-bottom: 0;'>Social Contract Indicators Dashboard</h1>
            <p style='color:#FCA311; font-size: 1.1rem; margin-top: 0; font-weight: 600;'>CO3 – Resilient Social Contracts for Democratic Societies</p>
        </div>
    </div>
"""
st.markdown(logo_html, unsafe_allow_html=True)







# Load the dataset directly
metadata_df = pd.read_excel("Metadata.xlsx")
df_raw = pd.read_excel("SC Indicators Data Prep.xlsx", sheet_name=0, header=None)

domain_row = df_raw.iloc[0]
subdomain_row = df_raw.iloc[1]
indicator_row = df_raw.iloc[2]
data = df_raw.iloc[3:].reset_index(drop=True)
data.columns = indicator_row
data.insert(0, "Country", df_raw.iloc[3:, 0].values)

if "COUNTRY" in data.columns:
    data = data.drop(columns=["COUNTRY"])

hierarchy = pd.DataFrame({
    "Domain": domain_row[1:],
    "Subdomain": subdomain_row[1:],
    "Indicator": indicator_row[1:]
})



# Sidebar Filters

st.sidebar.markdown("### 🧭 Navigation & Filters")

# Section 1: Data Filters
with st.sidebar.expander("🔍 Filter Data", expanded=False):
    st.markdown("Select domains, subdomains, and indicators to customize the dashboard.")
    selected_domains = st.multiselect("Domains", options=hierarchy["Domain"].unique(), default=hierarchy["Domain"].unique())
    filtered_hierarchy = hierarchy[hierarchy["Domain"].isin(selected_domains)]

    selected_subdomains = st.multiselect("Subdomains", options=filtered_hierarchy["Subdomain"].unique(), default=filtered_hierarchy["Subdomain"].unique())
    filtered_hierarchy = filtered_hierarchy[filtered_hierarchy["Subdomain"].isin(selected_subdomains)]

    grouped_indicators = filtered_hierarchy.groupby("Subdomain")["Indicator"].apply(list).to_dict()
    selected_indicators = []
    for subdomain, indicators in grouped_indicators.items():
        selected = st.multiselect(f"{subdomain}", indicators, default=indicators, key=f"sel_{subdomain}")
        selected_indicators.extend(selected)

# Section 2: Country Filter
with st.sidebar.expander("🌍 Select Countries", expanded=False):
    st.markdown("Choose one or more countries to include in the analysis.")
    countries = data["Country"].unique().tolist()
    selected_countries = st.multiselect("Countries", options=countries, default=countries)

# Section 3: Info & Resources
with st.sidebar.expander("📘 Info & Resources", expanded=False):
    st.markdown("Access user guidance and project background information.")
    st.markdown("[📥 Download User Manual](https://your-link-if-hosted.com)")
    st.markdown("[🌐 Project Website](https://www.co3socialcontract.eu)")
    
    filtered_hierarchy = hierarchy[hierarchy["Domain"].isin(selected_domains)]

    
    filtered_hierarchy = filtered_hierarchy[filtered_hierarchy["Subdomain"].isin(selected_subdomains)]

    

    

# Data Processing
df = data[data["Country"].isin(selected_countries)]
df_raw_indicators = df[selected_indicators].apply(pd.to_numeric, errors='coerce')
df_numeric = df_raw_indicators.copy()

# Step 1: Normalize indicators
df_norm_indicators = df_numeric.copy()
for col in df_norm_indicators.columns:
    min_val = df_norm_indicators[col].min()
    max_val = df_norm_indicators[col].max()
    if max_val > min_val:
        df_norm_indicators[col] = (df_norm_indicators[col] - min_val) / (max_val - min_val)

df_full = pd.concat([df[["Country"]], df_norm_indicators], axis=1)

# Step 2: Calculate subdomain indices (average of indicators) and normalize
subdomain_indices = {}
for sub in filtered_hierarchy["Subdomain"].unique():
    inds = filtered_hierarchy[(filtered_hierarchy["Subdomain"] == sub) & (filtered_hierarchy["Indicator"].isin(selected_indicators))]["Indicator"].tolist()
    if inds:
        subdomain_indices[sub] = df_norm_indicators[inds].mean(axis=1, skipna=True)

df_sub = pd.DataFrame(subdomain_indices)
df_sub.insert(0, "Country", df["Country"].values)

for col in df_sub.columns[1:]:
    min_val = df_sub[col].min()
    max_val = df_sub[col].max()
    if max_val > min_val:
        df_sub[col] = (df_sub[col] - min_val) / (max_val - min_val)

# Step 3: Calculate domain indices (average of normalized subdomains) and normalize
domain_indices = {}
for dom in filtered_hierarchy["Domain"].unique():
    subs = filtered_hierarchy[filtered_hierarchy["Domain"] == dom]["Subdomain"].unique()
    existing_subs = [s for s in subs if s in df_sub.columns]
    if existing_subs:
        domain_indices[dom] = df_sub[existing_subs].mean(axis=1, skipna=True)

df_dom = pd.DataFrame(domain_indices)
df_dom.insert(0, "Country", df["Country"].values)

for col in df_dom.columns[1:]:
    min_val = df_dom[col].min()
    max_val = df_dom[col].max()
    if max_val > min_val:
        df_dom[col] = (df_dom[col] - min_val) / (max_val - min_val)

# Step 4: Calculate composite index (average of normalized domains) and normalize
df_composite = df_dom.copy()
df_composite["Composite_Index"] = df_composite.iloc[:, 1:].mean(axis=1, skipna=True)
min_val = df_composite["Composite_Index"].min()
max_val = df_composite["Composite_Index"].max()
if max_val > min_val:
    df_composite["Composite_Index"] = (df_composite["Composite_Index"] - min_val) / (max_val - min_val)





def get_iso_alpha(country):
    iso_map = {
        "EL": "GRC",  # Greece
        "UK": "GBR",  # United Kingdom
        "EU": "EUU"   # European Union (custom)
    }
    if country in iso_map:
        return iso_map[country]
    try:
        return pycountry.countries.lookup(country).alpha_3
    except:
        return None

# Visualization Menu
view_option = st.markdown("""
    <hr style='margin-top: 1rem; margin-bottom: 1rem;'>
    <h3 style='font-weight: 600;'>Explore Dashboard Sections</h3>
""", unsafe_allow_html=True)
tabs = st.tabs(["Tables", "Bar Charts", "Map", "Scatter Plot", "Radar Chart", "Indicator Charts", "Metadata", "User Manual"])

with tabs[0]:
    st.subheader("Composite Indices by Subdomain")
    st.dataframe(df_sub.style.format({col: "{:.2f}" for col in df_sub.select_dtypes(include='number').columns}))

    st.subheader("Composite Indices by Domain")
    st.dataframe(df_dom.style.format({col: "{:.2f}" for col in df_dom.select_dtypes(include='number').columns}))

    st.subheader("Composite Index")
    st.dataframe(df_composite[["Country", "Composite_Index"]].style.format({"Composite_Index": "{:.2f}"}))

with tabs[1]:
    st.markdown("""
    <div style='padding: 10px; background-color: #f0f4f8; border-radius: 8px; margin-bottom: 20px;'>
        <strong>🔎 Summary:</strong><br>
        Countries Selected: <strong>{}</strong><br>
        Highest Composite Index: <strong>{} ({:.2f})</strong>
    </div>
    """.format(
        len(df_composite),
        df_composite.loc[df_composite["Composite_Index"].idxmax(), "Country"],
        df_composite["Composite_Index"].max()
    ), unsafe_allow_html=True)
    st.subheader("Bar Chart for Composite Index")
    df_plot_comp = df_composite.sort_values(by="Composite_Index")
    fig_comp = go.Figure()
    fig_comp.add_trace(go.Bar(
    y=df_plot_comp["Country"],
    x=df_plot_comp["Composite_Index"],
    orientation='h',
    marker=dict(color=["red" if c == "EU" else "steelblue" for c in df_plot_comp["Country"]], line=dict(width=0), opacity=0.8),
    text=[f"{v:.2f}" for v in df_plot_comp["Composite_Index"]],
    textposition="auto",
    hovertemplate="%{y}: %{x:.2f}<extra></extra>",
))
    fig_comp.update_layout(title="Composite Index by Country", height=800, yaxis_tickfont=dict(size=11), xaxis_title="Composite Index")
    st.plotly_chart(fig_comp, use_container_width=True)

    st.subheader("Bar Chart for Domain Index")
    if len(df_dom.columns) > 1:
        selected_domain = st.selectbox("Select Domain to Plot:", options=df_dom.columns[1:], key="domain_plot")
        if selected_domain in df_dom.columns:
            df_plot_dom = df_dom.sort_values(by=selected_domain)
            fig_dom = go.Figure()
            fig_dom.add_trace(go.Bar(
                y=df_plot_dom["Country"],
                x=df_plot_dom[selected_domain],
                orientation='h',
                marker=dict(color=["red" if c == "EU" else "steelblue" for c in df_plot_dom["Country"]], line=dict(width=0), opacity=0.8),
                text=[f"{v:.2f}" for v in df_plot_dom[selected_domain]],
                textposition="auto",
                hovertemplate="%{y}: %{x:.2f}<extra></extra>",
            ))
            fig_dom.update_layout(title=f"{selected_domain} by Country", height=800, yaxis_tickfont=dict(size=11), xaxis_title="Domain Index")
            st.plotly_chart(fig_dom, use_container_width=True)
        else:
            st.warning("Selected domain is not available in the filtered dataset.")
    else:
        st.warning("No domain data available after filtering.")

    st.subheader("Bar Chart for Subdomain Index")
    selected_subdomain = st.selectbox("Select Subdomain to Plot:", options=df_sub.columns[1:], key="subdomain_plot")
    df_plot_sub = df_sub.sort_values(by=selected_subdomain)
    fig_sub = go.Figure()
    fig_sub.add_trace(go.Bar(
        y=df_plot_sub["Country"],
        x=df_plot_sub[selected_subdomain],
        orientation='h',
        marker=dict(color=["red" if c == "EU" else "steelblue" for c in df_plot_sub["Country"]], line=dict(width=0), opacity=0.8),
        text=[f"{v:.2f}" for v in df_plot_sub[selected_subdomain]],
        textposition="auto",
        hovertemplate="%{y}: %{x:.2f}<extra></extra>",
    ))
    fig_sub.update_layout(title=f"{selected_subdomain} by Country", height=800, yaxis_tickfont=dict(size=11), xaxis_title="Subdomain Index")
    st.plotly_chart(fig_sub, use_container_width=True)

with tabs[2]:
    st.subheader("Map View")
    index_level = st.radio("Select index type to map:", ["Composite", "Domain", "Subdomain", "Indicator"], horizontal=True, key="map_level")

    if index_level == "Composite":
        df_map = df_composite[["Country", "Composite_Index"]].copy()
        index_column = "Composite_Index"

    elif index_level == "Domain":
        selected_domain_map = st.selectbox("Select Domain:", options=df_dom.columns[1:], key="map_domain")
        df_map = df_dom[["Country", selected_domain_map]].copy()
        index_column = selected_domain_map

    elif index_level == "Subdomain":
        selected_subdomain_map = st.selectbox("Select Subdomain:", options=df_sub.columns[1:], key="map_subdomain")
        df_map = df_sub[["Country", selected_subdomain_map]].copy()
        index_column = selected_subdomain_map

    elif index_level == "Indicator":
        norm_or_raw_map = st.radio("Select indicator type:", ["Normalized", "Raw"], horizontal=True, key="map_normraw")
        indicator_df_map = df_full if norm_or_raw_map == "Normalized" else pd.concat([df[["Country"]], df_raw_indicators], axis=1)
        indicator_options = [i for sub in grouped_indicators.values() for i in sub if i in indicator_df_map.columns]
        selected_indicator_map = st.selectbox("Select Indicator:", options=indicator_options, key="map_indicator")
        df_map = indicator_df_map[["Country", selected_indicator_map]].copy()
        index_column = selected_indicator_map

    df_map["iso_alpha"] = df_map["Country"].apply(get_iso_alpha)
    df_map = df_map.dropna(subset=["iso_alpha"])

    fig_map = px.choropleth(
        df_map,
        locations="iso_alpha",
        color=index_column,
        hover_name="Country",
        hover_data={"Country": True, index_column: ":.2f"},
        color_continuous_scale=px.colors.sequential.Blues,
        scope="europe",
        title=f"{index_column} by Country"
    )
    fig_map.update_geos(
        projection_type="mercator",
        center={"lat": 35, "lon": 25},
        fitbounds="locations",
        visible=False
    )
    fig_map.update_layout(
        margin={"r":0,"t":30,"l":0,"b":0},
        coloraxis_colorbar=dict(
            title=index_column,
            ticks="outside",
            tickformat=".2f"
        )
    )
    st.plotly_chart(fig_map, use_container_width=True)

with tabs[3]:
    st.subheader("Scatter Plot of Indices")
    level = st.radio("Select level of indices:", ["Domain", "Subdomain", "Composite"], horizontal=True, key="scatter_level_menu")
    df_to_plot = df_dom if level == "Domain" else df_sub if level == "Subdomain" else df_composite[["Country", "Composite_Index"]]
    x_axis = st.selectbox("Select X-axis index:", df_to_plot.columns[1:], key="x_axis")
    y_axis = st.selectbox("Select Y-axis index:", df_to_plot.columns[1:], key="y_axis")

    fig_scatter = px.scatter(
        df_to_plot,
        x=x_axis,
        y=y_axis,
        text="Country",
        color=np.where(df_to_plot["Country"] == "EU", "EU", "Other"),
        color_discrete_map={"EU": "red", "Other": "steelblue"},
        hover_data={"Country": True, x_axis: ":.2f", y_axis: ":.2f"},
    )

    fig_scatter.update_traces(
        textposition='top center',
        marker=dict(size=16),
        textfont=dict(size=14)
    )

    fig_scatter.update_layout(
        title=f"{x_axis} vs {y_axis} by Country",
        xaxis=dict(tickformat=".2f"),
        yaxis=dict(tickformat=".2f"),
        height=700,
        showlegend=False
    )

    if st.checkbox("Show regression line and R-squared"):
        x_vals = df_to_plot[x_axis].astype(float)
        y_vals = df_to_plot[y_axis].astype(float)
        mask = x_vals.notna() & y_vals.notna()
        x_vals = x_vals[mask]
        y_vals = y_vals[mask]
        slope, intercept = np.polyfit(x_vals, y_vals, 1)
        line_x = np.linspace(x_vals.min(), x_vals.max(), 100)
        line_y = slope * line_x + intercept
        r_value = np.corrcoef(x_vals, y_vals)[0, 1]
        r_squared = r_value ** 2

        fig_scatter.add_trace(go.Scatter(
            x=line_x,
            y=line_y,
            mode='lines',
            name=f"Fit (R² = {r_squared:.2f})",
            line=dict(color="black", dash="dot")
        ))

        fig_scatter.add_annotation(
            xref="paper", yref="paper",
            x=0.98, y=0.98,
            text=f"R² = {r_squared:.2f}<br>y = {slope:.2f}x + {intercept:.2f}",
            showarrow=False,
            font=dict(size=14, color="black"),
            align="right",            
        )

        

        

        

        

    

    st.plotly_chart(fig_scatter, use_container_width=True)

with tabs[4]:
    st.subheader("Radar Chart Comparison")
    level = st.radio("Select level of indices:", ["Domain", "Subdomain", "Composite"], horizontal=True, key="radar_level_menu_2")
    df_radar = df_dom if level == "Domain" else df_sub if level == "Subdomain" else df_composite[["Country", "Composite_Index"]]
    selected_countries_radar = st.multiselect("Select countries to compare:", df_radar["Country"].tolist(), default=["EU"])
    dimensions = df_radar.columns[1:]
    fig_radar = go.Figure()
    colors = px.colors.qualitative.Set2
    for i, country in enumerate(selected_countries_radar):
        values = df_radar[df_radar["Country"] == country][dimensions].values.flatten().tolist()
        fig_radar.add_trace(go.Scatterpolar(
            r=values,
            theta=dimensions,
            fill='toself',
            name=country,
            line=dict(color=colors[i % len(colors)]),
            hoverinfo='text',
            text=[f"{country}: {val:.2f}" for val in values]
        ))
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1], tickfont=dict(size=10))
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        height=700
    )
    st.plotly_chart(fig_radar, use_container_width=True)

with tabs[5]:
    st.subheader("Indicator Chart")
    norm_or_raw = st.radio("Select indicator type:", ["Normalized", "Raw"], horizontal=True)
    indicator_df = df_full if norm_or_raw == "Normalized" else pd.concat([df[["Country"]], df_raw_indicators], axis=1)
    grouped_options = {sub: indicators for sub, indicators in grouped_indicators.items() if any(i in indicator_df.columns for i in indicators)}
    subdomain_selected = st.selectbox("Select Subdomain", list(grouped_options.keys()), key="subdomain_group")
    indicators_in_group = [i for i in grouped_options[subdomain_selected] if i in indicator_df.columns]
    selected_indicator_to_plot = st.selectbox("Select Indicator", options=indicators_in_group, key="indicator_plot")
    df_plot_ind = indicator_df.sort_values(by=selected_indicator_to_plot)
    fig_ind = go.Figure()
    fig_ind.add_trace(go.Bar(
        y=df_plot_ind["Country"],
        x=df_plot_ind[selected_indicator_to_plot],
        orientation='h',
        marker=dict(color=["red" if c == "EU" else "steelblue" for c in df_plot_ind["Country"]], line=dict(width=0), opacity=0.8),
        text=[f"{v:.2f}" for v in df_plot_ind[selected_indicator_to_plot]],
        textposition="auto",
        hovertemplate="%{y}: %{x:.2f}<extra></extra>",
    ))
    fig_ind.update_layout(title=f"{selected_indicator_to_plot} by Country ({norm_or_raw})", height=800, yaxis_tickfont=dict(size=11), xaxis_title="Indicator Value")
    st.plotly_chart(fig_ind, use_container_width=True)

with tabs[6]:
    st.subheader("📘 Indicator Metadata Library")
    st.markdown("Use the filters below to learn about the source, question wording, and scale of each indicator.")
    domain_filter = st.selectbox("📂 Filter by Domain", metadata_df['Domain'].unique())
    sub_filtered = metadata_df[metadata_df['Domain'] == domain_filter]
    subdomain_filter = st.selectbox("📁 Filter by Subdomain", sub_filtered['Subdomain'].unique())
    final_filtered = sub_filtered[sub_filtered['Subdomain'] == subdomain_filter]
    indicator_filter = st.selectbox("📌 Select an Indicator", final_filtered['Indicator'].unique())
    meta = final_filtered[final_filtered['Indicator'] == indicator_filter].iloc[0]

    st.markdown("""
    <div style='padding: 1rem; background-color: #f9f9f9; border: 1px solid #ddd; border-radius: 8px;'>
        <p><strong>🧭 Domain:</strong> {}</p>
        <p><strong>📚 Subdomain:</strong> {}</p>
        <p><strong>🔗 Source:</strong> <a href='{}' target='_blank'>{}</a> ({})</p>
        <p><strong>📐 Response Scale:</strong> {}</p>
        <p><strong>📝 Question:</strong><br><em>{}</em></p>
    </div>
    """.format(
        meta['Domain'],
        meta['Subdomain'],
        meta['Link'], meta['Source'], meta['Date'],
        meta['Response Scale'],
        meta['Question']
    ), unsafe_allow_html=True)
    




with tabs[7]:
    st.subheader("📖 User Manual")
    with open("Social Contract Indicators Dashboard User Manual.pdf", "rb") as pdf_file:
        PDFbyte = pdf_file.read()
    st.download_button(label="📥 Download Manual (PDF)",
                       data=PDFbyte,
                       file_name="Social_Contract_Indicators_Manual.pdf",
                       mime='application/pdf')
    st.markdown("Or [view the full manual online](https://your-link-if-hosted.com) 📄", unsafe_allow_html=True)

# Footer
st.markdown("""
    <hr style='margin-top: 3rem;'>
    <div style='text-align: center; color: #666; font-size: 0.9rem;'>
        Developed by <strong>Istanbul Bilgi University Team - 2025</strong>
    </div>
""", unsafe_allow_html=True)
