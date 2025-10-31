import streamlit as st
import pandas as pd
import numpy as np
import re
import geopandas as gpd
from shapely.geometry import Point
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import folium
from streamlit_folium import folium_static
from folium.plugins import MarkerCluster
import time
import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from datetime import timedelta
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# Set page config
st.set_page_config(page_title="Maxar Dashboard", page_icon="🛰️", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for more intuitive UI
st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --primary-color: #1E88E5;
        --secondary-color: #5E35B1;
        --success-color: #43A047;
        --warning-color: #FB8C00;
        --danger-color: #E53935;
        --light-bg: #F5F7FA;
        --dark-text: #333333;
        --light-text: #FFFFFF;
    }
    
    /* Dashboard title styling */
    .dashboard-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--primary-color);
        margin-bottom: 0.4rem;
        text-align: center;
        padding: 0.6rem;
        background: linear-gradient(90deg, #E3F2FD, #BBDEFB);
        border-radius: 6px;
        box-shadow: 0 2px 3px rgba(0, 0, 0, 0.08);
    }
    
    /* Card styling */
    .card {
        background-color: white;
        border-radius: 6px;
        padding: 0.8rem;
        box-shadow: 0 2px 3px rgba(0, 0, 0, 0.08);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        margin-bottom: 0.4rem;
    }
    
    .card:hover {
        transform: translateY(-2px);
        box-shadow: 0 3px 6px rgba(0, 0, 0, 0.12);
    }
    
    /* Metric numbers */
    .big-number {
        font-size: 19px;
        font-weight: 700;
        color: var(--primary-color);
        text-align: center;
        margin-bottom: 0.2rem;
    }
    
    .medium-number {
        font-size: 14px;
        font-weight: 600;
        text-align: center;
    }
    
    /* Status colors */
    .status-rejected {
        color: var(--danger-color);
    }
    
    .status-completed {
        color: var(--success-color);
    }
    
    .status-active {
        color: var(--warning-color);
    }
    
    /* Labels */
    .metric-label {
        font-size: 13px;
        color: var(--dark-text);
        text-align: center;
        font-weight: 500;
    }
    
    /* Section headers */
    .section-header {
        font-size: 0.88rem;
        font-weight: 600;
        color: var(--secondary-color);
        margin: 0.4rem 0 0.4rem 0;
        padding-bottom: 0.2rem;
        border-bottom: 2px solid var(--secondary-color);
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 32px;
        white-space: pre-wrap;
        background-color: #F5F5F5;
        border-radius: 6px 6px 0px 0px;
        gap: 1px;
        padding: 0 10px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: var(--primary-color);
        color: white;
        font-weight: 600;
    }
    
    /* Sidebar styling */
    .sidebar .sidebar-content {
        background-color: var(--light-bg);
    }
    
    /* Improve table readability */
    .dataframe {
        font-size: 11px;
    }
    
    .dataframe th {
        background-color: #E3F2FD;
        color: var(--dark-text);
        font-weight: 600;
        text-align: left;
        padding: 10px 12px;
    }
    
    .dataframe td {
        padding: 8px 12px;
    }
    
    .dataframe tr:nth-child(even) {
        background-color: #F5F7FA;
    }
    
    /* Tooltip styling */
    .tooltip {
        position: relative;
        display: inline-block;
        cursor: help;
    }
    
    .tooltip .tooltiptext {
        visibility: hidden;
        width: 200px;
        background-color: #555;
        color: #fff;
        text-align: center;
        border-radius: 6px;
        padding: 5px;
        position: absolute;
        z-index: 1;
        bottom: 125%;
        left: 50%;
        margin-left: -100px;
        opacity: 0;
        transition: opacity 0.3s;
    }
    
    .tooltip:hover .tooltiptext {
        visibility: visible;
        opacity: 1;
    }

    /* Compact metric styling (25% smaller) */
    .compact-metric {
        background-color: #E3F2FD;
        padding: 6px;
        border-radius: 6px;
        margin-bottom: 4px;
    }
    .compact-metric .metric-label {
        font-size: 10px;
        font-weight: 500;
        text-align: center;
        margin-bottom: 3px;
        color: var(--dark-text);
    }
    .compact-metric .metric-value {
        font-size: 15px;
        font-weight: 700;
        color: var(--primary-color);
        text-align: center;
        line-height: 1.1;
    }
    .compact-metric .metric-sub {
        font-size: 11px;
        color: #666;
        text-align: center;
        margin-top: 2px;
    }
    </style>
