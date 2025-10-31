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
        font-size: 2.5rem;
        font-weight: 700;
        color: var(--primary-color);
        margin-bottom: 1rem;
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #E3F2FD, #BBDEFB);
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* Card styling */
    .card {
        background-color: white;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        margin-bottom: 1rem;
    }
    
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
    }
    
    /* Metric numbers */
    .big-number {
        font-size: 42px;
        font-weight: 700;
        color: var(--primary-color);
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    .medium-number {
        font-size: 28px;
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
        font-size: 16px;
        color: var(--dark-text);
        text-align: center;
        font-weight: 500;
    }
    
    /* Section headers */
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--secondary-color);
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid var(--secondary-color);
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #F5F5F5;
        border-radius: 8px 8px 0px 0px;
        gap: 1px;
        padding: 0 15px;
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
        font-size: 14px;
    }
    
    .dataframe th {
        background-color: #E3F2FD;
        color: var(--dark-text);
        font-weight: 600;
        text-align: left;
        padding: 12px 15px;
    }
    
    .dataframe td {
        padding: 10px 15px;
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

# def convert_time_to_seconds(time_str):
#     try:
#         h, m, s = time_str.split(':')
#         seconds = int(h) * 3600 + int(m) * 60 + float(s)
#         return seconds
#     except:
#         return 0

# def format_currency(value):
#     try:
#         # Remove $ and commas, then convert to float
#         if isinstance(value, str):
#             value = float(value.replace('$', '').replace(',', ''))
#         return f"${value:,.2f}"
#     except:
#         return "$0.00"

# Data loading and processing function
@st.cache_data(ttl=3600)
def load_data():
#     # Load data
#     selected_columns = [
#         "idStore.orderNumber", 
#         "general.orderCompleteTimestamp", 
#         "customer.customerIdentifier", 
#         "customer.customerName", 
#         "general.status", 
#         "general.orderCreateTimestamp", 
#         "general.orderActiveTimestamp", 
#         "general.orderSubmitTimestamp", 
#         "general.orderType", 
#         "general.productType", 
#         "general.produced.area", 
#         "collection.requestedVehicles.0", 
#         "collection.collectionVehicles.0",
#         "general.produced.geoJson.properties.centroidX",
#         "general.produced.geoJson.properties.centroidY"
#     ]
    
#     # Define new column names mapping
#     new_column_names = {
#         "idStore.orderNumber": "orderNumber",
#         "general.orderCompleteTimestamp": "orderCompleteTimestamp",
#         "customer.customerIdentifier": "customerIdentifier", 
#         "customer.customerName": "customerName",
#         "general.status": "status",
#         "general.orderCreateTimestamp": "orderCreateTimestamp",
#         "general.orderActiveTimestamp": "orderActiveTimestamp",
#         "general.orderSubmitTimestamp": "orderSubmitTimestamp",
#         "general.orderType": "orderType",
#         "general.productType": "productType",
#         "general.produced.area": "area",
#         "collection.requestedVehicles.0": "requestedVehicles",
#         "collection.collectionVehicles.0": "collectionVehicles",
#         "general.produced.geoJson.properties.centroidX": "longitude",
#         "general.produced.geoJson.properties.centroidY": "latitude"
#     }
    
#     try:
#         # Read raw data
#         df_raw = pd.read_csv('raw.csv', usecols=selected_columns)
#         df_raw.rename(columns=new_column_names, inplace=True)
        
#         # Read result data
#         df_result = pd.read_csv('result.csv', sep=',', dtype={'Order Number': str}, na_filter=True).dropna(how='all')
#         df_result_f = df_result[(df_result['Order Notes'] == 'N')].copy()
#         df_result_f.columns = [to_camel_case(col) for col in df_result_f.columns]
        
#         # Clean order numbers
#         df_result_f.loc[:, 'orderNumber'] = df_result_f['orderNumber'].astype(str).apply(clean_number)
#         order_numbers_with_n = df_result_f['orderNumber'].astype(str).apply(clean_number).tolist()
#         df_raw['orderNumber'] = df_raw['orderNumber'].astype(str).apply(clean_number)
        
#         # Filter rows
#         def should_keep_row(row):
#             if row['status'] != 'Complete':
#                 return True
#             else:
#                 idstore_number = row['orderNumber']
#                 if idstore_number in order_numbers_with_n:
#                     return True
#                 return False
        
#         df_raw['keep_row'] = df_raw.apply(should_keep_row, axis=1)
#         df_matching = df_raw[df_raw['keep_row']].copy()
#         df_matching.drop(['keep_row'], axis=1, inplace=True)
        
#         # Clean data
#         df_matching = df_matching.replace("No Data", np.nan)
#         df_matching["spacecraft"] = (
#             df_matching["collectionVehicles"]
#             .fillna(df_matching["requestedVehicles"])
#             .fillna("No Data")
#         )
#         df_matching = df_matching.drop(columns=["requestedVehicles", "collectionVehicles"])
        
#         # Merge dataframes
#         df_merged = pd.merge(df_matching, df_result_f, on='orderNumber', how='left')
    
    try: 
        import streamlit as st
        import pandas as pd
        import requests
        from io import BytesIO
        import base64 
        onedrive_short_link = "https://1drv.ms/x/c/dc8660967561258c/EesHHNPC1x1BofD2js_0uHsBNiQ5V_iww706GduttkAWPg?e=iBT3yg"

        def get_onedrive_direct_link(share_url):
            """Convert OneDrive sharing link to direct download link"""
            try:
                # Encode URL untuk API OneDrive
                encoded = base64.b64encode(share_url.encode()).decode()
                # Hilangkan padding '=' yang bisa bikin masalah
                encoded = encoded.rstrip('=')
                direct_url = f"https://api.onedrive.com/v1.0/shares/u!{encoded}/root/content"
                return direct_url
            except Exception as e:
                st.error(f"❌ Gagal convert link: {e}")
                return None

        try:
            st.info("🔄 Mengambil file dari OneDrive...")
            
            # Method 1: Coba pakai API OneDrive
            direct_link = get_onedrive_direct_link(onedrive_short_link)
            
            if direct_link:
                st.write("🔗 Direct download URL:", direct_link)
                
                # Ambil file dari OneDrive
                file_resp = requests.get(direct_link, timeout=30)
                
                # Validasi response
                if file_resp.status_code == 200:
                    content_type = file_resp.headers.get("Content-Type", "")
                    
                    # Cek apakah benar file Excel
                    if "html" in content_type.lower():
                        st.error("🚫 Gagal: Link masih mengarah ke halaman HTML, bukan file Excel.")
                        st.info("💡 **Solusi alternatif:**")
                        st.markdown("""
                        1. Buka link OneDrive di browser
                        2. Klik kanan file → **Download**
                        3. Upload file Excel nya ke Streamlit menggunakan file uploader
                        """)
                        
                        # Tambahkan file uploader sebagai backup
                        uploaded_file = st.file_uploader("📤 Upload file Excel manual", type=['xlsx', 'xls'])
                        if uploaded_file:
                            df = pd.read_excel(uploaded_file, engine="openpyxl")
                            st.success("✅ File Excel berhasil dibaca!")
                            st.dataframe(df)
                    else:
                        # Baca Excel dari bytes
                        df = pd.read_excel(BytesIO(file_resp.content), engine="openpyxl")
                        st.success("✅ File Excel berhasil dibaca!")
                        
                        # Tampilkan info dasar
                        st.write(f"**Jumlah baris:** {len(df)}")
                        st.write(f"**Jumlah kolom:** {len(df.columns)}")
                        
                        # Tampilkan dataframe
                        st.dataframe(df)
                        
                        # Tombol download salinan
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                            df.to_excel(writer, index=False, sheet_name="Data")
                        
                        output.seek(0)
                        st.download_button(
                            label="📥 Download salinan Excel",
                            data=output.getvalue(),
                            file_name="copy_from_onedrive.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                else:
                    st.error(f"❌ Gagal mengambil file. Status code: {file_resp.status_code}")
                    st.info("💡 Coba gunakan file uploader di bawah:")
                    
                    uploaded_file = st.file_uploader("📤 Upload file Excel manual", type=['xlsx', 'xls'])
                    if uploaded_file:
                        df = pd.read_excel(uploaded_file, engine="openpyxl")
                        st.success("✅ File Excel berhasil dibaca!")
                        st.dataframe(df)

        except requests.exceptions.RequestException as e:
            st.error(f"❌ Error koneksi: {e}")
            st.info("💡 Upload file manual:")
            uploaded_file = st.file_uploader("📤 Upload file Excel", type=['xlsx', 'xls'])
            if uploaded_file:
                df = pd.read_excel(uploaded_file, engine="openpyxl")
                st.success("✅ File Excel berhasil dibaca!")
                st.dataframe(df)

        except Exception as e:
            st.error(f"❌ Gagal membaca file: {e}")
            st.info("💡 **Solusi:**")
            st.markdown("""
            - Pastikan link OneDrive adalah link **sharing** yang valid
            - Pastikan file memiliki permission **"Anyone with the link"**
            - Atau upload file manual menggunakan uploader di bawah
            """)
            
            uploaded_file = st.file_uploader("📤 Upload file Excel manual", type=['xlsx', 'xls'])
            if uploaded_file:
                df = pd.read_excel(uploaded_file, engine="openpyxl")
                st.success("✅ File Excel berhasil dibaca!")
                st.dataframe(df)
        # Geocoding
        world = gpd.read_file('world_admin.geojson')
        country_column = 'name'
        
        geometry = [Point(xy) for xy in zip(df_merged['longitude'], df_merged['latitude'])]
        df_geo = gpd.GeoDataFrame(df_merged, geometry=geometry, crs="EPSG:4326")
        
        # Spatial join
        joined = gpd.sjoin(df_geo, world, how="left", predicate='within')
        
        # Handle missing countries
        missing_countries = joined[joined[country_column].isna()]
        if len(missing_countries) > 0:
            for idx, row in missing_countries.iterrows():
                nearest_country = find_country(row.geometry, world, country_column)
                joined.at[idx, country_column] = nearest_country
        
        # Add country to merged dataframe
        df_merged['country'] = joined[country_column]
        
        # Convert to numeric
        df_merged['latitude'] = pd.to_numeric(df_merged['latitude'], errors='coerce')
        df_merged['longitude'] = pd.to_numeric(df_merged['longitude'], errors='coerce')
        
        # Clean final dataframe
        df_clean = df_merged.dropna(subset=['latitude', 'longitude'])
        
        # Convert timestamps to datetime
        for col in ['orderCreateTimestamp', 'orderActiveTimestamp', 'orderSubmitTimestamp', 'orderCompleteTimestamp']:
            df_clean[col] = pd.to_datetime(df_clean[col])
        
        # Extract date from completeDate
        df_clean['completeDate'] = pd.to_datetime(df_clean['completeDate'])
        
        # Calculate time to complete (in minutes)
        df_clean['timeToComplete'] = (df_clean['orderCompleteTimestamp'] - df_clean['orderActiveTimestamp']).dt.total_seconds() / 60
        
        # Convert chargeS to seconds
        df_clean['seconds'] = pd.to_timedelta(df_clean['chargeS']).dt.total_seconds()
        
        # Clean charge column (remove $ and commas)
        df_clean['charge'] = df_clean['charge'].str.replace('$', '').str.replace(',', '').astype(float)
   
        return df_clean
    
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

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

if archive_tasking_filter != "All":
    df_filtered = df[df['archiveTasking'] == archive_tasking_filter]
else:
    df_filtered = df

# Add sidebar sections with better styling
st.sidebar.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
st.sidebar.markdown("<div style='background-color: var(--light-bg); padding: 10px; border-radius: 5px; margin-bottom: 15px;'>", unsafe_allow_html=True)

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
st.write(df_filtered['status'].value_counts())

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

# Main dashboard content
st.markdown("<div class='section-header'>Key Performance Metrics</div>", unsafe_allow_html=True)

# Big Numbers Row with card styling
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    <div class='card'>
        <div class='metric-label'>Total Orders</div>
        <div class='big-number'>{}</div>
        <div style='text-align: center; font-size: 12px; color: #666;'>Total number of orders in selected period</div>
    </div>
    """.format(len(df_filtered)), unsafe_allow_html=True)

with col2:
    total_area = df_filtered['sqkm'].sum()
    st.markdown("""
    <div class='card'>
        <div class='metric-label'>Area Ordered</div>
        <div class='big-number'>{:,.2f}</div>
        <div style='text-align: center; font-size: 12px; color: #666;'>Total square kilometers</div>
    </div>
    """.format(total_area), unsafe_allow_html=True)

with col3:
    total_revenue = df_filtered['charge'].sum()
    st.markdown("""
    <div class='card'>
        <div class='metric-label'>Revenue</div>
        <div class='big-number'>${:,.2f}</div>
        <div style='text-align: center; font-size: 12px; color: #666;'>Total revenue generated</div>
    </div>
    """.format(total_revenue), unsafe_allow_html=True)

with col4:
    completed_delivered = df_filtered[df_filtered['status'].isin(['Complete', 'Delivered'])].shape[0]
    success_rate = (completed_delivered / len(df_filtered)) * 100 if len(df_filtered) > 0 else 0
    st.markdown("""
    <div class='card'>
        <div class='metric-label'>Success Rate</div>
        <div class='big-number'>{:.1f}%</div>
        <div style='text-align: center; font-size: 12px; color: #666;'>Completed/delivered orders</div>
    </div>
    """.format(success_rate), unsafe_allow_html=True)

# Status counts with improved styling
st.markdown("<div class='section-header'>Status Breakdown</div>", unsafe_allow_html=True)

# Get unique status values and combine Completed and Delivered
status_counts = df_filtered['status'].value_counts()
unique_statuses = status_counts.index.tolist()

# Define columns based on unique statuses (including Cancelled)
status_columns = st.columns(4)

# Column 1: Rejected
with status_columns[0]:
    rejected_count = df_filtered[df_filtered['status'] == 'Rejected'].shape[0]
    rejected_percent = (rejected_count / len(df_filtered)) * 100 if len(df_filtered) > 0 else 0
    st.markdown("""
    <div class='card'>
        <div style='display: flex; justify-content: center; margin-bottom: 10px;'>
            <div style='background-color: var(--danger-color); color: white; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center;'>
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
        <div style='display: flex; justify-content: center; margin-bottom: 10px;'>
            <div style='background-color: var(--success-color); color: white; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center;'>
                ✅
            </div>
        </div>
        <div class='metric-label'>Completed/Delivered</div>
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
        <div style='display: flex; justify-content: center; margin-bottom: 10px;'>
            <div style='background-color: #9E9E9E; color: white; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center;'>
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
        <div style='display: flex; justify-content: center; margin-bottom: 10px;'>
            <div style='background-color: var(--warning-color); color: white; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center;'>
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
tabs = st.tabs(["📈 Revenue", "📊 Orders", "🛰️ Spacecraft", "🌎 Geography", "📋 Details"])

# Tab 1: Revenue Analysis
with tabs[0]:
    # st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: var(--primary-color);'>Revenue Trends</h3>", unsafe_allow_html=True)

    # Add option to view monthly or daily trends
    trend_period = st.radio(
        "View trends by:",
        options=["Monthly","Daily"],
        horizontal=True,
        key="revenue_trend_period"
    )
    
    # Line chart: Revenue over time with improved styling
    if trend_period == "Daily":
        df_revenue_time = df_filtered.groupby(df_filtered['orderCreateTimestamp'].dt.date)['charge'].sum().reset_index()
        date_format = '%Y-%m-%d'
        x_title = 'Date'
    else:  # Monthly
        df_filtered['month'] = df_filtered['orderCreateTimestamp'].dt.to_period('M')
        df_revenue_time = df_filtered.groupby('month')['charge'].sum().reset_index()
        df_revenue_time['month'] = df_revenue_time['month'].dt.to_timestamp()
        date_format = '%b %Y'
        x_title = 'Month'
    
    # Rename columns for consistency
    df_revenue_time.columns = ['Date', 'Revenue'] if trend_period == "Daily" else ['Month', 'Revenue']
    
    # Add some insights
    total_revenue = df_revenue_time['Revenue'].sum()
    
    if trend_period == "Daily":
        avg_period_revenue = df_revenue_time['Revenue'].mean()
        period_label = "Daily"
        max_revenue_period = df_revenue_time.loc[df_revenue_time['Revenue'].idxmax()]
        max_date_str = max_revenue_period['Date'].strftime(date_format)
    else:  # Monthly
        avg_period_revenue = df_revenue_time['Revenue'].mean()
        period_label = "Monthly"
        max_revenue_period = df_revenue_time.loc[df_revenue_time['Revenue'].idxmax()]
        max_date_str = max_revenue_period['Month'].strftime(date_format)
    
    # Display insights
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Revenue", f"${total_revenue:,.2f}")
    with col2:
        st.metric(f"Avg. {period_label} Revenue", f"${avg_period_revenue:,.2f}")
    with col3:
        st.metric(f"Peak Revenue {period_label.rstrip('ly')}", f"{max_date_str}", f"${max_revenue_period['Revenue']:,.2f}")
    
    # Enhanced chart
    x_column = 'Date' if trend_period == "Daily" else 'Month'
    
    fig_revenue = px.line(
        df_revenue_time, 
        x=x_column, 
        y='Revenue',
        labels={'Revenue': 'Revenue ($)', x_column: x_title},
        line_shape='linear'
    )
    
    fig_revenue.update_traces(line=dict(color='#1E88E5', width=3))
    fig_revenue.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=30, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor='#EEEEEE'),
        yaxis=dict(showgrid=True, gridcolor='#EEEEEE'),
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_revenue, use_container_width=True)
    # st.markdown("</div>", unsafe_allow_html=True)

