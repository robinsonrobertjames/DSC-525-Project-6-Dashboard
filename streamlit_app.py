import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
import json

# Force layout to wide screen mode
st.set_page_config(layout = "wide")

# Set page title and description
st.title("How Fairfax County Community Resources Affect The Census Vulnerability Index")
st.markdown("Explore the relationship between public resource availability and socio-economic vulnerability across census tracts.")

# Load and process geospatial data
@st.cache_data
def load_and_process_data():
    gdf_vuln = gpd.read_file('Vulnerability_Index_Census_Tract_2021.shp').to_crs(epsg = 4326)
    gdf_vuln['id'] = gdf_vuln.index.astype(str)

    geojson_dict = json.loads(gdf_vuln.geometry.to_json())
    
    df_res = pd.read_csv('all_community_resources.csv')
    gdf_res = gpd.GeoDataFrame(
        df_res, 
        geometry = gpd.points_from_xy(df_res.lon, df_res.lat), 
        crs="EPSG:2283"
    ).to_crs(epsg=4326)
    
    gdf_res['latitude'] = gdf_res.geometry.y
    gdf_res['longitude'] = gdf_res.geometry.x
    
    joined = gpd.sjoin(gdf_res, gdf_vuln, how="inner", predicate="within")
    resource_counts = joined.groupby('GEOID').size().reset_index(name = 'resource_count')
    
    gdf_vuln = gdf_vuln.merge(resource_counts, on = 'GEOID', how = 'left')
    gdf_vuln['resource_count'] = gdf_vuln['resource_count'].fillna(0).astype(int)
    
    return gdf_vuln, geojson_dict, gdf_res

try:
    with st.spinner("Processing geospatial layers and performing spatial joins..."):
        gdf_vulnerability, geojson_layer, gdf_resources = load_and_process_data()

    # Sidebar UI filter for asset types
    all_types = sorted(gdf_resources['type'].unique())
    selected_types = st.sidebar.multiselect(
        "Filter Public Infrastructure Types on Map",
        options = all_types,
        default = all_types
    )
    
    filtered_resources = gdf_resources[gdf_resources['type'].isin(selected_types)]

#bar chart
    st.subheader("Resource Distribution vs. Vulnerability Score")
    
    # Sort tracts by vulnerability score for clear visualization
    chart_df = gdf_vulnerability.sort_values(by= "VULNERABIL", ascending=False)
    
    # Create interactive Plotly Bar Chart
    fig_bar = px.bar(
        chart_df,
        x="NAMELSAD",
        y="resource_count",
        color="VULNERABIL",
        color_continuous_scale = "Viridis",
        labels={
            "NAMELSAD": "Census Tract",
            "resource_count": "Number of Resources",
            "VULNERABIL": "Vulnerability Index"
        },
        hover_data=["GEOID", "VULNERABIL", "resource_count"],
        template = "plotly_dark",
        title="Number of Community Resources per Census Tract (Sorted by Vulnerability Score)"
    )
    
    fig_bar.update_layout(
        height = 400,
        margin=dict(l = 20, r = 20, t = 50, b = 20),
        xaxis_tickangle = -45
    )
    
    st.plotly_chart(fig_bar, use_container_width=True)
    st.divider()

#map
    st.subheader("Geographic Overlay Map")

    fig_map = go.Figure()

    # choropleth layer for vulnerability index
    fig_map.add_trace(go.Choroplethmapbox(
        geojson=geojson_layer,
        locations=gdf_vulnerability['id'],
        z=gdf_vulnerability['VULNERABIL'],
        colorscale="Viridis",
        marker_opacity = 0.55,
        marker_line_width = 0.5,
        marker_line_color = "gray",
        colorbar=dict(title = "Vulnerability Index", thickness=15),
        customdata=gdf_vulnerability[['NAMELSAD', 'resource_count']],
        hovertemplate="<b>%{customdata[0]}</b><br>" +
                      "Vulnerability: %{z:.2f}<br>" +
                      "Total Resources: %{customdata[1]}<extra></extra>",
        name="Vulnerability"
    ))

    # infastructure points layer
    fig_map.add_trace(go.Scattermapbox(
        lat=filtered_resources['latitude'],
        lon=filtered_resources['longitude'],
        mode='markers',
        marker=go.scattermapbox.Marker(
            size=9,
            color='#00FFF0',
            opacity=0.9
        ),
        text=filtered_resources['name'],
        hoverinfo='text',
        name="Public Assets"
    ))

    # map dark theme and layout settings
    fig_map.update_layout(
        mapbox_style = "carto-darkmatter",
        mapbox_center = {"lat": 38.83, "lon": -77.27},
        mapbox_zoom = 10,
        margin = {"r":0,"t":0,"l":0,"b":0},
        height = 650,
        template = "plotly_dark",
        showlegend=True,
        legend=dict(yanchor = "top", y = 0.99, xanchor = "left", x=0.01)
    )

    st.plotly_chart(fig_map, use_container_width=True)

except Exception as e:
    st.error(f"Failed to display dashboard components: {e}")