""", unsafe_allow_html=True)

# Helper functions for data cleaning
def to_camel_case(s):
    s = re.sub(r'[^0-9a-zA-Z]+', ' ', s)         # ganti non-alphanumeric jadi spasi
    parts = s.title().replace(" ", "")           # kapital tiap kata lalu hilangin spasi
    return parts[0].lower() + parts[1:] if parts else s

def clean_number(x):
    # Convert to string first to handle any numeric inputs
    x = str(x)
    # Remove leading/trailing zeros by converting to int and back to string
    try:
        return str(int(x))
    except ValueError:
        return x

def find_country(point, world_gdf, country_column='name'):
    # Cek apakah titik berada di dalam poligon negara manapun
    for idx, country in world_gdf.iterrows():
        if point.within(country.geometry):
            return country[country_column]
    
    # Jika titik tidak berada di dalam negara manapun (misalnya di lautan)
    # Cari negara terdekat
    min_distance = float('inf')
    nearest_country = None
    
    for idx, country in world_gdf.iterrows():
        distance = point.distance(country.geometry)
        if distance < min_distance:
            min_distance = distance
            nearest_country = country[country_column]
    
    return f"{nearest_country}"
        
@st.cache_data(ttl=3600)
def load_data():
    from datetime import timedelta
    import geopandas as gpd
    from shapely.geometry import Point
    import requests
    from io import BytesIO

    export_url = "https://docs.google.com/spreadsheets/d/1uNLGSPMFQhC3P9sscgIkaeQVJFRan14RsF3xkpDMvJ4/export?format=xlsx"

    r = requests.get(export_url)
    df_merged = pd.read_excel(BytesIO(r.content), engine="openpyxl")
    df_merged.columns = df_merged.columns.str.strip()  # ✅ perbaikan
    df_merged.loc[df_merged['archiveTasking'] == 'Tasking', 'archiveTasking'] = (
        df_merged['archiveTasking'] + "-" + df_merged['orderType']
    )
    df_merged.loc[df_merged['archiveTasking'] == 'TASKING', 'archiveTasking'] = (
        df_merged['archiveTasking'] + "-" + df_merged['orderType']
    )
    
    # daftar kolom tanggal
    datetime_cols = [
        "orderCreateTimestamp",
        "orderActiveTimestamp",
        "orderSubmitTimestamp",
        "orderCompleteTimestamp",
        "completeDate",
    ]

    # parsing datetime
    for col in datetime_cols:
        if col in df_merged.columns:
            df_merged[col] = pd.to_datetime(df_merged[col], format="%m/%d/%Y %H:%M", errors="coerce")
            df_merged[col] = df_merged[col] + timedelta(hours=7)  # ubah ke WIB (UTC+7)

    # Geocoding
    world = gpd.read_file("world_admin.geojson")
    country_column = "name"
    
    geometry = [Point(xy) for xy in zip(df_merged["longitude"], df_merged["latitude"])]
    df_geo = gpd.GeoDataFrame(df_merged, geometry=geometry, crs="EPSG:4326")
    
    joined = gpd.sjoin(df_geo, world, how="left", predicate="within")
    
    missing_countries = joined[joined[country_column].isna()]
    if len(missing_countries) > 0:
        for idx, row in missing_countries.iterrows():
            nearest_country = find_country(row.geometry, world, country_column)
            joined.at[idx, country_column] = nearest_country
    
    df_merged["country"] = joined[country_column]
    df_merged["latitude"] = pd.to_numeric(df_merged["latitude"], errors="coerce")
    df_merged["longitude"] = pd.to_numeric(df_merged["longitude"], errors="coerce")
    
    df_clean = df_merged.dropna(subset=["latitude", "longitude"])
    
    # Konversi tanggal lagi untuk memastikan semua aman
    for col in datetime_cols:
        if col in df_clean.columns:
            df_clean[col] = pd.to_datetime(df_clean[col])

    # Hitung waktu penyelesaian
    df_clean["timeToComplete"] = (
        df_clean["orderCompleteTimestamp"] - df_clean["orderActiveTimestamp"]
    ).dt.total_seconds() / 60

    # Konversi kolom waktu lain
    # if "chargeS" in df_clean.columns:
    #     df_clean["seconds"] = pd.to_timedelta(df_clean["chargeS"], errors="coerce").dt.total_seconds()

    # Bersihkan kolom charge
    if "charge" in df_clean.columns:
        df_clean["charge"] = (
            df_clean["charge"].astype(str).str.replace("$", "").str.replace(",", "").astype(float)
        )

    return df_clean


# Load data
df = load_data()

# Dashboard title with improved styling
st.markdown("<div class='dashboard-title'>🛰️ Maxar Satellite Imagery Dashboard</div>", unsafe_allow_html=True)

# Filter section with better styling
st.sidebar.markdown("<h2 style='color: var(--primary-color); border-bottom: 2px solid var(--primary-color); padding-bottom: 10px;'>Dashboard Filters</h2>", unsafe_allow_html=True)

# Add helpful description
st.sidebar.markdown("<p style='margin-bottom: 20px;'>Use the filters below to customize your view of the satellite imagery data.</p>", unsafe_allow_html=True)

# Filter by Archive/Tasking with improved styling
archive_tasking_filter = st.sidebar.radio(
    "📊 Filter by Type:",
    ["All", "ARCHIVE", "TASKING"]
)

if archive_tasking_filter == "TASKING":
    df_filtered = df[df['archiveTasking'] != "ARCHIVE"]
elif archive_tasking_filter != "All":
    df_filtered = df[df['archiveTasking'] == archive_tasking_filter]
else:
    df_filtered = df

# Add sidebar sections with better styling
st.sidebar.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
st.sidebar.markdown("<div style='background-color: var(--light-bg); padding: 8px; border-radius: 5px; margin-bottom: 10px;'>", unsafe_allow_html=True)

# Date range filter with icon and tooltip
st.sidebar.markdown("<div style='display: flex; align-items: center;'>"
                   "<span style='font-weight: 600; margin-right: 5px;'>📅 Date Range</span>"
                   "<div class='tooltip'>ℹ️<span class='tooltiptext'>Filter orders by creation date</span></div>"
                   "</div>", unsafe_allow_html=True)

min_date = df_filtered['orderCreateTimestamp'].min().date()
max_date = df_filtered['orderCreateTimestamp'].max().date()

date_range = st.sidebar.date_input(
    "",  # Empty label as we're using custom markdown above
    [min_date, max_date],
    min_value=min_date,
    max_value=max_date
)

# Tampilkan di halaman Streamlit
# st.write(df_filtered['status'].value_counts())

if len(date_range) == 2:
    start_date, end_date = date_range
    mask = (df_filtered['orderCreateTimestamp'].dt.date >= start_date) & (df_filtered['orderCreateTimestamp'].dt.date <= end_date)
    df_filtered = df_filtered[mask]

st.sidebar.markdown("</div>", unsafe_allow_html=True)

# Status filter with icon and tooltip
st.sidebar.markdown("<div style='background-color: var(--light-bg); padding: 10px; border-radius: 5px; margin-bottom: 15px;'>", unsafe_allow_html=True)
st.sidebar.markdown("<div style='display: flex; align-items: center;'>"
                   "<span style='font-weight: 600; margin-right: 5px;'>🔄 Status</span>"
                   "<div class='tooltip'>ℹ️<span class='tooltiptext'>Filter orders by their current status</span></div>"
                   "</div>", unsafe_allow_html=True)

status_options = df['status'].unique().tolist()
selected_status = st.sidebar.multiselect(
    "",  # Empty label as we're using custom markdown above
    status_options,
    default=status_options
)

if selected_status:
    df_filtered = df_filtered[df_filtered['status'].isin(selected_status)]

st.sidebar.markdown("</div>", unsafe_allow_html=True)

# Spacecraft filter with icon and tooltip
st.sidebar.markdown("<div style='background-color: var(--light-bg); padding: 10px; border-radius: 5px; margin-bottom: 15px;'>", unsafe_allow_html=True)
st.sidebar.markdown("<div style='display: flex; align-items: center;'>"
                   "<span style='font-weight: 600; margin-right: 5px;'>🛰️ Spacecraft</span>"
                   "<div class='tooltip'>ℹ️<span class='tooltiptext'>Filter orders by spacecraft used</span></div>"
                   "</div>", unsafe_allow_html=True)

spacecraft_options = df['spacecraft'].unique().tolist()
selected_spacecraft = st.sidebar.multiselect(
    "",  # Empty label as we're using custom markdown above
    spacecraft_options,
    default=spacecraft_options
)

if selected_spacecraft:
    df_filtered = df_filtered[df_filtered['spacecraft'].isin(selected_spacecraft)]

st.sidebar.markdown("</div>", unsafe_allow_html=True)

# Country filter with icon and tooltip
st.sidebar.markdown("<div style='background-color: var(--light-bg); padding: 10px; border-radius: 5px; margin-bottom: 15px;'>", unsafe_allow_html=True)
st.sidebar.markdown("<div style='display: flex; align-items: center;'>"
                   "<span style='font-weight: 600; margin-right: 5px;'>🌎 Countries</span>"
                   "<div class='tooltip'>ℹ️<span class='tooltiptext'>Filter orders by country location</span></div>"
                   "</div>", unsafe_allow_html=True)

country_options = sorted(df['country'].unique().tolist())
selected_countries = st.sidebar.multiselect(
    "",  # Empty label as we're using custom markdown above
    country_options
)

if selected_countries:
    df_filtered = df_filtered[df_filtered['country'].isin(selected_countries)]

# Main dashboard content - combine Key Performance Metrics and Status Breakdown in one row
left_col, right_col = st.columns([1, 1])

with left_col:
    st.markdown("<div class='section-header'>Key Performance Metrics</div>", unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)

    with m1:
        st.markdown("""
        <div class='card'>
            <div class='metric-label'>Total Orders</div>
            <div class='big-number'>{}</div>
            <div style='text-align: center; font-size: 12px; color: #666;'>Total number of orders</div>
        </div>
        """.format(len(df_filtered)), unsafe_allow_html=True)

    with m2:
        total_area = df_filtered['sqkm'].sum()
        st.markdown("""
        <div class='card'>
            <div class='metric-label'>Area Ordered</div>
            <div class='big-number'>{:,.2f}</div>
            <div style='text-align: center; font-size: 12px; color: #666;'>Total square kilometers</div>
        </div>
        """.format(total_area), unsafe_allow_html=True)

    with m3:
        completed_delivered = df_filtered[df_filtered['status'].isin(['Complete', 'Delivered'])].shape[0]
        success_rate = (completed_delivered / len(df_filtered)) * 100 if len(df_filtered) > 0 else 0
        st.markdown("""
        <div class='card'>
            <div class='metric-label'>Success Rate</div>
            <div class='big-number'>{:.1f}%</div>
            <div style='text-align: center; font-size: 12px; color: #666;'>Completed/delivered orders</div>
        </div>
        """.format(success_rate), unsafe_allow_html=True)

with right_col:
    st.markdown("<div class='section-header'>Status Breakdown</div>", unsafe_allow_html=True)

    # Optional: precompute counts
    status_counts = df_filtered['status'].value_counts()

    # Define columns for status cards
    status_columns = st.columns(4)

    # Column 1: Rejected
    with status_columns[0]:
        rejected_count = df_filtered[df_filtered['status'] == 'Rejected'].shape[0]
        rejected_percent = (rejected_count / len(df_filtered)) * 100 if len(df_filtered) > 0 else 0
        st.markdown("""
         <div class='card'>
            <div style='display: flex; justify-content: center; margin-bottom: 4px;'>
                <div style='background-color: var(--danger-color); color: white; border-radius: 50%; width: 18px; height: 18px; display: flex; align-items: center; justify-content: center;'>
                    ❌
                </div>
            </div>
            <div class='metric-label'>Rejected</div>
            <div class='medium-number status-rejected'>{}</div>
            <div style='text-align: center; font-size: 12px; color: #666;'>{:.1f}% of total orders</div>
        </div>
        """.format(rejected_count, rejected_percent), unsafe_allow_html=True)

    # Column 2: Completed/Delivered (Combined)
    with status_columns[1]:
        completed_delivered_count = df_filtered[df_filtered['status'].isin(['Complete', 'Delivered'])].shape[0]
        completed_delivered_percent = (completed_delivered_count / len(df_filtered)) * 100 if len(df_filtered) > 0 else 0
        st.markdown("""
         <div class='card'>
            <div style='display: flex; justify-content: center; margin-bottom: 4px;'>
                <div style='background-color: var(--success-color); color: white; border-radius: 50%; width: 18px; height: 18px; display: flex; align-items: center; justify-content: center;'>
                    ✅
                </div>
            </div>
            <div class='metric-label'>Completed/<br>Delivered</div>
            <div class='medium-number status-completed'>{}</div>
            <div style='text-align: center; font-size: 12px; color: #666;'>{:.1f}% of total orders</div>
        </div>
        """.format(completed_delivered_count, completed_delivered_percent), unsafe_allow_html=True)

    # Column 3: Cancelled
    with status_columns[2]:
        cancelled_count = df_filtered[df_filtered['status'] == 'Cancelled'].shape[0]
        cancelled_percent = (cancelled_count / len(df_filtered)) * 100 if len(df_filtered) > 0 else 0
        st.markdown("""
         <div class='card'>
            <div style='display: flex; justify-content: center; margin-bottom: 4px;'>
                <div style='background-color: #9E9E9E; color: white; border-radius: 50%; width: 18px; height: 18px; display: flex; align-items: center; justify-content: center;'>
                    🚫
                </div>
            </div>
            <div class='metric-label'>Cancelled</div>
            <div class='medium-number'>{}</div>
            <div style='text-align: center; font-size: 12px; color: #666;'>{:.1f}% of total orders</div>
        </div>
        """.format(cancelled_count, cancelled_percent), unsafe_allow_html=True)

    # Column 4: Active
    with status_columns[3]:
        active_count = df_filtered[df_filtered['status'] == 'Active'].shape[0]
        active_percent = (active_count / len(df_filtered)) * 100 if len(df_filtered) > 0 else 0
        st.markdown("""
         <div class='card'>
            <div style='display: flex; justify-content: center; margin-bottom: 4px;'>
                <div style='background-color: var(--warning-color); color: white; border-radius: 50%; width: 18px; height: 18px; display: flex; align-items: center; justify-content: center;'>
                    ⏳
                </div>
            </div>
            <div class='metric-label'>Active</div>
            <div class='medium-number status-active'>{}</div>
            <div style='text-align: center; font-size: 12px; color: #666;'>{:.1f}% of total orders</div>
        </div>
        """.format(active_count, active_percent), unsafe_allow_html=True)

# Charts section with improved styling
st.markdown("<div class='section-header'>Analytics & Insights</div>", unsafe_allow_html=True)

# Create tabs for better organization
tabs = st.tabs(["📊 Orders Trend", "🌎 Geography"])

# Tab 3: Spacecraft Analysis
with tabs[0]:
    # st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: var(--primary-color); font-size: 15px;'>Orders Trend</h3>", unsafe_allow_html=True)
    
    # Satu baris: kontrol di kiri, metrik di kanan
    row_cols = st.columns([2, 2, 1, 1, 1])
    
    with row_cols[0]:
        # Definisikan opsi untuk dropdown
        trend_type_options = ["Spacecraft", "Type", "Status", "Countries", "Area (sqkm)"]
        
        # Buat dropdown untuk memilih jenis trend
        trend_type = st.selectbox(
            "View trends by:",
            options=trend_type_options,
            index=1,  # Default ke "Spacecraft" (index 0)
            key="orders_trend_type"
        )
    
    with row_cols[1]:
        # Add option to view monthly or daily trends
        trend_period = st.radio(
            "Time period:",
            options=["Monthly","Daily"],
            horizontal=True,
            key="orders_trend_period"
        )
    
    # Bar chart: Orders over time based on selected trend type
    # Define the grouping column based on trend_type
    if trend_type == "Spacecraft":
        group_column = 'spacecraft'
        chart_title = 'Order Trends by Spacecraft'
    elif trend_type == "Type":
        group_column = 'archiveTasking'
        chart_title = 'Order Trends by Type'
    elif trend_type == "Status":
        group_column = 'status'
        chart_title = 'Order Trends by Status'
    elif trend_type == "Countries":
        group_column = 'country'
        chart_title = 'Order Trends by Countries'
    elif trend_type == "Area (sqkm)":
        # Create area categories
        df_filtered['area_category'] = pd.cut(
            df_filtered['sqkm'], 
            bins=[0, 10, 250, 500, float('inf')],
            labels=['<10 sqkm', '10-250 sqkm', '250-500 sqkm', '>500 sqkm']
        )
        group_column = 'area_category'
        chart_title = 'Order Trends by Area (sqkm)'
    
    # Set time period for grouping
    if trend_period == "Daily":
        if trend_type == "Area (sqkm)":
            df_orders_trend = df_filtered.groupby([df_filtered['orderCreateTimestamp'].dt.date, 'area_category']).size().reset_index(name='Orders')
        else:
            df_orders_trend = df_filtered.groupby([df_filtered['orderCreateTimestamp'].dt.date, group_column]).size().reset_index(name='Orders')
        date_column = df_filtered['orderCreateTimestamp'].dt.date
        date_format = '%Y-%m-%d'
        x_title = 'Date'
        x_column = 'orderCreateTimestamp'
    else:  # Monthly
        df_filtered['month'] = df_filtered['orderCreateTimestamp'].dt.to_period('M')
        if trend_type == "Area (sqkm)":
            df_orders_trend = df_filtered.groupby([df_filtered['month'], 'area_category']).size().reset_index(name='Orders')
        else:
            df_orders_trend = df_filtered.groupby([df_filtered['month'], group_column]).size().reset_index(name='Orders')
        df_orders_trend['month'] = df_orders_trend['month'].dt.to_timestamp()
        date_format = '%b %Y'
        x_title = 'Month'
        x_column = 'month'
    
    # Add some insights
    total_orders = df_orders_trend['Orders'].sum()
    
    if trend_period == "Daily":
        avg_period_orders = df_orders_trend.groupby(x_column)['Orders'].sum().mean()
        period_label = "Daily"
        max_orders_period = df_orders_trend.groupby(x_column)['Orders'].sum().idxmax()
        max_orders_count = df_orders_trend.groupby(x_column)['Orders'].sum().max()
        max_date_str = max_orders_period.strftime(date_format) if hasattr(max_orders_period, 'strftime') else max_orders_period.to_timestamp().strftime(date_format)
    else:  # Monthly
        avg_period_orders = df_orders_trend.groupby(x_column)['Orders'].sum().mean()
        period_label = "Monthly"
        max_orders_period = df_orders_trend.groupby(x_column)['Orders'].sum().idxmax()
        max_orders_count = df_orders_trend.groupby(x_column)['Orders'].sum().max()
        max_date_str = max_orders_period.strftime(date_format) if hasattr(max_orders_period, 'strftime') else max_orders_period.to_timestamp().strftime(date_format)
    
    # Display insights di baris yang sama (kanan)
    with row_cols[2]:
        st.markdown(f"""
        <div class='compact-metric'>
            <div class='metric-label'>Total Orders</div>
            <div class='metric-value'>{total_orders:,}</div>
        </div>
        """, unsafe_allow_html=True)
    with row_cols[3]:
        st.markdown(f"""
        <div class='compact-metric'>
            <div class='metric-label'>Avg. {period_label} Orders</div>
            <div class='metric-value'>{avg_period_orders:.1f}</div>
        </div>
        """, unsafe_allow_html=True)
    with row_cols[4]:
        peak_label = "Peak Orders Month" if trend_period == "Monthly" else "Peak Orders Day"
        st.markdown(f"""
        <div class='compact-metric'>
            <div class='metric-label'>{peak_label}</div>
            <div class='metric-value'>{max_date_str}</div>
            <div class='metric-sub'>{max_orders_count} orders</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Enhanced chart
    fig_orders = px.bar(
        df_orders_trend,
        x=x_column,
        y='Orders',
        color=group_column,
        labels={x_column: x_title, 'Orders': 'Number of Orders', group_column: trend_type},
        color_discrete_sequence=px.colors.qualitative.Bold,
        title=chart_title
    )
    
    fig_orders.update_layout(
        height=320,
        margin=dict(l=20, r=20, t=30, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor='#EEEEEE'),
        yaxis=dict(showgrid=True, gridcolor='#EEEEEE'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        barmode='stack',
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_orders, use_container_width=True)

    # Calculate total usage in minutes
    total_minutes = df_filtered['seconds'].sum() / 60

    st.markdown("""
        <div style='margin-bottom: 8px; padding: 8px; background-color: #F5F7FA; border-radius: 5px;'>
            <span style='color: #555;'>📋 *Estimated allocation is based on the average order during VRS period. <br>
            *Allocation between spacecraft or orders types can be adjusted based on priority and preferences of user.</span>
        </div>
        """, unsafe_allow_html=True)
    
    
    # Display total usage metric
    st.markdown("<h3 style='text-align: center; color: var(--primary-color); font-size: 15px;'>Access Windows</h3>", unsafe_allow_html=True)
    
    # Create a more detailed spacecraft icons dictionary with descriptions
    spacecraft_icons = {
        'GE01': {'icon': '🛰️', 'color': '#4CAF50', 'description': 'GeoEye-1 - High resolution imaging satellite'},
        'WV01': {'icon': '🛰️', 'color': '#2196F3', 'description': 'WorldView-1 - Panchromatic imaging satellite'},
        'WV02': {'icon': '🛰️', 'color': '#9C27B0', 'description': 'WorldView-2 - 8-band multispectral satellite'},
        'WV03': {'icon': '🛰️', 'color': '#FF9800', 'description': 'WorldView-3 - Super-spectral, high-resolution satellite'},
        'WV04': {'icon': '🛰️', 'color': '#F44336', 'description': 'WorldView-4 - High-resolution Earth imaging satellite'},
        'No Data': {'icon': '❓', 'color': '#9E9E9E', 'description': 'Spacecraft information not available'}
    }
    
    # Spacecraft usage statistics
    spacecraft_counts = df_filtered['spacecraft'].value_counts().reset_index()
    spacecraft_counts.columns = ['Spacecraft', 'Orders']
    spacecraft_counts['Percentage'] = (spacecraft_counts['Orders'] / spacecraft_counts['Orders'].sum() * 100).round(1)
    
    # Calculate total minutes per spacecraft from chargeS
    spacecraft_minutes = df_filtered.groupby('spacecraft')['seconds'].sum().reset_index()
    spacecraft_minutes['Minutes'] = (spacecraft_minutes['seconds'] / 60).round(2)
    spacecraft_minutes = spacecraft_minutes.drop('seconds', axis=1)
    
    # Merge minutes data with spacecraft counts
    spacecraft_counts = pd.merge(spacecraft_counts, spacecraft_minutes, left_on='Spacecraft', right_on='spacecraft', how='left')
    spacecraft_counts = spacecraft_counts.drop('spacecraft', axis=1)
    spacecraft_counts['Minutes'] = spacecraft_counts['Minutes'].fillna(0)
    
    # Combine LG01-LG04 into single LG01-04 entry for Access Windows table
    access_windows_data = spacecraft_counts.copy()
    lg_entries = access_windows_data[access_windows_data['Spacecraft'].isin(['LG01', 'LG02', 'LG03', 'LG04'])]
    if not lg_entries.empty:
        # Sum up LG01-LG04 data
        lg_combined_orders = lg_entries['Orders'].sum()
        lg_combined_minutes = lg_entries['Minutes'].sum()
        lg_combined_percentage = (lg_combined_orders / spacecraft_counts['Orders'].sum() * 100).round(1)
        
        # Remove individual LG entries
        access_windows_data = access_windows_data[~access_windows_data['Spacecraft'].isin(['LG01', 'LG02', 'LG03', 'LG04'])]
        
        # Add combined LG01-04 entry
        lg_combined_row = pd.DataFrame({
            'Spacecraft': ['LG01-04'],
            'Orders': [lg_combined_orders],
            'Percentage': [lg_combined_percentage],
            'Minutes': [lg_combined_minutes]
        })
        access_windows_data = pd.concat([access_windows_data, lg_combined_row], ignore_index=True)
        access_windows_data = access_windows_data.sort_values('Orders', ascending=False).reset_index(drop=True)

    # Compute AO-only (TASKING-AO) realized values per spacecraft
    df_tasking_ao = df_filtered[df_filtered['archiveTasking'].astype(str).str.upper() == 'TASKING-AO']
    ao_counts = df_tasking_ao['spacecraft'].value_counts().reset_index()
    ao_counts.columns = ['Spacecraft', 'Orders']
    ao_minutes = df_tasking_ao.groupby('spacecraft')['seconds'].sum().reset_index()
    ao_minutes['Minutes'] = (ao_minutes['seconds'] / 60).round(2)
    ao_minutes = ao_minutes.drop('seconds', axis=1)
    ao_data = pd.merge(ao_counts, ao_minutes, left_on='Spacecraft', right_on='spacecraft', how='left').drop('spacecraft', axis=1)
    ao_total_orders = ao_counts['Orders'].sum() if not ao_counts.empty else 0
    if ao_total_orders > 0:
        ao_data['Percentage'] = (ao_data['Orders'] / ao_total_orders * 100).round(1)
    else:
        ao_data['Percentage'] = 0

    # Build lookup for AO-only realized values
    ao_lookup = {r['Spacecraft']: (r['Orders'], r['Percentage'], r['Minutes']) for _, r in ao_data.iterrows()}
    # Add combined LG01-04 realized values from AO-only subset
    lg_entries_ao = ao_data[ao_data['Spacecraft'].isin(['LG01', 'LG02', 'LG03', 'LG04'])]
    if not lg_entries_ao.empty:
        lg_orders_ao = lg_entries_ao['Orders'].sum()
        lg_minutes_ao = lg_entries_ao['Minutes'].sum()
        lg_percent_ao = ((lg_orders_ao / ao_total_orders) * 100).round(1) if ao_total_orders > 0 else 0
        ao_lookup['LG01-04'] = (lg_orders_ao, lg_percent_ao, lg_minutes_ao)

    # Create two columns for visualization and table
    # col1, col2 = st.columns([3, 2])
    
    # with col2:
    # Create a styled HTML table for spacecraft details
    html_table = """<table style='width:100%; border-collapse: collapse;'>""" 
    # Projection mapping for Access Windows
    projection_map = {
        'WV02': (3.19, 38.33),
        'WV03': (2.86, 34.37),
        'LG01-04': (7.96, 95.57),
        'WV04': (None, None),
        'GE01': (None, None)
    }
    # Totals for projection
    projection_total_minutes_per_month = 14.02
    projection_total_minutes_year = 168.27
    projection_total_aw_month = 7
    projection_total_aw_year = 84

    html_table += """<tr style='background-color: #E3F2FD;'>
        <th style='padding: 6px; text-align: center;' rowspan='2'>Icon</th>
        <th style='padding: 6px; text-align: left;' rowspan='2'>Spacecraft</th>
        <th style='padding: 6px; text-align: center;' colspan='2'>Realized</th>
        <th style='padding: 6px; text-align: center;' colspan='2'>Estimated allocation</th>
    </tr>
    <tr style='background-color: #E3F2FD;'>
        <th style='padding: 6px; text-align: right;'>Orders</th>
        <th style='padding: 6px; text-align: right;'>Minutes</th>
        <th style='padding: 6px; text-align: right;'>Minutes/month</th>
        <th style='padding: 6px; text-align: right;'>Minutes/year</th>
    </tr>"""
    # Exclude WV04 from Access Windows table
    access_windows_data = access_windows_data[access_windows_data['Spacecraft'] != 'WV04']

    for i, row in access_windows_data.iterrows():
        bg_color = '#F5F7FA' if i % 2 == 0 else 'white'
        # Use special icon for combined LG01-04
        if row['Spacecraft'] == 'LG01-04':
            icon_info = {'icon': '🛰️', 'color': '#FF5722'}
        else:
            icon_info = spacecraft_icons.get(row['Spacecraft'], {'icon': '❓', 'color': '#9E9E9E'})
        
        html_table += f"""<tr style='background-color: {bg_color};'>
            <td style='padding: 6px; text-align: center;'>
                <div style='background-color: {icon_info['color']}; color: white; border-radius: 50%; width: 19px; height: 19px; display: flex; align-items: center; justify-content: center; margin: 0 auto;'>
                    {icon_info['icon']}
                </div>
            </td>
            <td style='padding: 6px; text-align: left;'>{row['Spacecraft']}</td>
            <td style='padding: 6px; text-align: right;'>""" + (
                f"{ao_lookup.get(row['Spacecraft'], (None, None, None))[0]:,}" 
                if ao_lookup.get(row['Spacecraft'], (None, None, None))[0] is not None else ""
            ) + """</td>
            <td style='padding: 6px; text-align: right;'>""" + (
                f"{ao_lookup.get(row['Spacecraft'], (None, None, None))[2]:,.2f}" 
                if ao_lookup.get(row['Spacecraft'], (None, None, None))[2] is not None else ""
            ) + """</td>
            <td style='padding: 6px; text-align: right;'>""" + (
                f"{projection_map.get(row['Spacecraft'], (None, None))[0]:.2f}" 
                if projection_map.get(row['Spacecraft'], (None, None))[0] is not None else ""
            ) + """</td>
            <td style='padding: 6px; text-align: right;'>""" + (
                f"{projection_map.get(row['Spacecraft'], (None, None))[1]:.2f}" 
                if projection_map.get(row['Spacecraft'], (None, None))[1] is not None else ""
            ) + """</td>
        </tr>"""

    # Calculate totals for Realized columns from AO-only data
    total_realized_orders = sum(ao_lookup.get(row['Spacecraft'], (0, 0, 0))[0] or 0 for _, row in access_windows_data.iterrows())
    total_realized_minutes = sum(ao_lookup.get(row['Spacecraft'], (0, 0, 0))[2] or 0 for _, row in access_windows_data.iterrows())
    
    # Add realized totals row
    html_table += f"""<tr style='background-color: #E8F5E8;'>
        <td style='padding: 6px; text-align: center;'></td>
        <td style='padding: 6px; text-align: left;'><b>Total</b></td>
        <td style='padding: 6px; text-align: right;'><b>{total_realized_orders:,} AWs</b></td>
        <td style='padding: 6px; text-align: right;'><b>{total_realized_minutes:,.2f} mins</b></td>
        <td style='padding: 6px; text-align: right;'><b>{projection_total_minutes_per_month:.2f} mins (~7 AWs)</b></td>
        <td style='padding: 6px; text-align: right;'><b>{projection_total_minutes_year:.2f} mins (~84 AWs)</b></td>
    </tr>"""
    

    html_table += """</table>"""
    st.markdown(html_table, unsafe_allow_html=True)

    st.markdown("<h3 style='text-align: center; color: var(--primary-color); font-size: 15px;'>Indirect Tasking and Archive</h3>", unsafe_allow_html=True)
    
    # Create Indirect Tasking and Archive data by archiveTasking column
    indirect_tasking_data = df_filtered['archiveTasking'].value_counts().reset_index()
    indirect_tasking_data.columns = ['Type', 'Orders']
    
    # Calculate total area (sqkm) per type
    indirect_area = df_filtered.groupby('archiveTasking')['sqkm'].sum().reset_index()
    indirect_area['sqkm'] = indirect_area['sqkm'].round(2)
    
    # Merge sqkm data
    indirect_tasking_data = pd.merge(indirect_tasking_data, indirect_area, left_on='Type', right_on='archiveTasking', how='left')
    indirect_tasking_data = indirect_tasking_data.drop('archiveTasking', axis=1)
    indirect_tasking_data['sqkm'] = indirect_tasking_data['sqkm'].fillna(0)
    
    # Keep only Archive and TASKING-TO (case-insensitive)
    indirect_tasking_data = indirect_tasking_data[indirect_tasking_data['Type'].astype(str).str.upper().isin(['ARCHIVE', 'TASKING-TO'])].reset_index(drop=True)
    
    # Create a styled HTML table for indirect tasking details
    html_table = """<table style='width:100%; border-collapse: collapse;'>""" 
    html_table += """<tr style='background-color: #E3F2FD;'>
        <th style='padding: 6px; text-align: center; width: 10%;' rowspan='2'>Icon</th>
        <th style='padding: 6px; text-align: left; width: 25%;' rowspan='2'>Type</th>
        <th style='padding: 6px; text-align: center; width: 40%;' colspan='2'>Realized</th>
        <th style='padding: 6px; text-align: center; width: 25%;' colspan='1'>Estimated allocation</th>
    </tr>
    <tr style='background-color: #E3F2FD;'>
        <th style='padding: 6px; text-align: right; width: 20%;'>Orders</th>
        <th style='padding: 6px; text-align: right; width: 20%;'>sqkm</th>
        <th style='padding: 6px; text-align: right; width: 25%;'>sqkm</th>
    </tr>"""
    
    # Define icons for different types
    type_icons = {
        'ARCHIVE': {'icon': '📁', 'color': '#4CAF50'},
        'TASKING-TO': {'icon': '📡', 'color': '#9C27B0'},
    }
    quota_map = {
        'ARCHIVE': 1200000,
        'TASKING-TO': 3787.88
    }
    
    for i, row in indirect_tasking_data.iterrows():
        bg_color = '#F5F7FA' if i % 2 == 0 else 'white'
        type_key = str(row['Type']).upper()
        icon_info = type_icons.get(type_key, {'icon': '❓', 'color': '#9E9E9E'})
        label_text = "Archive" if type_key == "ARCHIVE" else type_key
        
        html_table += f"""<tr style='background-color: {bg_color};'>
            <td style='padding: 6px; text-align: center; width: 10%;'>
                <div style='background-color: {icon_info['color']}; color: white; border-radius: 50%; width: 19px; height: 19px; display: flex; align-items: center; justify-content: center; margin: 0 auto;'>
                    {icon_info['icon']}
                </div>
            </td>
            <td style='padding: 6px; text-align: left; width: 25%;'>{label_text}</td>
            <td style='padding: 6px; text-align: right; width: 20%;'>{row['Orders']:,}</td>
            <td style='padding: 6px; text-align: right; width: 20%;'>{row['sqkm']:,.2f}</td>
            <td style='padding: 6px; text-align: right; width: 25%;'>{quota_map.get(type_key, '') if quota_map.get(type_key) is None else f"{quota_map.get(type_key):,.2f}"}</td>
        </tr>"""
    
    html_table += """</table>"""
    st.markdown(html_table, unsafe_allow_html=True)


        

# Tab 4: Geography Analysis
with tabs[1]:
    # st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: var(--primary-color); font-size: 15px;'>Geographic Distribution</h3>", unsafe_allow_html=True)
    
    # Create two columns for map and country stats with better proportion
    col1, col2 = st.columns([1, 1])
    # Keep map and table the same height in this tab
    geo_height = 500

    # Process tabel terlebih dahulu agar pemilihan baris memperbarui query params
    with col2:
        st.markdown("<div class='section-header'>Orders List</div>", unsafe_allow_html=True)

        # Add a description for the table
        st.markdown("""
        <div style='margin-bottom: 8px; padding: 8px; background-color: #F5F7FA; border-radius: 5px;'>
            <span style='color: #555;'>📋 This table shows all orders matching your current filter criteria. Click on column headers to sort the data.</span>
        </div>
        """, unsafe_allow_html=True)

        # Prepare table data
        table_data = df_filtered[[
            'orderNumber', 
            'status', 
            'orderCreateTimestamp', 
            'archiveTasking',
            'orderCompleteTimestamp', 
            'country', 
            'latitude', 
            'longitude', 
            'seconds', 
            'sqkm'
        ]].copy()

        # Format columns
        table_data['orderCreateTimestamp'] = table_data['orderCreateTimestamp'].dt.strftime('%Y-%m-%d %H:%M')
        table_data['orderCompleteTimestamp'] = table_data['orderCompleteTimestamp'].dt.strftime('%Y-%m-%d %H:%M')
        table_data['Coordinates'] = table_data.apply(lambda row: f"{row['latitude']:.6f}, {row['longitude']:.6f}", axis=1)
        table_data['Minutes'] = table_data['seconds'] / 60

        # Format the sqkm with 2 decimal places
        table_data['sqkm'] = table_data['sqkm'].round(2)

        # Add a formatted status column with colored badges
        def format_status(status):
            if status == 'Complete':
                return f"<span style='background-color: #4CAF50; color: white; padding: 3px 8px; border-radius: 10px; font-size: 0.8em;'>✓ {status}</span>"
            elif status == 'Active':
                return f"<span style='background-color: #FF9800; color: white; padding: 3px 8px; border-radius: 10px; font-size: 0.8em;'>⟳ {status}</span>"
            elif status == 'Rejected':
                return f"<span style='background-color: #F44336; color: white; padding: 3px 8px; border-radius: 10px; font-size: 0.8em;'>✗ {status}</span>"
            elif status == 'Delivered':
                return f"<span style='background-color: #2196F3; color: white; padding: 3px 8px; border-radius: 10px; font-size: 0.8em;'>✓ {status}</span>"
            else:
                return f"<span style='background-color: #9E9E9E; color: white; padding: 3px 8px; border-radius: 10px; font-size: 0.8em;'>{status}</span>"

        # Select and rename columns for display
        display_data = table_data[[
            'orderNumber',
            'status', 
            'orderCreateTimestamp', 
            'archiveTasking', 
            'country',  
            'sqkm'
        ]].copy()

        display_data.columns = [
            'Order ID', 
            'Status', 
            'Create Date', 
            'Archive/Tasking', 
            'Country', 
            'Area (sqkm)'
        ]

        # Add search functionality
        search_term = st.text_input("🔍 Search orders by ID, country, or status", "")

        if search_term:
            # Case-insensitive search across multiple columns
            mask = display_data['Order ID'].astype(str).str.contains(search_term, case=False) | \
                display_data['Country'].astype(str).str.contains(search_term, case=False) | \
                display_data['Status'].astype(str).str.contains(search_term, case=False)
            display_data = display_data[mask]

        # Merge lat/lon into display data to build a Zoom link column
        display_data = display_data.join(table_data[["latitude", "longitude"]])
        display_data["Zoom"] = display_data.apply(lambda row: f"?geo_lat={row['latitude']:.6f}&geo_lon={row['longitude']:.6f}&geo_zoom=8", axis=1)

        # Render interactive table with single row selection using AgGrid
        grid_df = display_data.copy()

        gob = GridOptionsBuilder.from_dataframe(grid_df)
        gob.configure_selection(selection_mode="single", use_checkbox=False)
        gob.configure_grid_options(domLayout="normal")
        # Hide helper columns from view
        if "latitude" in grid_df.columns:
            gob.configure_column("latitude", hide=True)
        if "longitude" in grid_df.columns:
            gob.configure_column("longitude", hide=True)
        if "Zoom" in grid_df.columns:
            gob.configure_column("Zoom", hide=True)
        # Set widths for readability
        gob.configure_column("Order ID", width=140)
        gob.configure_column("Status", width=120)
        gob.configure_column("Create Date", width=160)
        gob.configure_column("Archive/Tasking", width=140)
        gob.configure_column("Country", width=120)
        gob.configure_column("Area (sqkm)", width=120)
        grid_options = gob.build()

        grid_resp = AgGrid(
            grid_df,
            gridOptions=grid_options,
            height=geo_height,
            fit_columns_on_grid_load=True,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            allow_unsafe_jscode=False,
        )

        # If a row is selected, update query params to zoom the map
        selected_rows = grid_resp.get("selected_rows", None)
        lat = None
        lon = None
        order_id = None
        # Helper to safely get value from dict/Series
        def _get_val(obj, key):
            try:
                return obj.get(key) if hasattr(obj, "get") else obj[key]
            except Exception:
                return None

        # Extract selected row and resolve Order ID
        if isinstance(selected_rows, list) and len(selected_rows) > 0:
            sel = selected_rows[0]
            order_id = _get_val(sel, "Order ID") or _get_val(sel, "orderNumber")
        elif isinstance(selected_rows, pd.DataFrame) and not selected_rows.empty:
            sel = selected_rows.iloc[0]
            order_id = _get_val(sel, "Order ID") or _get_val(sel, "orderNumber")

        # Lookup lat/lon from source table_data using orderNumber to avoid mismatches
        if order_id is not None:
            try:
                oid_str = str(order_id).strip()
                match = table_data[table_data["orderNumber"].astype(str).str.strip() == oid_str]
                if not match.empty:
                    lat = float(match.iloc[0]["latitude"]) if pd.notnull(match.iloc[0]["latitude"]) else None
                    lon = float(match.iloc[0]["longitude"]) if pd.notnull(match.iloc[0]["longitude"]) else None
            except Exception:
                lat = None
                lon = None

        # Fallback: try read lat/lon directly from selected row if lookup failed
        if (lat is None or lon is None) and 'sel' in locals():
            lat = _get_val(sel, "latitude")
            lon = _get_val(sel, "longitude")

        if lat is not None and lon is not None:
            try:
                st.query_params["geo_lat"] = f"{float(lat):.6f}"
                st.query_params["geo_lon"] = f"{float(lon):.6f}"
                st.query_params["geo_zoom"] = "10"
            except Exception:
                pass

        # Add download button for the filtered data (exclude helper columns)
        csv = grid_df.drop(columns=[c for c in ["latitude", "longitude", "Zoom"] if c in grid_df.columns]).to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download filtered data as CSV",
            data=csv,
            file_name="filtered_orders.csv",
            mime="text/csv",
            help="Download the currently filtered data as a CSV file"
        )

        st.markdown("</div>", unsafe_allow_html=True)

    # Setelah tabel memutakhirkan query params, render peta menggunakan nilai terbaru
    with col1:
        st.markdown("<h4 style='text-align: center; font-size: 14px;'>Order Locations</h4>", unsafe_allow_html=True)
        
        # Tombol untuk mengembalikan peta ke tampilan default
        reset_clicked = st.button("🔄 Reset Map View", help="Reset Map View")
        if reset_clicked:
            try:
                # Hapus parameter geo agar peta kembali ke default (mean & zoom awal)
                for k in ("geo_lat", "geo_lon", "geo_zoom"):
                    if k in st.query_params:
                        del st.query_params[k]
            except Exception:
                pass

        # Read selected coordinates from URL query params to auto-zoom map
        params = st.query_params
        sel_lat = params.get('geo_lat')
        sel_lon = params.get('geo_lon')
        sel_zoom = params.get('geo_zoom')

        # Create a map centered either on selection or on mean of points
        if sel_lat is not None and sel_lon is not None:
            try:
                map_center = [float(sel_lat), float(sel_lon)]
                zoom_start = int(sel_zoom) if sel_zoom is not None else 8
            except Exception:
                map_center = [df_filtered['latitude'].mean(), df_filtered['longitude'].mean()]
                zoom_start = 2
        else:
            map_center = [df_filtered['latitude'].mean(), df_filtered['longitude'].mean()]
            zoom_start = 2

        m = folium.Map(location=map_center, zoom_start=zoom_start, tiles='CartoDB positron')

        # Add marker cluster for better visualization
        marker_cluster = MarkerCluster().add_to(m)

        # Define status colors for markers
        status_colors = {
            'Complete': 'green',
            'Active': 'orange',
            'Rejected': 'red',
            'Delivered': 'blue'
        }

        # Add markers for each order with improved popup
        for idx, row in df_filtered.iterrows():
            # Determine marker color based on status
            color = status_colors.get(row['status'], 'gray')

            # Create a more detailed popup
            popup_text = f"""
            <div style='font-family: Arial, sans-serif; padding: 5px;'>
                <h4 style='margin-top: 0; color: #1E88E5;'>Order Details</h4>
                <table style='width: 100%; border-collapse: collapse;'>
                    <tr><td><b>Order ID:</b></td><td>{row['orderNumber']}</td></tr>
                    <tr><td><b>Status:</b></td><td>{row['status']}</td></tr>
                    <tr><td><b>Country:</b></td><td>{row['country']}</td></tr>
                    <tr><td><b>Area:</b></td><td>{row['sqkm']:.2f} sqkm</td></tr>
                    <tr><td><b>Created:</b></td><td>{row['orderCreateTimestamp'].strftime('%Y-%m-%d')}</td></tr>
                </table>
            </div>
            """

            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=folium.Popup(popup_text, max_width=300),
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(marker_cluster)

        # Display the map with height matching the table
        folium_static(m, height=geo_height+120)
    