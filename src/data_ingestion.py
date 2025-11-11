"""
Data Ingestion Module for Agentic Graph RAG.
Handles AI-powered entity resolution and knowledge graph construction.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import pickle
import time
import re

from langchain_openai import ChatOpenAI
from sentence_transformers import SentenceTransformer
import faiss

from src.config import Config


class EntityResolver:
    """Uses LLM to resolve entity names across different datasets."""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=Config.OPENAI_API_KEY,
            model=Config.OPENAI_MODEL,
            temperature=0
        )
        
    def find_best_match(self, query_name: str, candidate_names: List[str]) -> Optional[str]:
        """
        Uses LLM to find the best matching product name from candidates.
        Returns None if no good match is found.
        """
        if not candidate_names:
            return None
            
        prompt = f"""You are an expert at matching product names in e-commerce systems.

Given a product name from one system, find the best matching product from a list of candidates.

Query Product: "{query_name}"

Candidate Products:
{chr(10).join(f"{i+1}. {name}" for i, name in enumerate(candidate_names))}

Instructions:
- If you find a clear match (same product, possibly with slight name variations), respond with ONLY the exact candidate name.
- If no good match exists (completely different products), respond with exactly: "NO_MATCH"

Your response:"""

        try:
            response = self.llm.invoke(prompt)
            result = response.content.strip()
            
            if result == "NO_MATCH":
                return None
            
            # Return the matched name if it's in our candidates
            if result in candidate_names:
                return result
            
            return None
        except Exception as e:
            print(f"  ⚠ Error matching '{query_name}': {e}")
            return None


class GraphBuilder:
    """Builds the Neo4j knowledge graph from the fused data."""
    
    def __init__(self):
        self.driver = Config.get_neo4j_driver()
    
    def clear_database(self):
        """Clears all existing data from the graph."""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        print("  ✓ Database cleared")
    
    def create_constraints(self):
        """Creates uniqueness constraints for better performance."""
        with self.driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE",
                "CREATE CONSTRAINT brand_name IF NOT EXISTS FOR (b:Brand) REQUIRE b.name IS UNIQUE",
                "CREATE CONSTRAINT category_name IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE"
            ]
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception:
                    pass  # Constraint might already exist
        print("  ✓ Constraints created")
    
    def clean_price(self, price_value) -> float:
        """Clean and convert price string to float."""
        if pd.isna(price_value):
            return 0.0
        
        # Convert to string and clean
        price_str = str(price_value).lower()
        # Remove currency symbols and common separators
        price_str = re.sub(r'[rs₹$€£,\s]', '', price_str)
        
        try:
            return float(price_str)
        except ValueError:
            return 0.0
    
    def ingest_products(self, products_df: pd.DataFrame):
        """Ingests products into the graph."""
        with self.driver.session() as session:
            for _, row in products_df.iterrows():
                # Clean the price
                price = self.clean_price(row['price'])
                
                query = """
                MERGE (p:Product {id: $product_id})
                SET p.name = $name, p.price = $price
                
                MERGE (b:Brand {name: $brand})
                MERGE (p)-[:MANUFACTURED_BY]->(b)
                
                MERGE (c:Category {name: $category})
                MERGE (p)-[:BELONGS_TO]->(c)
                """
                session.run(query, 
                           product_id=row['product_id'],
                           name=row['product_name'],
                           price=price,
                           brand=row['brand'],
                           category=row['category'])
        
        print(f"  ✓ Ingested {len(products_df)} products into graph")
    
    def ingest_reviews(self, reviews_mapping: List[Dict]):
        """Ingests reviews and links them to products."""
        with self.driver.session() as session:
            for item in reviews_mapping:
                if item['matched_product_id']:
                    query = """
                    MATCH (p:Product {id: $product_id})
                    CREATE (r:Review {
                        id: $review_id,
                        rating: $rating,
                        text: $text
                    })
                    CREATE (p)-[:HAS_REVIEW]->(r)
                    """
                    session.run(query,
                               product_id=item['matched_product_id'],
                               review_id=item['review_id'],
                               rating=float(item['rating']),
                               text=item['text'])
        
        matched_count = sum(1 for item in reviews_mapping if item['matched_product_id'])
        print(f"  ✓ Ingested {matched_count}/{len(reviews_mapping)} reviews into graph")
    
    def ingest_specs(self, specs_mapping: List[Dict]):
        """Ingests technical specifications and links them to products."""
        with self.driver.session() as session:
            for item in specs_mapping:
                if item['matched_product_id']:
                    query = """
                    MATCH (p:Product {id: $product_id})
                    SET p[$spec_name] = $spec_value
                    """
                    session.run(query,
                               product_id=item['matched_product_id'],
                               spec_name=item['spec_name'],
                               spec_value=item['spec_value'])
        
        matched_count = sum(1 for item in specs_mapping if item['matched_product_id'])
        print(f"  ✓ Ingested {matched_count}/{len(specs_mapping)} specs into graph")
    
    def close(self):
        """Closes the Neo4j connection."""
        self.driver.close()


class VectorIndexBuilder:
    """Builds FAISS vector index for semantic search on reviews."""
    
    def __init__(self):
        print("  Loading embedding model...")
        self.model = SentenceTransformer(Config.EMBEDDING_MODEL_NAME)
    
    def build_index(self, reviews_mapping: List[Dict]):
        """Creates FAISS index from review texts."""
        # Filter only matched reviews
        valid_reviews = [r for r in reviews_mapping if r['matched_product_id']]
        
        if not valid_reviews:
            print("  ⚠ No valid reviews to index")
            return
        
        # Generate embeddings
        print(f"  Generating embeddings for {len(valid_reviews)} reviews...")
        texts = [r['text'] for r in valid_reviews]
        embeddings = self.model.encode(texts, show_progress_bar=True)
        
        # Create FAISS index
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings.astype('float32'))
        
        # Save index
        faiss.write_index(index, Config.FAISS_INDEX_PATH)
        
        # Save metadata
        metadata = [
            {
                'review_id': r['review_id'],
                'product_id': r['matched_product_id'],
                'text': r['text'],
                'rating': r['rating']
            }
            for r in valid_reviews
        ]
        
        with open(Config.FAISS_METADATA_PATH, 'wb') as f:
            pickle.dump(metadata, f)
        
        print(f"  ✓ Built FAISS index with {len(valid_reviews)} reviews")
        print(f"  ✓ Saved to {Config.FAISS_INDEX_PATH}")


def run_ingestion():
    """Main ingestion pipeline."""
    print("\n" + "="*70)
    print("  AGENTIC GRAPH RAG - DATA INGESTION PIPELINE")
    print("="*70 + "\n")
    
    # Validate configuration
    Config.validate_config()
    
    # Load CSVs
    print("\n[1/6] Loading CSV files...")
    products_df = pd.read_csv(Config.PRODUCTS_CSV)
    reviews_df = pd.read_csv(Config.REVIEWS_CSV)
    specs_df = pd.read_csv(Config.SPECS_CSV)
    print(f"  • Products: {len(products_df)}")
    print(f"  • Reviews: {len(reviews_df)}")
    print(f"  • Specs: {len(specs_df)}")
    
    # Initialize components
    print("\n[2/6] Initializing AI components...")
    resolver = EntityResolver()
    graph_builder = GraphBuilder()
    vector_builder = VectorIndexBuilder()
    
    # Clear and prepare database
    print("\n[3/6] Preparing Neo4j database...")
    graph_builder.clear_database()
    graph_builder.create_constraints()
    
    # Ingest products
    print("\n[4/6] Ingesting products into knowledge graph...")
    graph_builder.ingest_products(products_df)
    
    # Resolve and ingest reviews
    print("\n[5/6] Resolving and ingesting reviews (AI-powered matching)...")
    product_names = products_df['product_name'].tolist()
    product_id_map = dict(zip(products_df['product_name'], products_df['product_id']))
    
    reviews_mapping = []
    for idx, row in reviews_df.iterrows():
        matched_name = resolver.find_best_match(row['product_name'], product_names)
        matched_id = product_id_map.get(matched_name) if matched_name else None
        
        reviews_mapping.append({
            'review_id': row['review_id'],
            'original_name': row['product_name'],
            'matched_name': matched_name,
            'matched_product_id': matched_id,
            'rating': row['user_rating'],
            'text': row['review_text']
        })
        
        if (idx + 1) % 10 == 0:
            print(f"    Processed {idx + 1}/{len(reviews_df)} reviews...")
        time.sleep(0.1)  # Rate limiting
    
    graph_builder.ingest_reviews(reviews_mapping)
    
    # Resolve and ingest specs
    print("\n[6/6] Resolving and ingesting specifications...")
    specs_mapping = []
    for idx, row in specs_df.iterrows():
        matched_name = resolver.find_best_match(row['product_name'], product_names)
        matched_id = product_id_map.get(matched_name) if matched_name else None
        
        specs_mapping.append({
            'spec_id': row['spec_id'],
            'original_name': row['product_name'],
            'matched_name': matched_name,
            'matched_product_id': matched_id,
            'spec_name': row['spec_name'],
            'spec_value': row['spec_value']
        })
        
        if (idx + 1) % 20 == 0:
            print(f"    Processed {idx + 1}/{len(specs_df)} specs...")
        time.sleep(0.1)  # Rate limiting
    
    graph_builder.ingest_specs(specs_mapping)
    
    # Build vector index
    print("\n[7/7] Building FAISS vector index for semantic search...")
    vector_builder.build_index(reviews_mapping)
    
    # Cleanup
    graph_builder.close()
    
    print("\n" + "="*70)
    print("  ✓ DATA INGESTION COMPLETE!")
    print("="*70)
    print(f"\n  📊 Summary:")
    print(f"     • Products in graph: {len(products_df)}")
    print(f"     • Reviews matched: {sum(1 for r in reviews_mapping if r['matched_product_id'])}/{len(reviews_df)}")
    print(f"     • Specs matched: {sum(1 for s in specs_mapping if s['matched_product_id'])}/{len(specs_df)}")
    print(f"\n  🚀 Ready for Phase 3: Building the Agentic Core!\n")


if __name__ == "__main__":
    run_ingestion()
