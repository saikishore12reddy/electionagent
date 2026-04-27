from preprocessor import ECIPreprocessor
from database_manager import DatabaseManager
import pandas as pd
import numpy as np
import os

SCHEMA_MAPPING = {
    "4": "successful_candidates",
    "13": "constituency_stats",
    "17": "party_performance_statewise",
    "20": "national_party_performance",
    "21": "state_party_performance",
    "33": "candidate_detailed_results"
}

def clean_df_columns(df, expected_cols):
    """Maps the raw dataframe to the exact expected schema structure."""
    if len(df.columns) < len(expected_cols):
        # Pad with NaNs if the report is missing columns
        for i in range(len(df.columns), len(expected_cols)):
            df[f'temp_{i}'] = np.nan
    
    # Take only the number of columns we expect
    df = df.iloc[:, :len(expected_cols)].copy()
    df.columns = expected_cols
    return df

def run_ingestion(data_dir="data"):
    prep = ECIPreprocessor(data_dir=data_dir)
    db = DatabaseManager()
    
    # The strictly defined schemas from the Implementation Plan
    schemas = {
        "4": [
            "serial_no", "state_name", "const_no", "constituency_name", "constituency_type", 
            "total_valid_votes", "winner_name", "winner_category", "winner_gender", 
            "winner_party", "winner_symbol", "winner_votes", "runner_up_name", 
            "runner_up_category", "runner_up_gender", "runner_up_party", 
            "runner_up_symbol", "runner_up_votes", "margin_votes", "margin_pct"
        ],
        "13": [
            "state_name", "pc_no", "constituency_name", "total_polling_stations", 
            "male_electors", "female_electors", "tg_electors", "total_electors", "service_electors",
            "male_voters", "female_voters", "tg_voters", "total_general_voters", "nri_voters",
            "postal_voters", "total_voters", "voter_turnout_pct", 
            "male_turnout_pct", "female_turnout_pct", "tg_turnout_pct"
        ],
        "17": [
            "state_name", "serial", "party_name", "total_valid_votes_state", "total_electors",
            "seats_won", "total_valid_votes_polled", "vote_share_pct"
        ],
        "20": [
            "serial_no", "party_name", "seats_contested", "seats_won", "forfeited_deposits",
            "total_votes_secured", "vote_share_pct_overall", "vote_share_pct_valid"
        ],
        "21": [
            "serial_no_1", "serial_no", "party_abbr", "party_name", "state_name", 
            "seats_contested", "seats_won", "forfeited_deposits", "total_electors", 
            "total_votes_polled", "total_valid_votes", "total_votes_secured", 
            "vote_share_pct_state", "vote_share_pct_valid"
        ],
        "33": [
            "state_name", "constituency_name", "candidate_name", "gender", "age",
            "social_category", "party_name", "party_symbol", "total_const_votes", "valid_votes",
            "general_votes", "postal_votes", "total_votes", "vote_pct_electors", 
            "vote_share_pct", "vote_pct_valid", "total_electors_const"
        ],
        "9": [
            "serial_no", "state_name", 
            "general_voters_male", "general_voters_female", "general_voters_tg", "general_voters_total",
            "service_voters_male", "service_voters_female", "service_voters_total",
            "grand_total_male", "grand_total_female", "grand_total_tg", "total_electors",
            "nri_voters_male", "nri_voters_female", "nri_voters_tg", "nri_voters_total"
        ]
    }
    
    # Ingest the strictly mapped schemas
    for report_num, expected_cols in schemas.items():
        print(f"Processing Report {report_num} ({SCHEMA_MAPPING.get(report_num, f'report_{report_num}')})...")
        df = prep.standardize_report(report_num)
        
        if df is not None and not df.empty:
            df = clean_df_columns(df, expected_cols)
            table_name = SCHEMA_MAPPING.get(report_num, f"report_{report_num}")
            db.create_table_from_df(df, table_name)
            print(f"✅ Ingested {table_name} successfully.")
        else:
            print(f"❌ Failed to process Report {report_num}.")
            
    # Also ingest a few others dynamically just in case they are needed for vector context
    dynamic_reports = ["10", "11", "12", "18", "22", "23", "24", "25", "26", "32"]
    for report_num in dynamic_reports:
        print(f"Processing Report {report_num} (Dynamic Mapping)...")
        df = prep.standardize_report(report_num)
        if df is not None and not df.empty:
            clean_cols = []
            for i, c in enumerate(df.columns):
                name = str(c).replace(' ', '_').replace('(', '').replace(')', '').replace('%', 'pct').strip('_')
                if not name: name = f"column_{i}"
                clean_cols.append(name.lower())
                
            seen = {}
            unique_cols = []
            for col in clean_cols:
                if col in seen:
                    seen[col] += 1
                    unique_cols.append(f"{col}_{seen[col]}")
                else:
                    seen[col] = 0
                    unique_cols.append(col)
                    
            df.columns = unique_cols
            db.create_table_from_df(df, f"report_{report_num}")

if __name__ == "__main__":
    run_ingestion()
