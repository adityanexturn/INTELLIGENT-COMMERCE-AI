"""
Review Agent: Review sentiment specialist (REDESIGNED & FIXED).
Expert on customer reviews, ratings, and product sentiment.
"""

from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
import re

from src.config import Config
from src.tools.vector_tools import get_vector_tools
from src.tools.graph_tools import get_graph_tools

class ReviewAgent:
    """Enhanced specialist agent for review-based queries."""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=Config.OPENAI_API_KEY,
            model=Config.OPENAI_MODEL,
            temperature=0.5
        )
        self.vector_tools = get_vector_tools()
        self.graph_tools = get_graph_tools()
        
        self.system_prompt = """You are the Review Agent, a specialist in customer reviews and sentiment analysis.

Your expertise:
- Finding products based on review content
- Analyzing product ratings and sentiment
- Identifying products with specific qualities mentioned in reviews
- Providing honest review summaries
- Understanding customer pain points and satisfaction

Guidelines:
- Focus on what customers actually say
- Highlight common themes in reviews
- Mention average ratings when relevant
- Be honest about both positive and negative feedback
- Help users understand real-world product experiences
"""
    
    def process(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process review-related queries.
        
        Args:
            query: The user's question
            context: Optional context (e.g., product_ids from other agents)
        
        Returns:
            Dict with results and thinking steps
        """
        thinking_steps = []
        thinking_steps.append("⭐ Analyzing query for review-based insights...")
        
        query_lower = query.lower()
        results = None
        
        # Check if we need to filter by products from context
        product_ids = context.get('product_ids', []) if context else []
        
        # ✅ NEW: Try to extract specific product name first
        if not product_ids and any(keyword in query_lower for keyword in ["about", "for", "of", "think about"]):
            thinking_steps.append("🔍 Attempting to extract specific product name...")
            
            # Extract product name after keywords
            patterns = [
                r'(?:about|for|of)\s+(.+?)(?:\?|$)',
                r'(?:think about|customers say about|reviews for)\s+(.+?)(?:\?|$)',
                r'(?:what do customers)\s+.+?\s+(?:about|for)\s+(.+?)(?:\?|$)'
            ]
            
            product_name = None
            for pattern in patterns:
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    product_name = match.group(1).strip()
                    # Remove common trailing words
                    product_name = re.sub(r'\s+(headphones?|laptop|phone|smartphone|tablet)$', r' \1', product_name, flags=re.IGNORECASE)
                    break
            
            if product_name:
                thinking_steps.append(f"   Extracted product name: {product_name}")
                
                # Search for the product by name
                products = self.graph_tools.search_products_by_name(product_name, limit=3)
                if products:
                    product_ids = [p['id'] for p in products]
                    thinking_steps.append(f"   Found {len(product_ids)} matching products")
                else:
                    thinking_steps.append(f"   No exact match, falling back to semantic search")
        
        # CASE 1: Specific product reviews (extracted or from context)
        if product_ids:
            thinking_steps.append(f"📝 Getting reviews for {len(product_ids)} specific product(s)")
            results = []
            for pid in product_ids[:3]:  # Limit to top 3 matches
                sentiment = self.vector_tools.get_product_sentiment_summary(pid)
                if sentiment['review_count'] > 0:
                    product = self.graph_tools.get_product_by_id(pid)
                    # Get actual review texts
                    reviews = self.vector_tools.get_product_reviews(pid)
                    results.append({
                        'product': product,
                        'sentiment': sentiment,
                        'relevant_reviews': reviews[:2]  # Show top 2 reviews
                    })
        
        # CASE 2: Reviews with specific keywords
        elif "reviews" in query_lower or "rated" in query_lower or "opinion" in query_lower or "think" in query_lower or "customers say" in query_lower or "feedback" in query_lower:
            thinking_steps.append("🔍 Searching reviews semantically")
            review_results = self.vector_tools.search_reviews_semantic(query, top_k=10)
            
            # Get unique product IDs
            product_ids = list(set([r['product_id'] for r in review_results]))
            thinking_steps.append(f"Found reviews from {len(product_ids)} products")
            
            results = []
            for pid in product_ids[:5]:
                product = self.graph_tools.get_product_by_id(pid)
                sentiment = self.vector_tools.get_product_sentiment_summary(pid)
                results.append({
                    'product': product,
                    'sentiment': sentiment,
                    'relevant_reviews': [r for r in review_results if r['product_id'] == pid][:2]
                })
        
        # CASE 3: Quality-based search (good, best, excellent, etc.)
        elif any(quality in query_lower for quality in ["good", "best", "excellent", "great", "top rated", "highest rated"]):
            thinking_steps.append("🎯 Searching for top-rated products")
            product_ids = self.vector_tools.search_products_by_review_content(
                query, 
                min_similarity=0.6,
                top_k=10
            )
            
            thinking_steps.append(f"Found {len(product_ids)} highly-rated products")
            
            results = []
            for pid in product_ids[:5]:
                product = self.graph_tools.get_product_by_id(pid)
                sentiment = self.vector_tools.get_product_sentiment_summary(pid)
                results.append({
                    'product': product,
                    'sentiment': sentiment
                })
        
        # CASE 4: Default semantic search
        else:
            thinking_steps.append("🔎 Performing semantic review search")
            review_results = self.vector_tools.search_reviews_semantic(query, top_k=10)
            
            product_ids = list(set([r['product_id'] for r in review_results]))
            
            results = []
            for pid in product_ids[:5]:
                product = self.graph_tools.get_product_by_id(pid)
                sentiment = self.vector_tools.get_product_sentiment_summary(pid)
                results.append({
                    'product': product,
                    'sentiment': sentiment
                })
        
        thinking_steps.append(f"✓ Analyzed reviews for {len(results) if results else 0} products")
        
        return {
            "agent": "Review Agent",
            "results": results,
            "thinking": thinking_steps,
            "success": results is not None and len(results) > 0
        }
    
    def format_response(self, results: List[Dict]) -> str:
        """Format review results with natural language summary."""
        if not results:
            return "No reviews found matching your criteria. Try asking about specific products or brands."
        
        response = f"**Found {len(results)} product(s) with relevant reviews:**\n\n"
        
        for i, item in enumerate(results, 1):
            product = item['product']
            sentiment = item['sentiment']
            
            response += f"### {i}. {product['name']}\n"
            response += f"**Brand:** {product['brand']} | **Price:** ₹{product['price']:,.2f}\n\n"
            response += f"**Customer Rating:** {sentiment['average_rating']:.1f}/5 ({sentiment['review_count']} reviews)\n\n"
            
            # Show relevant review excerpts if available
            if 'relevant_reviews' in item and item['relevant_reviews']:
                response += "**What customers are saying:**\n"
                for review in item['relevant_reviews'][:2]:
                    response += f"  • \"{review['text'][:150]}...\" ({review['rating']}/5)\n"
                response += "\n"
        
        # Natural language summary
        response += "\n**Summary:** "
        avg_rating = sum(r['sentiment']['average_rating'] for r in results) / len(results)
        
        if len(results) == 1:
            # Specific product summary
            product = results[0]['product']
            rating = results[0]['sentiment']['average_rating']
            if rating >= 4.5:
                response += f"The {product['name']} has excellent customer satisfaction with a {rating:.1f}/5 rating. "
            elif rating >= 4.0:
                response += f"The {product['name']} is well-received by customers with a {rating:.1f}/5 rating. "
            elif rating >= 3.5:
                response += f"The {product['name']} has mixed reviews ({rating:.1f}/5) - check specific features that matter to you. "
            else:
                response += f"The {product['name']} has lower ratings ({rating:.1f}/5) - consider alternatives or check recent reviews. "
        else:
            # Multiple products summary
            if avg_rating >= 4.5:
                response += "These products have excellent customer satisfaction with consistently high ratings. "
            elif avg_rating >= 4.0:
                response += "These products are well-received by customers with good overall ratings. "
            elif avg_rating >= 3.5:
                response += "These products have mixed reviews - check specific features that matter to you. "
            else:
                response += "Customer feedback suggests considering alternatives or checking recent reviews for improvements. "
        
        response += "Read detailed reviews to understand how each product performs in real-world use!"
        
        return response
