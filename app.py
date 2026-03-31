import streamlit as st
import pandas as pd
from scraper import scrape_google_maps
import base64

# Page Config
st.set_page_config(page_title="AI Lead Gen Pro - GMap Scraper", page_icon="📍", layout="wide")

# Custom CSS for Professional Look
st.markdown("""
    <style>
    .main {background-color: #f8f9fa;}
    h1 {color: #2c3e50;}
    .stButton>button {background-color: #2980b9; color: white; border-radius: 5px;}
    </style>
    """, unsafe_allow_html=True)

st.title("📍 AI Lead Gen Pro - Google Maps Scraper")
st.markdown("Scrape business leads directly from Google Maps with advanced filtering.")

# Sidebar for Inputs
with st.sidebar:
    st.header("🔍 Search Parameters")
    niche = st.text_input("Business Niche", placeholder="e.g., Plumbers, Real Estate")
    location = st.text_input("Location", placeholder="e.g., New York, Dhaka")
    max_results = st.slider("Max Results to Scrape", min_value=5, max_value=100, value=20)
    
    start_scraping = st.button("🚀 Start Scraping")

# Session state to store data
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()

# Scraping Logic
if start_scraping:
    if niche and location:
        with st.spinner(f'Scraping {niche} in {location}... Please wait.'):
            try:
                df = scrape_google_maps(niche, location, max_results)
                st.session_state.df = df
                st.success("✅ Scraping Completed Successfully!")
            except Exception as e:
                st.error(f"An error occurred: {e}")
    else:
        st.warning("⚠️ Please enter both Niche and Location.")

# Advanced Filtering & Display
if not st.session_state.df.empty:
    st.divider()
    st.header("🎛️ Advanced Filters")
    
    df = st.session_state.df
    
    # Filter Layout
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        min_rating = st.slider("Minimum Rating ⭐", 0.0, 5.0, 0.0, 0.1)
    with col2:
        min_reviews = st.number_input("Minimum Reviews 📝", min_value=0, value=0)
    with col3:
        has_website = st.checkbox("Must have Website 🌐")
    with col4:
        has_phone = st.checkbox("Must have Phone 📞")

    # Apply Filters
    filtered_df = df[
        (df['Rating'] >= min_rating) & 
        (df['Reviews'] >= min_reviews)
    ]
    
    if has_website:
        filtered_df = filtered_df[filtered_df['Website'] != "N/A"]
    if has_phone:
        filtered_df = filtered_df[filtered_df['Phone'] != "N/A"]

    # Display Data
    st.subheader(f"📊 Filtered Results: {len(filtered_df)} Businesses Found")
    st.dataframe(filtered_df, use_container_width=True)

    # Download Button
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Data as CSV",
        data=csv,
        file_name=f'{niche}_{location}_leads.csv',
        mime='text/csv',
    )