# Tab 2: Orders Analysis
with tabs[1]:
    # st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: var(--primary-color);'>Order Trends by Spacecraft</h3>", unsafe_allow_html=True)
    
    # Add option to view monthly or daily trends
    trend_period = st.radio(
        "View trends by:",
        options=["Monthly","Daily"],
        horizontal=True,
        key="orders_trend_period"
    )
    
    # Bar chart: Orders over time by spacecraft with improved styling
    if trend_period == "Daily":
        df_orders_spacecraft = df_filtered.groupby([df_filtered['orderCreateTimestamp'].dt.date, 'spacecraft']).size().reset_index(name='Orders')
        date_column = df_filtered['orderCreateTimestamp'].dt.date
        date_format = '%Y-%m-%d'
        x_title = 'Date'
        x_column = 'orderCreateTimestamp'
    else:  # Monthly
        df_filtered['month'] = df_filtered['orderCreateTimestamp'].dt.to_period('M')
        df_orders_spacecraft = df_filtered.groupby([df_filtered['month'], 'spacecraft']).size().reset_index(name='Orders')
        df_orders_spacecraft['month'] = df_orders_spacecraft['month'].dt.to_timestamp()
        date_format = '%b %Y'
        x_title = 'Month'
        x_column = 'month'
    
    # Add some insights
    total_orders = df_orders_spacecraft['Orders'].sum()
    
    if trend_period == "Daily":
        avg_period_orders = df_orders_spacecraft.groupby(x_column)['Orders'].sum().mean()
        period_label = "Daily"
        max_orders_period = df_orders_spacecraft.groupby(x_column)['Orders'].sum().idxmax()
        max_orders_count = df_orders_spacecraft.groupby(x_column)['Orders'].sum().max()
        max_date_str = max_orders_period.strftime(date_format) if hasattr(max_orders_period, 'strftime') else max_orders_period.to_timestamp().strftime(date_format)
    else:  # Monthly
        avg_period_orders = df_orders_spacecraft.groupby(x_column)['Orders'].sum().mean()
        period_label = "Monthly"
        max_orders_period = df_orders_spacecraft.groupby(x_column)['Orders'].sum().idxmax()
        max_orders_count = df_orders_spacecraft.groupby(x_column)['Orders'].sum().max()
        max_date_str = max_orders_period.strftime(date_format) if hasattr(max_orders_period, 'strftime') else max_orders_period.to_timestamp().strftime(date_format)
    
    # Display insights
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Orders", f"{total_orders:,}")
    with col2:
        st.metric(f"Avg. {period_label} Orders", f"{avg_period_orders:.1f}")
    with col3:
        st.metric(f"Peak Orders {period_label.rstrip('ly')}", f"{max_date_str}", f"{max_orders_count} orders")
    
    # Enhanced chart
    fig_orders = px.bar(
        df_orders_spacecraft,
        x=x_column,
        y='Orders',
        color='spacecraft',
        labels={x_column: x_title, 'Orders': 'Number of Orders', 'spacecraft': 'Spacecraft'},
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    
    fig_orders.update_layout(
        height=400,
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
    # st.markdown("</div>", unsafe_allow_html=True)

# Tab 3: Spacecraft Analysis
with tabs[2]:
    # st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: var(--primary-color);'>Spacecraft Usage Analysis</h3>", unsafe_allow_html=True)
    
    # Calculate total usage in minutes
    total_minutes = df_filtered['seconds'].sum() / 60
    
    # Display total usage metric
    st.metric("Total Spacecraft Usage", f"{total_minutes:,.2f} minutes")
    
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
    
    # Create two columns for visualization and table
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # Create a pie chart for spacecraft usage
        fig_spacecraft = px.pie(
            spacecraft_counts, 
            values='Orders', 
            names='Spacecraft',
            hole=0.4,
            color_discrete_sequence=[spacecraft_icons.get(s, {'color': '#9E9E9E'})['color'] for s in spacecraft_counts['Spacecraft']]
        )
        
        fig_spacecraft.update_layout(
            margin=dict(l=20, r=20, t=30, b=20),
            legend=dict(orientation='h', yanchor='bottom', y=-0.2, xanchor='center', x=0.5)
        )
        
        st.plotly_chart(fig_spacecraft, use_container_width=True)
    
    with col2:
        # Create a styled HTML table for spacecraft details
        html_table = """<table style='width:100%; border-collapse: collapse;'>""" 
        html_table += """<tr style='background-color: #E3F2FD;'>
            <th style='padding: 10px; text-align: center;'>Icon</th>
            <th style='padding: 10px; text-align: left;'>Spacecraft</th>
            <th style='padding: 10px; text-align: right;'>Orders</th>
            <th style='padding: 10px; text-align: right;'>%</th>
            <th style='padding: 10px; text-align: right;'>Minutes</th>
        </tr>"""
        
        for i, row in spacecraft_counts.iterrows():
            bg_color = '#F5F7FA' if i % 2 == 0 else 'white'
            icon_info = spacecraft_icons.get(row['Spacecraft'], {'icon': '❓', 'color': '#9E9E9E'})
            
            html_table += f"""<tr style='background-color: {bg_color};'>
                <td style='padding: 10px; text-align: center;'>
                    <div style='background-color: {icon_info['color']}; color: white; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; margin: 0 auto;'>
                        {icon_info['icon']}
                    </div>
                </td>
                <td style='padding: 10px; text-align: left;'>{row['Spacecraft']}</td>
                <td style='padding: 10px; text-align: right;'>{row['Orders']:,}</td>
                <td style='padding: 10px; text-align: right;'>{row['Percentage']}%</td>
                <td style='padding: 10px; text-align: right;'>{row['Minutes']:,.2f}</td>
            </tr>"""
        
        html_table += """</table>"""
        st.markdown(html_table, unsafe_allow_html=True)
        
        # Add a small description section
        st.markdown("<div style='margin-top: 20px; font-size: 14px;'>", unsafe_allow_html=True)
        for spacecraft, info in spacecraft_icons.items():
            if spacecraft in spacecraft_counts['Spacecraft'].values:
                st.markdown(f"<div style='margin-bottom: 5px;'><b>{spacecraft}</b>: {info['description']}</div>", unsafe_allow_html=True)
        # Removed closing div tag
    
    # st.markdown("</div>", unsafe_allow_html=True)

# Tab 4: Geography Analysis
with tabs[3]:
    # st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: var(--primary-color);'>Geographic Distribution</h3>", unsafe_allow_html=True)
    
    # Create two columns for map and country stats with better proportion
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        st.markdown("<h4 style='text-align: center;'>Order Locations</h4>", unsafe_allow_html=True)
        
        # Create a map centered at the mean of all points with improved styling
        map_center = [df_filtered['latitude'].mean(), df_filtered['longitude'].mean()]
        m = folium.Map(location=map_center, zoom_start=2, tiles='CartoDB positron')
        
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
        
        # Add a legend to the map
        # legend_html = '''
        #     <div style="position: fixed; 
        #                 bottom: 50px; right: 50px; width: 150px; height: 120px; 
        #                 border:2px solid grey; z-index:9999; font-size:12px;
        #                 background-color: white; padding: 10px; border-radius: 5px;">
        #         <p style="margin-top: 0; font-weight: bold;">Status</p>
        #         <div style="display: flex; align-items: center; margin-bottom: 5px;">
        #             <div style="background-color: green; width: 15px; height: 15px; border-radius: 50%; margin-right: 5px;"></div>
        #             <span>Complete</span>
        #         </div>
        #         <div style="display: flex; align-items: center; margin-bottom: 5px;">
        #             <div style="background-color: orange; width: 15px; height: 15px; border-radius: 50%; margin-right: 5px;"></div>
        #             <span>Active</span>
        #         </div>
        #         <div style="display: flex; align-items: center; margin-bottom: 5px;">
        #             <div style="background-color: red; width: 15px; height: 15px; border-radius: 50%; margin-right: 5px;"></div>
        #             <span>Rejected</span>
        #         </div>
        #         <div style="display: flex; align-items: center;">
        #             <div style="background-color: blue; width: 15px; height: 15px; border-radius: 50%; margin-right: 5px;"></div>
        #             <span>Delivered</span>
        #         </div>
        #     </div>
        # '''
        # m.get_root().html.add_child(folium.Element(legend_html))
        
        # Display the map
        folium_static(m)
    
    with col2:
        st.markdown("<h4 style='text-align: center;'>List of Countries</h4>", unsafe_allow_html=True)
        
        # Calculate country statistics with additional metrics
        country_stats = df_filtered.groupby('country').agg({
            'sqkm': ['sum', 'mean', 'max'],
            'orderNumber': 'count'
        }).reset_index()
        
        # Flatten the multi-level columns
        country_stats.columns = ['Country', 'Total Area (sqkm)', 'Avg Area (sqkm)', 'Max Area (sqkm)', 'Orders']
        country_stats = country_stats.sort_values('Total Area (sqkm)', ascending=False)
        
        # Create a styled HTML table for country stats with scrollable container
        # Add container with fixed height and scrolling - match map height and add margin
        # overflow-y: auto untuk scroll vertikal, overflow-x: hidden untuk mencegah scroll horizontal
        html_container = """<div style='height: 500px; overflow-y: auto; overflow-x: hidden; padding: 0; margin: 0; border: 1px solid #e0e0e0; border-radius: 5px;'>"""
        
        html_table = """<table style='width:100%; table-layout: fixed; border-collapse: collapse;'>"""
        html_table += """<tr style='background-color: #E3F2FD; position: sticky; top: 0; z-index: 10;'>
            <th style='padding: 8px; text-align: left; width: 30%;'>Country</th>
            <th style='padding: 8px; text-align: right; width: 20%;'>Total Area (sqkm)</th>
            <th style='padding: 8px; text-align: right; width: 20%;'>Avg Area (sqkm)</th>
            <th style='padding: 8px; text-align: right; width: 20%;'>Max Area (sqkm)</th>
            <th style='padding: 8px; text-align: right; width: 10%;'>Orders</th>
        </tr>"""
        
        for i, row in country_stats.iterrows():
            bg_color = '#F5F7FA' if i % 2 == 0 else 'white'
            html_table += f"""<tr style='background-color: {bg_color}; border-bottom: 1px solid #e0e0e0;'>
                <td style='padding: 8px; text-align: left; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{row['Country']}</td>
                <td style='padding: 8px; text-align: right; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{row['Total Area (sqkm)']:,.2f}</td>
                <td style='padding: 8px; text-align: right; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{row['Avg Area (sqkm)']:,.2f}</td>
                <td style='padding: 8px; text-align: right; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{row['Max Area (sqkm)']:,.2f}</td>
                <td style='padding: 8px; text-align: right; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{row['Orders']}</td>
            </tr>"""
        
        html_table += """</table>"""
        
        # Close the scrollable container
        html_content = html_container + html_table + """</div>"""
        st.markdown(html_content, unsafe_allow_html=True)
    
    # Removed closing div tag

# Tab 5: Details Analysis
with tabs[4]:
    # st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: var(--primary-color);'>Order Details Analysis</h3>", unsafe_allow_html=True)
    
    # Key metrics in cards
    col1, col2 = st.columns(2)
    
    with col1:
        # Average area per order
        avg_sqkm = df_filtered['sqkm'].mean()
        st.markdown("""
        <div style='background-color: #E3F2FD; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
            <div style='text-align: center; font-size: 16px; font-weight: 500; margin-bottom: 10px;'>Average Area per Order</div>
            <div style='text-align: center; font-size: 28px; font-weight: 700; color: var(--primary-color);'>{:.2f} sqkm</div>
        </div>
        """.format(avg_sqkm), unsafe_allow_html=True)
    
    with col2:
        # Average time to complete
        avg_time_to_complete = df_filtered['timeToComplete'].mean()
        st.markdown("""
        <div style='background-color: #E3F2FD; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
            <div style='text-align: center; font-size: 16px; font-weight: 500; margin-bottom: 10px;'>Average Time to Complete</div>
            <div style='text-align: center; font-size: 28px; font-weight: 700; color: var(--primary-color);'>{:.2f} minutes</div>
        </div>
        """.format(avg_time_to_complete), unsafe_allow_html=True)
    
    # Create tabs for different detail views
    detail_tabs = st.tabs(["📦 Product Types", "📋 Order Types", "📝 Descriptions", "⏱️ Responsiveness"])
    
    # Tab 1: Product Types
    with detail_tabs[0]:
        # Product Type with improved styling
        product_counts = df_filtered['productType'].value_counts().reset_index()
        product_counts.columns = ['Product Type', 'Count']
        product_counts['Percentage'] = (product_counts['Count'] / product_counts['Count'].sum() * 100).round(1)
        
        # Create two columns for chart and table
        pcol1, pcol2 = st.columns([3, 2])
        
        with pcol1:
            fig_product = px.bar(
                product_counts,
                x='Product Type',
                y='Count',
                color='Product Type',
                color_discrete_sequence=px.colors.qualitative.Bold,
                text='Count'
            )
            
            fig_product.update_layout(
                height=350,
                margin=dict(l=20, r=20, t=30, b=20),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor='#EEEEEE'),
                showlegend=False
            )
            
            fig_product.update_traces(texttemplate='%{text}', textposition='outside')
            
            st.plotly_chart(fig_product, use_container_width=True)
        
        with pcol2:
            # Create a styled HTML table for product types
            html_table = """<table style='width:100%; border-collapse: collapse;'>""" 
            html_table += """<tr style='background-color: #E3F2FD;'>
                <th style='padding: 8px; text-align: left;'>Product Type</th>
                <th style='padding: 8px; text-align: right;'>Count</th>
                <th style='padding: 8px; text-align: right;'>%</th>
            </tr>"""
            
            for i, row in product_counts.iterrows():
                bg_color = '#F5F7FA' if i % 2 == 0 else 'white'
                html_table += f"""<tr style='background-color: {bg_color};'>
                    <td style='padding: 8px; text-align: left;'>{row['Product Type']}</td>
                    <td style='padding: 8px; text-align: right;'>{row['Count']}</td>
                    <td style='padding: 8px; text-align: right;'>{row['Percentage']}%</td>
                </tr>"""
            
            html_table += """</table>"""
            st.markdown(html_table, unsafe_allow_html=True)
    
    # Tab 2: Order Types
    with detail_tabs[1]:
        # Order Type with improved styling
        order_type_counts = df_filtered['orderType'].value_counts().reset_index()
        order_type_counts.columns = ['Order Type', 'Count']
        order_type_counts['Percentage'] = (order_type_counts['Count'] / order_type_counts['Count'].sum() * 100).round(1)
        
        # Create two columns for chart and table
        ocol1, ocol2 = st.columns([3, 2])
        
        with ocol1:
            fig_order_type = px.bar(
                order_type_counts,
                x='Order Type',
                y='Count',
                color='Order Type',
                color_discrete_sequence=px.colors.qualitative.Pastel,
                text='Count'
            )
            
            fig_order_type.update_layout(
                height=350,
                margin=dict(l=20, r=20, t=30, b=20),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor='#EEEEEE'),
                showlegend=False
            )
            
            fig_order_type.update_traces(texttemplate='%{text}', textposition='outside')
            
            st.plotly_chart(fig_order_type, use_container_width=True)
        
        with ocol2:
            # Create a styled HTML table for order types
            html_table = """<table style='width:100%; border-collapse: collapse;'>""" 
            html_table += """<tr style='background-color: #E3F2FD;'>
                <th style='padding: 8px; text-align: left;'>Order Type</th>
                <th style='padding: 8px; text-align: right;'>Count</th>
                <th style='padding: 8px; text-align: right;'>%</th>
            </tr>"""
            
            for i, row in order_type_counts.iterrows():
                bg_color = '#F5F7FA' if i % 2 == 0 else 'white'
                html_table += f"""<tr style='background-color: {bg_color};'>
                    <td style='padding: 8px; text-align: left;'>{row['Order Type']}</td>
                    <td style='padding: 8px; text-align: right;'>{row['Count']}</td>
                    <td style='padding: 8px; text-align: right;'>{row['Percentage']}%</td>
                </tr>"""
            
            html_table += """</table>"""
            st.markdown(html_table, unsafe_allow_html=True)
    
    # Tab 3: Descriptions
    with detail_tabs[2]:
        # Order Description with improved styling
        description_counts = df_filtered['orderDescription'].value_counts().reset_index()
        description_counts.columns = ['Order Description', 'Count']
        description_counts['Percentage'] = (description_counts['Count'] / description_counts['Count'].sum() * 100).round(1)
        
        # Sort by count for better visualization
        description_counts = description_counts.sort_values('Count', ascending=True)
        
        fig_description = px.bar(
            description_counts,
            x='Count',
            y='Order Description',
            orientation='h',
            color='Count',
            color_continuous_scale='Viridis',
            text='Count'
        )
        
        fig_description.update_layout(
            height=400,
            margin=dict(l=20, r=20, t=30, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=True, gridcolor='#EEEEEE'),
            yaxis=dict(showgrid=False),
            coloraxis_showscale=False
        )
        
        fig_description.update_traces(texttemplate='%{text}', textposition='outside')
        
        st.plotly_chart(fig_description, use_container_width=True)
    
    # Tab 4: Responsiveness
    with detail_tabs[3]:
        # Responsiveness with improved styling
        responsiveness_counts = df_filtered['responsiveness'].value_counts().reset_index()
        responsiveness_counts.columns = ['Responsiveness', 'Count']
        responsiveness_counts['Percentage'] = (responsiveness_counts['Count'] / responsiveness_counts['Count'].sum() * 100).round(1)
        
        # Create two columns for chart and table
        rcol1, rcol2 = st.columns([3, 2])
        
        with rcol1:
            fig_responsiveness = px.pie(
                responsiveness_counts,
                values='Count',
                names='Responsiveness',
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.RdBu
            )
            
            fig_responsiveness.update_layout(
                height=350,
                margin=dict(l=20, r=20, t=30, b=20),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation='h', yanchor='bottom', y=-0.2, xanchor='center', x=0.5)
            )
            
            fig_responsiveness.update_traces(textinfo='percent+label')
            
            st.plotly_chart(fig_responsiveness, use_container_width=True)
        
        with rcol2:
            # Create a styled HTML table for responsiveness
            html_table = """<table style='width:100%; border-collapse: collapse;'>""" 
            html_table += """<tr style='background-color: #E3F2FD;'>
                <th style='padding: 8px; text-align: left;'>Responsiveness</th>
                <th style='padding: 8px; text-align: right;'>Count</th>
                <th style='padding: 8px; text-align: right;'>%</th>
            </tr>"""
            
            for i, row in responsiveness_counts.iterrows():
                bg_color = '#F5F7FA' if i % 2 == 0 else 'white'
                html_table += f"""<tr style='background-color: {bg_color};'>
                    <td style='padding: 8px; text-align: left;'>{row['Responsiveness']}</td>
                    <td style='padding: 8px; text-align: right;'>{row['Count']}</td>
                    <td style='padding: 8px; text-align: right;'>{row['Percentage']}%</td>
                </tr>"""
            
            html_table += """</table>"""
            st.markdown(html_table, unsafe_allow_html=True)
    
    # st.markdown("</div>", unsafe_allow_html=True)

