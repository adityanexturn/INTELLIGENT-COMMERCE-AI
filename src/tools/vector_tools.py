"""
Vector Tools: FAISS semantic search tools for reviews (ENHANCED).
Used by Review Agent with improved similarity scoring.
"""

from typing import List, Dict, Optional
import pickle
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from src.config import Config

class VectorTools:
    """Enhanced tools for semantic search on product reviews using FAISS."""
    
    def __init__(self):
        # Load FAISS index
        self.index = faiss.read_index(Config.FAISS_INDEX_PATH)
        
        # Load metadata
        with open(Config.FAISS_METADATA_PATH, 'rb') as f:
            self.metadata = pickle.load(f)
        
        # Load embedding model
        self.model = SentenceTransformer(Config.EMBEDDING_MODEL_NAME)
    
    def search_reviews_semantic(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Semantic search on reviews based on natural language query.
        
        Args:
            query: Natural language query (e.g., "good battery life")
            top_k: Number of results to return
        
        Returns:
            List of dicts with product_id, review_text, rating, and similarity score
        """
        # Generate query embedding
        query_embedding = self.model.encode([query])[0]
        
        # Search FAISS index
        distances, indices = self.index.search(
            np.array([query_embedding]).astype('float32'), 
            top_k
        )
        
        # Compile results
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx < len(self.metadata):
                result = self.metadata[idx].copy()
                # Convert distance to similarity score (0-1 range)
                result['similarity_score'] = float(1 / (1 + distance))
                results.append(result)
        
        return results
    
    def get_product_reviews(self, product_id: str) -> List[Dict]:
        """Get all reviews for a specific product."""
        return [
            review for review in self.metadata 
            if review['product_id'] == product_id
        ]
    
    def get_reviews_by_rating(self, min_rating: float = 4.0, 
                             max_rating: float = 5.0, 
                             limit: int = 10) -> List[Dict]:
        """Get reviews within a rating range."""
        filtered = [
            review for review in self.metadata
            if min_rating <= review['rating'] <= max_rating
        ]
        return filtered[:limit]
    
    def search_products_by_review_content(self, query: str, 
                                         min_similarity: float = 0.5,
                                         top_k: int = 10) -> List[str]:
        """
        Find product IDs that have reviews matching the query.
        
        Args:
            query: What to search for in reviews (e.g., "fast performance")
            min_similarity: Minimum similarity threshold
            top_k: Max results
        
        Returns:
            List of unique product IDs ranked by relevance
        """
        results = self.search_reviews_semantic(query, top_k=top_k * 2)
        
        # Filter by similarity and get unique product IDs
        product_ids = []
        seen = set()
        
        for result in results:
            if result['similarity_score'] >= min_similarity:
                prod_id = result['product_id']
                if prod_id not in seen:
                    product_ids.append(prod_id)
                    seen.add(prod_id)
                
                if len(product_ids) >= top_k:
                    break
        
        return product_ids
    
    def get_product_sentiment_summary(self, product_id: str) -> Dict:
        """Get sentiment summary for a product based on its reviews."""
        reviews = self.get_product_reviews(product_id)
        
        if not reviews:
            return {
                'product_id': product_id,
                'review_count': 0,
                'average_rating': 0.0,
                'reviews': []
            }
        
        ratings = [r['rating'] for r in reviews]
        
        return {
            'product_id': product_id,
            'review_count': len(reviews),
            'average_rating': sum(ratings) / len(ratings),
            'min_rating': min(ratings),
            'max_rating': max(ratings),
            'reviews': reviews
        }
    
    def get_top_rated_products(self, category: Optional[str] = None,
                              min_reviews: int = 1,
                              limit: int = 10) -> List[Dict]:
        """
        Get top-rated products based on average review ratings.
        
        Args:
            category: Optional category filter
            min_reviews: Minimum number of reviews required
            limit: Max results
        
        Returns:
            List of products with their ratings
        """
        # Group reviews by product
        product_ratings = {}
        for review in self.metadata:
            pid = review['product_id']
            if pid not in product_ratings:
                product_ratings[pid] = []
            product_ratings[pid].append(review['rating'])
        
        # Calculate averages
        product_scores = []
        for pid, ratings in product_ratings.items():
            if len(ratings) >= min_reviews:
                avg_rating = sum(ratings) / len(ratings)
                product_scores.append({
                    'product_id': pid,
                    'average_rating': avg_rating,
                    'review_count': len(ratings)
                })
        
        # Sort by average rating
        product_scores.sort(key=lambda x: x['average_rating'], reverse=True)
        
        return product_scores[:limit]
    
    def analyze_review_sentiment(self, product_id: str) -> Dict:
        """
        Analyze sentiment distribution for a product's reviews.
        
        Returns:
            Dict with sentiment breakdown
        """
        reviews = self.get_product_reviews(product_id)
        
        if not reviews:
            return {
                'positive': 0,
                'neutral': 0,
                'negative': 0,
                'total': 0
            }
        
        positive = sum(1 for r in reviews if r['rating'] >= 4)
        negative = sum(1 for r in reviews if r['rating'] <= 2)
        neutral = len(reviews) - positive - negative
        
        return {
            'positive': positive,
            'neutral': neutral,
            'negative': negative,
            'total': len(reviews),
            'positive_percentage': (positive / len(reviews)) * 100,
            'negative_percentage': (negative / len(reviews)) * 100
        }

# Singleton instance
_vector_tools_instance = None

def get_vector_tools() -> VectorTools:
    """Get or create the VectorTools singleton instance."""
    global _vector_tools_instance
    if _vector_tools_instance is None:
        _vector_tools_instance = VectorTools()
    return _vector_tools_instance
