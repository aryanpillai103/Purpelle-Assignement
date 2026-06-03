# streamlit_app.py - Updated for STORE_BLR_002
import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
import os

# ============================================
# LOAD API URL FROM ENVIRONMENT VARIABLE
# ============================================
# For Streamlit Cloud: Set in Secrets Management
# For Local: Use .env file or environment variable

# Try to get from Streamlit secrets first (for cloud)
try:
    API_URL = st.secrets["API_URL"]
except:
    # Fallback to environment variable (for local development)
    API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Apex Retail Analytics", layout="wide", page_icon="🏪")

st.title("🏪 Apex Retail - Live Store Analytics")

# Display API status without exposing URL
with st.expander("ℹ️ System Status", expanded=False):
    st.info(f"Connected to analytics backend")

# Check API connection
try:
    response = requests.get(f"{API_URL}/health", timeout=10)
    if response.status_code == 200:
        health_data = response.json()
        st.success("✅ Connected to Analytics API")
        st.caption(f"📊 Events stored: {health_data.get('events_stored', 0)} | POS: {health_data.get('pos_transactions', 0)}")
    else:
        st.error("⚠️ API is not responding correctly")
        st.stop()
except Exception as e:
    st.error("❌ Cannot connect to analytics backend")
    st.info("""
    ### Backend API is deploying...
    Please wait 1-2 minutes for the backend to start.
    
    Once deployed, refresh this page.
    """)
    st.stop()

# Sidebar
st.sidebar.header("Store Settings")

# UPDATED: Store list now includes STORE_BLR_002 as primary
store_options = {
    "STORE_BLR_002": "🏬 Bangalore (Brigade Road)",
    "STORE_DEL_001": "🏬 Delhi Store",
    "STORE_MUM_001": "🏬 Mumbai Store"
}

selected_store_display = st.sidebar.selectbox(
    "Select Store",
    options=list(store_options.keys()),
    format_func=lambda x: store_options[x],
    index=0  # Default to STORE_BLR_002
)

store_id = selected_store_display

refresh_rate = st.sidebar.slider("Refresh (seconds)", 3, 15, 5)

# Show API info in sidebar
st.sidebar.divider()
st.sidebar.caption(f"🔗 API: {API_URL.replace('https://', '').replace('http://', '')}")

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
        return None, None, None, None

# Auto-refresh loop
auto_refresh = st.empty()

while True:
    metrics, funnel, anomalies, heatmap = fetch_data()
    
    if metrics:
        with placeholder.container():
            # Key metrics row
            col1, col2, col3, col4, col5 = st.columns(5)
            
            # Highlight if data is available
            visitors = metrics.get('unique_visitors', 0)
            conversion = metrics.get('conversion_rate', 0) * 100
            
            col1.metric("👥 Visitors", visitors, 
                        delta=None if visitors > 0 else "⚠️ No data",
                        delta_color="off")
            col2.metric("📈 Conversion", f"{conversion:.1f}%",
                        delta=None if conversion > 0 else "No purchases yet")
            col3.metric("⏱️ Queue", metrics.get('queue_depth', 0))
            col4.metric("💰 Revenue", f"₹{metrics.get('total_revenue', 0):,.0f}")
            col5.metric("📊 Transactions", metrics.get('total_transactions', 0))
            
            # Two columns for charts
            left, right = st.columns(2)
            
            with left:
                st.subheader("📊 Conversion Funnel")
                if funnel and funnel.get('stages'):
                    funnel_df = pd.DataFrame(funnel['stages'])
                    # Ensure no negative drop-offs
                    funnel_df['drop_off'] = funnel_df['drop_off'].clip(lower=0)
                    st.bar_chart(funnel_df.set_index('name')['count'])
                    
                    # Show drop-off percentages
                    if len(funnel_df) > 1:
                        st.caption(f"📉 Drop-off: {funnel_df.iloc[1]['drop_off']} people left before Product Zone")
                else:
                    st.info("No funnel data available")
            
            with right:
                st.subheader("🔥 Zone Heatmap")
                if heatmap and heatmap.get('zones'):
                    heatmap_df = pd.DataFrame(heatmap['zones'])
                    st.dataframe(heatmap_df, use_container_width=True)
                    st.caption(f"📊 Data confidence: {heatmap.get('data_confidence', 'low')}")
                else:
                    st.info("No heatmap data available")
            
            # Anomalies
            if anomalies and anomalies.get('anomalies'):
                st.warning("⚠️ Active Anomalies Detected")
                for a in anomalies['anomalies']:
                    st.write(f"- **{a['type']}**: {a['description']}")
                    if a.get('suggested_action'):
                        st.write(f"  → Suggested Action: {a['suggested_action']}")
            else:
                # Show success message when no anomalies
                if visitors > 0:
                    st.success("✅ No active anomalies - Store operating normally")
            
            # Dwell times
            if metrics.get('avg_dwell_by_zone'):
                st.subheader("⏱️ Average Dwell Time by Zone")
                dwell_df = pd.DataFrame(
                    metrics['avg_dwell_by_zone'].items(),
                    columns=['Zone', 'Seconds']
                )
                # Add visual bar for dwell times
                max_dwell = dwell_df['Seconds'].max() if not dwell_df.empty else 1
                dwell_df['Bar'] = dwell_df['Seconds'].apply(lambda x: "█" * int(x / max_dwell * 30) if max_dwell > 0 else "")
                st.dataframe(dwell_df[['Zone', 'Seconds']], use_container_width=True)
    
    auto_refresh.caption(f"🔄 Last updated: {datetime.now().strftime('%H:%M:%S')} | Auto-refresh in {refresh_rate}s | Store: {store_id}")
    time.sleep(refresh_rate)