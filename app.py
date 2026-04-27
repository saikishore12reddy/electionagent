import streamlit as st
import pandas as pd
import os
import json
import time
from datetime import datetime
from downloader import ECIDownloader
from preprocessor import ECIPreprocessor
from agent_engine import ElectoralAnalysisAgent
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION & STYLING ---
st.set_page_config(
    page_title="Electoral Insight AI | 2024 Lok Sabha",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Look
st.markdown("""
<style>
    :root {
        --primary: #6366f1;
        --secondary: #ec4899;
        --bg: #0f172a;
        --text: #f8fafc;
        --accent: #10b981;
    }
    
    .stApp {
        background: radial-gradient(circle at top left, #1e1b4b, #0f172a);
        color: var(--text);
    }
    
    [data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.8);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .stButton>button {
        background: linear-gradient(90deg, var(--primary), var(--secondary));
        color: white !important;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
    }
    
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(12px);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    
    h1, h2, h3 {
        color: #fff !important;
        font-family: 'Inter', sans-serif;
    }
    
    .status-badge {
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    .status-ok { background: rgba(16, 185, 129, 0.2); color: #10b981; }
    .status-missing { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'agent' not in st.session_state:
    st.session_state.agent = ElectoralAnalysisAgent()
if 'download_progress' not in st.session_state:
    st.session_state.download_progress = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# --- COMPONENTS ---
def sidebar_status():
    with st.sidebar:
        st.title("🛰️ System Status")
        data_dir = "data"
        reports = [f"Report_{n}.xlsx" for n in ["4", "9", "10", "11", "12", "13", "17", "18", "20", "21", "22", "23", "24", "25", "26", "32", "33"]]
        
        found_count = 0
        if os.path.exists(data_dir):
            for r in reports:
                if os.path.exists(os.path.join(data_dir, r)):
                    found_count += 1
        
        status_color = "status-ok" if found_count == len(reports) else "status-missing"
        status_text = "READY" if found_count == len(reports) else f"{found_count}/{len(reports)} Reports"
        
        st.markdown(f"**Data Coverage:** <span class='status-badge {status_color}'>{status_text}</span>", unsafe_allow_html=True)
        st.divider()
        
        if st.button("🚀 Run Downloader"):
            downloader = ECIDownloader()
            with st.status("Downloading ECI Reports...", expanded=True) as status:
                st.write("Initializing Playwright...")
                # We can't easily stream the stdout of downloader.py here without refactoring 
                # but we can add st.write messages after batches
                try:
                    # Clear data dir first to avoid stale files
                    import shutil
                    if os.path.exists("data"):
                        shutil.rmtree("data")
                    os.makedirs("data")
                    
                    st.write("📡 Connecting to ECI Portal...")
                    downloader.download_reports()
                    
                    st.write("⚙️ Processing & Ingesting into SQL Database...")
                    from ingestor import run_ingestion
                    run_ingestion()
                    
                    st.write("📊 Data ingested successfully.")
                    status.update(label="System Ready!", state="complete", expanded=False)
                except Exception as e:
                    st.error(f"Error during setup: {e}")
                    status.update(label="Setup Failed", state="error")
            st.rerun()

# --- MAIN CONTENT ---
st.title("🗳️ Electoral Insight AI")
st.markdown("### Agentic Analysis of Lok Sabha 2024 Statistical Reports")

# Tabs for different functions
tab_agent, tab_explorer, tab_sql, tab_setup = st.tabs(["🤖 AI Analyst", "🔍 Data Explorer", "💾 SQL Query", "⚙️ Setup"])

with tab_agent:
    st.info("Ask complex quantitative questions like: 'Which party had the highest victory margin in Uttar Pradesh?' or 'Calculate average turnout by state.'")
    
    # Chat display
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    # Chat input
    if prompt := st.chat_input("Enter your research query..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        with st.chat_message("assistant"):
            with st.spinner("Analyzing cross-document data..."):
                try:
                    response = st.session_state.agent.query(prompt)
                    st.markdown(response.response)
                    
                    # Show sub-questions in an expander
                    if hasattr(response, 'source_nodes'):
                        with st.expander("Show Data Chain"):
                            for i, sub in enumerate(response.source_nodes):
                                st.caption(f"Ref {i+1}: {sub.node.metadata.get('report_id', 'Unknown')}")
                    
                    st.session_state.chat_history.append({"role": "assistant", "content": response.response})
                except Exception as e:
                    st.error(f"Analysis failed: {e}")

with tab_explorer:
    col1, col2 = st.columns([1, 3])
    with col1:
        st.subheader("Reports")
        selected_report = st.selectbox("Select Report", ["4", "9", "32", "33"])
    
    with col2:
        path = f"processed/Report_{selected_report}.csv"
        if os.path.exists(path):
            df = pd.read_csv(path)
            st.dataframe(df.head(200))
            st.download_button("Download CSV", df.to_csv(), f"Report_{selected_report}.csv")
        else:
            st.warning(f"Report {selected_report} not found. Please run the setup.")

with tab_sql:
    st.subheader("Direct SQL Access")
    st.write("Query the structural database directly. Available tables: `successful_candidates`, `constituency_stats`, `party_performance_statewise`, `candidate_detailed_results` etc.")
    
    query = st.text_area("Enter SQL Query", "SELECT * FROM successful_candidates LIMIT 10")
    if st.button("Execute Query"):
        from database_manager import DatabaseManager
        db = DatabaseManager()
        try:
            res_df = db.query(query)
            st.dataframe(res_df)
        except Exception as e:
            st.error(f"SQL Error: {e}")

with tab_setup:
    st.markdown("#### System Configuration")
    st.write("This application uses **Llama-3 (70B)** via **Groq** for reasoning and **Pandas** for structured extraction.")
    st.divider()
    if st.button("Reset Storage Context"):
        import shutil
        if os.path.exists("storage"):
            shutil.rmtree("storage")
        st.success("Vector store cleared. Restart app to re-index.")

# Call sidebar
sidebar_status()
