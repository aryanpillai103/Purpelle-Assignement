# streamlit_app.py - Deploy this to Streamlit Cloud
import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime


API_URL = "https://purpelle-assignement.onrender.com"  # Change to your Render URL

st.set_page_config(page_title="Apex Retail Analytics", layout="wide", page_icon="🏪")

st.title("🏪 Apex Retail - Live Store Analytics")

# Check API connection
try:
    response = requests.get(f"{API_URL}/health", timeout=10)
    if response.status_code == 200:
        st.success(f"✅ Connected to Analytics API")
    else:
        st.error("⚠️ API is not responding correctly")
        st.stop()
except Exception as e:
    st.error(f"❌ Cannot connect to API at {API_URL}")
    st.info("""
    ### Backend API is deploying...
    Please wait 1-2 minutes for the backend to start.
    
    Once deployed, refresh this page.
    """)
    st.stop()

# Sidebar
st.sidebar.header("Store Settings")
store_id = st.sidebar.selectbox(
    "Select Store",
    ["STORE_BLR_001", "STORE_DEL_001", "STORE_MUM_001"]
)
refresh_rate = st.sidebar.slider("Refresh (seconds)", 3, 15, 5)
st.sidebar.info(f"🖥️ API: {API_URL}")

# Main content
placeholder = st.empty()

def fetch_data():
    """Fetch all data from API"""
    try:
        metrics = requests.get(f"{API_URL}/stores/{store_id}/metrics", timeout=10).json()
        funnel = requests.get(f"{API_URL}/stores/{store_id}/funnel", timeout=10).json()
        anomalies = requests.get(f"{API_URL}/stores/{store_id}/anomalies", timeout=10).json()
        heatmap = requests.get(f"{API_URL}/stores/{store_id}/heatmap", timeout=10).json()
        return metrics, funnel, anomalies, heatmap
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None, None, None, None

# Auto-refresh loop
auto_refresh = st.empty()

while True:
    metrics, funnel, anomalies, heatmap = fetch_data()
    
    if metrics:
        with placeholder.container():
            # Key metrics row
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("👥 Visitors", metrics.get('unique_visitors', 0))
            col2.metric("📈 Conversion", f"{metrics.get('conversion_rate', 0)*100:.1f}%")
            col3.metric("⏱️ Queue", metrics.get('queue_depth', 0))
            col4.metric("💰 Revenue", f"₹{metrics.get('total_revenue', 0):,.0f}")
            col5.metric("📊 Transactions", metrics.get('total_transactions', 0))
            
            # Two columns for charts
            left, right = st.columns(2)
            
            with left:
                st.subheader("📊 Conversion Funnel")
                if funnel and funnel.get('stages'):
                    funnel_df = pd.DataFrame(funnel['stages'])
                    st.bar_chart(funnel_df.set_index('name')['count'])
                else:
                    st.info("No funnel data available")
            
            with right:
                st.subheader("🔥 Zone Heatmap")
                if heatmap and heatmap.get('zones'):
                    heatmap_df = pd.DataFrame(heatmap['zones'])
                    st.dataframe(heatmap_df, use_container_width=True)
                else:
                    st.info("No heatmap data available")
            
            # Anomalies
            if anomalies and anomalies.get('anomalies'):
                st.warning("⚠️ Active Anomalies Detected")
                for a in anomalies['anomalies']:
                    st.write(f"- **{a['type']}**: {a['description']}")
                    st.write(f"  → Suggested Action: {a.get('suggested_action', 'Monitor closely')}")
            
            # Dwell times
            if metrics.get('avg_dwell_by_zone'):
                st.subheader("⏱️ Average Dwell Time by Zone")
                dwell_df = pd.DataFrame(
                    metrics['avg_dwell_by_zone'].items(),
                    columns=['Zone', 'Seconds']
                )
                st.dataframe(dwell_df, use_container_width=True)
    
    auto_refresh.caption(f"🔄 Last updated: {datetime.now().strftime('%H:%M:%S')} | Auto-refresh in {refresh_rate}s")
    time.sleep(refresh_rate)