# Orders table with improved styling
# st.markdown("<div class='card'>", unsafe_allow_html=True)
# st.markdown("<h3 style='text-align: center; color: var(--primary-color);'>Orders List</h3>", unsafe_allow_html=True)

st.markdown("<div class='section-header'>Orders List</div>", unsafe_allow_html=True)

# Add a description for the table
st.markdown("""
<div style='margin-bottom: 15px; padding: 10px; background-color: #F5F7FA; border-radius: 5px;'>
    <span style='color: #555;'>📋 This table shows all orders matching your current filter criteria. Click on column headers to sort the data.</span>
</div>
""", unsafe_allow_html=True)

# Prepare table data
table_data = df_filtered[[
    'orderNumber', 
    'status', 
    'orderCreateTimestamp', 
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
    'orderCompleteTimestamp', 
    'country', 
    'Coordinates', 
    'Minutes', 
    'sqkm'
]].copy()

display_data.columns = [
    'Order ID', 
    'Status', 
    'Create Date', 
    'Complete Date', 
    'Country', 
    'Coordinates', 
    'Minutes', 
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

# Display the table with improved styling
st.dataframe(
    display_data,
    use_container_width=True,
    column_config={
        "Order ID": st.column_config.TextColumn(
            "Order ID",
            help="Unique identifier for each order",
            width="medium"
        ),
        "Status": st.column_config.TextColumn(
            "Status",
            help="Current status of the order",
            width="small"
        ),
        "Create Date": st.column_config.DateColumn(
            "Create Date",
            help="Date when the order was created",
            format="YYYY-MM-DD HH:mm",
            width="medium"
        ),
        "Complete Date": st.column_config.DateColumn(
            "Complete Date",
            help="Date when the order was completed",
            format="YYYY-MM-DD HH:mm",
            width="medium"
        ),
        "Country": st.column_config.TextColumn(
            "Country",
            help="Country where the order is located",
            width="medium"
        ),
        "Coordinates": st.column_config.TextColumn(
            "Coordinates",
            help="Latitude and longitude coordinates",
            width="medium"
        ),
        "Minutes": st.column_config.NumberColumn(
            "Minutes",
            help="Time to complete in minutes",
            format="%.1f",
            width="small"
        ),
        "Area (sqkm)": st.column_config.NumberColumn(
            "Area (sqkm)",
            help="Area covered in square kilometers",
            format="%.2f",
            width="small"
        )
    },
    hide_index=True,
)

# Add download button for the filtered data
csv = display_data.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Download filtered data as CSV",
    data=csv,
    file_name="filtered_orders.csv",
    mime="text/csv",
    help="Download the currently filtered data as a CSV file"
)

st.markdown("</div>", unsafe_allow_html=True)

# # Footer with improved styling
# st.markdown("<div style='margin-top: 30px; padding: 20px; background-color: #F5F7FA; border-radius: 10px; text-align: center;'>", unsafe_allow_html=True)
# st.markdown("""
# <div style='display: flex; justify-content: space-between; align-items: center;'>
#     <div>
#         <h4 style='color: var(--primary-color); margin-bottom: 5px;'>Maxar Satellite Imagery Dashboard</h4>
#         <p style='color: #666; font-size: 0.9em; margin: 0;'>© 2023 Maxar Technologies</p>
#     </div>
#     <div>
#         <p style='color: #666; font-size: 0.9em; margin: 0;'>Last updated: August 2023</p>
#         <p style='color: #666; font-size: 0.9em; margin: 0;'>Dashboard created with Streamlit</p>
#     </div>
# </div>
# """, unsafe_allow_html=True)
# st.markdown("</div>", unsafe_allow_html=True)