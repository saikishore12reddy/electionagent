from sqlalchemy import create_engine
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

class DatabaseManager:
    def __init__(self, db_url=None):
        if not db_url:
            db_url = os.getenv("DATABASE_URL", "sqlite:///election_data.db")
        
        # Ensure postgresql:// is used for sqlalchemy if it is postgres://
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
            
        self.engine = create_engine(db_url)
        self.db_url = db_url
        
    def create_table_from_df(self, df, table_name):
        """Create or replace a table from a DataFrame."""
        df.to_sql(table_name, self.engine, if_exists='replace', index=False)
        print(f"Table '{table_name}' created/updated in database with {len(df)} rows.")

    def query(self, sql):
        """Execute a custom SQL query and return a DataFrame."""
        return pd.read_sql_query(sql, self.engine)

# Simple schema definitions for key reports
SCHEMA_MAPPING = {
    "4": "successful_candidates",
    "13": "constituency_stats",
    "17": "party_performance_statewise",
    "18": "party_performance_detailed",
    "20": "national_party_performance",
    "21": "state_party_performance",
    "33": "candidate_detailed_results"
}
