# dashboard/web_dashboard.py - Web-based dashboard

import streamlit as st
import requests
import pandas as pd
import time

API_URL = "http://127.0.0.1:8000"
STORES = ["STORE_BLR_001", "STORE_DEL_001", "STORE_MUM_001"]

st.set_page_config(page_title="Apex Retail Analytics", layout="wide")
st.title("🛍️ Apex Retail - Live Store Analytics")

# Sidebar
st.sidebar.header("Settings")
selected_store = st.sidebar.selectbox("Select Store", STORES)
refresh_rate = st.sidebar.slider("Refresh (seconds)", 2, 10, 5)

# Auto-refresh
placeholder = st.empty()

while True:
    try:
        # Fetch metrics
        metrics = requests.get(f"{API_URL}/stores/{selected_store}/metrics").json()
        funnel = requests.get(f"{API_URL}/stores/{selected_store}/funnel").json()
        anomalies = requests.get(f"{API_URL}/stores/{selected_store}/anomalies").json()
        
        with placeholder.container():
            # Metrics row
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("👥 Visitors", metrics.get('unique_visitors', 0))
            col2.metric("📈 Conversion Rate", f"{metrics.get('conversion_rate', 0)*100:.1f}%")
            col3.metric("⏱️ Queue Depth", metrics.get('queue_depth', 0))
            col4.metric("💰 Revenue", f"₹{metrics.get('total_revenue', 0):,.0f}")
            
            # Funnel chart
            st.subheader("📊 Conversion Funnel")
            funnel_df = pd.DataFrame(funnel.get('stages', []))
            if not funnel_df.empty:
                st.bar_chart(funnel_df.set_index('name')['count'])
            
            # Anomalies
            if anomalies.get('anomalies'):
                st.warning("⚠️ Active Anomalies")
                for a in anomalies['anomalies']:
                    st.write(f"- **{a['type']}**: {a['description']}")
            
            st.caption(f"Last updated: {time.strftime('%H:%M:%S')}")
        
        time.sleep(refresh_rate)
        
    except Exception as e:
        st.error(f"Error connecting to API: {e}")
        st.info("Make sure API is running: python api/main.py")
        time.sleep(5)