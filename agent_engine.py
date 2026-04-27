import os
from llama_index.llms.groq import Groq
from llama_index.core import (
    VectorStoreIndex, 
    StorageContext, 
    load_index_from_storage, 
    Document,
    Settings
)
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.query_engine import SubQuestionQueryEngine, RouterQueryEngine
from llama_index.core.indices.struct_store import NLSQLTableQueryEngine
from llama_index.core import SQLDatabase
from sqlalchemy import create_engine, inspect
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

class ElectoralAnalysisAgent:
    def __init__(self, processed_dir="processed", persist_dir="storage"):
        self.processed_dir = processed_dir
        self.persist_dir = persist_dir
        
        # Configure LLM (Llama-3 via Groq as requested)
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment.")
            
        self.llm = Groq(model="llama-3.3-70b-versatile", api_key=api_key)
        Settings.llm = self.llm
        Settings.embed_model = "local:BAAI/bge-small-en-v1.5" # Defaulting to a local embedding model for speed/cost
        
        self.engine = None
        self.categories = {
            "Demographics": ["9", "10", "11", "12", "13"],
            "Performance": ["4", "17", "18", "20", "21", "22"],
            "Gender": ["23", "24", "25", "26"],
            "Granular": ["32", "33"]
        }

    def _load_data_as_docs(self, category):
        docs = []
        report_nums = self.categories.get(category, [])
        for num in report_nums:
            path = os.path.join(self.processed_dir, f"Report_{num}.csv")
            if os.path.exists(path):
                df = pd.read_csv(path)
                # Convert first 100 rows to MD for the document content (to avoid token overflow while keeping tabular structure)
                md_content = df.head(100).to_markdown(index=False)
                docs.append(Document(
                    text=md_content,
                    metadata={"report_id": num, "category": category}
                ))
        return docs

    def build_agent(self):
        query_engine_tools = []
        
        # 1. SQL Database Engine (Structured Data)
        try:
            db_url = os.getenv("DATABASE_URL", "sqlite:///election_data.db")
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql://", 1)
            
            db_engine = create_engine(db_url)
            sql_database = SQLDatabase(db_engine)
            sql_query_engine = NLSQLTableQueryEngine(
                sql_database=sql_database,
                llm=self.llm
            )
            query_engine_tools.append(
                QueryEngineTool(
                    query_engine=sql_query_engine,
                    metadata=ToolMetadata(
                        name="sql_analytics_tool",
                        description=(
                            "BEST for quantitative questions, aggregations, counts, winners, margins, and comparisons. "
                            "CRITICAL TABLE CONTEXT: "
                            "1. `successful_candidates`: Tracks exactly 1 winner per constituency (Total 543 rows). Use this to count constituencies per state (e.g. COUNT(constituency_name)). "
                            "   * IMPORTANT: To find SC or ST seats, you MUST count rows in `successful_candidates` where `constituency_type` = 'SC' or 'ST'. Do NOT use summary tables for this. "
                            "   * Columns: `state_name`, `constituency_name`, `constituency_type`, `winner_name`, `winner_party`, `winner_gender`, `margin_votes`. "
                            "2. `candidate_detailed_results`: Contains every CANDIDATE that ran. Do NOT count rows here to find constituencies, it will return the number of candidates (e.g., 1169 in Maharashtra). "
                            "3. `constituency_stats`: Demographic data per constituency."
                        )
                    )
                )
            )
        except Exception as e:
            print(f"SQL Engine setup failed: {e}")

        # 2. Vector Stores (Qualitative/Report Context)
        for category in self.categories:
            category_persist = os.path.join(self.persist_dir, category)
            
            if os.path.exists(category_persist):
                storage_context = StorageContext.from_defaults(persist_dir=category_persist)
                index = load_index_from_storage(storage_context)
            else:
                docs = self._load_data_as_docs(category)
                if not docs:
                    continue
                index = VectorStoreIndex.from_documents(docs)
                index.storage_context.persist(persist_dir=category_persist)
            
            engine = index.as_query_engine(similarity_top_k=3)
            query_engine_tools.append(
                QueryEngineTool(
                    query_engine=engine,
                    metadata=ToolMetadata(
                        name=f"{category}_vector_tool",
                        description=f"Good for qualitative details and descriptive report content related to {category}."
                    )
                )
            )
            
        if not query_engine_tools:
            return "No report data found. Please run the downloader first."

        # Create Sub-Question Query Engine for multi-document joins
        from llama_index.core.question_gen import LLMQuestionGenerator
        question_gen = LLMQuestionGenerator.from_defaults(llm=self.llm)
        self.engine = SubQuestionQueryEngine.from_defaults(
            query_engine_tools=query_engine_tools,
            llm=self.llm,
            question_gen=question_gen,
            verbose=True
        )
        return "Agent ready with SQL and Vector capabilities."

    def query(self, question):
        if not self.engine:
            status = self.build_agent()
            if self.engine is None:
                return status
        
        response = self.engine.query(question)
        return response

if __name__ == "__main__":
    agent = ElectoralAnalysisAgent()
    # agent.build_agent()
