"""
Configuration module for Agentic Graph RAG E-Commerce System.
Fully compatible with Streamlit Cloud deployment.
"""

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables for local development
load_dotenv()

def get_secret(key: str, default=None):
    """Get secret from Streamlit secrets or environment variables."""
    try:
        import streamlit as st
        # Only try to access secrets if we're actually running in Streamlit
        if hasattr(st, 'secrets'):
            try:
                if key in st.secrets:
                    return st.secrets[key]
            except Exception:
                # If secrets aren't available, fall through to env vars
                pass
    except (ImportError, Exception):
        # Streamlit not available or not running, use env vars
        pass
    
    return os.getenv(key, default)


class Config:
    """Central configuration for the application."""
    
    # OpenAI Configuration
    OPENAI_API_KEY = get_secret("OPENAI_API_KEY")
    OPENAI_MODEL = "gpt-3.5-turbo"
    
    # Neo4j AuraDB Configuration
    NEO4J_URI = get_secret("NEO4J_URI")
    NEO4J_USERNAME = get_secret("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD = get_secret("NEO4J_PASSWORD")
    
    # Turso Configuration
    TURSO_DATABASE_URL = get_secret("TURSO_DATABASE_URL")
    TURSO_AUTH_TOKEN = get_secret("TURSO_AUTH_TOKEN")
    
    # Embedding Model Configuration
    EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
    
    # File Paths
    DATA_DIR = "data"
    PRODUCTS_CSV = os.path.join(DATA_DIR, "products.csv")
    REVIEWS_CSV = os.path.join(DATA_DIR, "reviews.csv")
    SPECS_CSV = os.path.join(DATA_DIR, "specs.csv")
    
    # FAISS Index Paths
    FAISS_INDEX_PATH = os.path.join(DATA_DIR, "faiss_index.bin")
    FAISS_METADATA_PATH = os.path.join(DATA_DIR, "faiss_metadata.pkl")

    # Firebase paths
    FIREBASE_URL = get_secret("FIREBASE_URL")
    FIREBASE_SERVICE_ACCOUNT_JSON = get_secret("FIREBASE_SERVICE_ACCOUNT_JSON")
    
    @staticmethod
    def get_neo4j_driver():
        """Returns a Neo4j driver instance."""
        return GraphDatabase.driver(
            Config.NEO4J_URI,
            auth=(Config.NEO4J_USERNAME, Config.NEO4J_PASSWORD)
        )
    
    @staticmethod
    def validate_config():
        """Validates that all required configuration is present."""
        errors = []
        
        if not Config.OPENAI_API_KEY:
            errors.append("❌ OPENAI_API_KEY not found")
        if not Config.NEO4J_URI:
            errors.append("❌ NEO4J_URI not found")
        if not Config.NEO4J_PASSWORD:
            errors.append("❌ NEO4J_PASSWORD not found")
        if not Config.TURSO_DATABASE_URL:
            errors.append("❌ TURSO_DATABASE_URL not found")
        if not Config.TURSO_AUTH_TOKEN:
            errors.append("❌ TURSO_AUTH_TOKEN not found")
            
        if errors:
            print("\n" + "\n".join(errors))
            raise ValueError("Configuration incomplete. Check your .env file.")
        
        print("✓ Configuration validated successfully")
        print(f"  • Neo4j: {Config.NEO4J_URI}")
        print(f"  • Turso: {Config.TURSO_DATABASE_URL}")
        print(f"  • OpenAI Model: {Config.OPENAI_MODEL}")


if __name__ == "__main__":
    Config.validate_config()
