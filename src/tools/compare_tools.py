"""
Compare Tools: Product comparison and recommendation tools (ENHANCED).
Used by Compare Agent with intelligent product name extraction.
"""

from typing import List, Dict, Optional
from langchain_openai import ChatOpenAI
from src.config import Config
from src.tools.graph_tools import get_graph_tools
from src.tools.vector_tools import get_vector_tools

class CompareTools:
    """Enhanced tools for comparing products with intelligent extraction."""
    
    def __init__(self):
        self.graph_tools = get_graph_tools()
        self.vector_tools = get_vector_tools()
        self.llm = ChatOpenAI(
            api_key=Config.OPENAI_API_KEY,
            model=Config.OPENAI_MODEL,
            temperature=0
        )
    
    def extract_product_names_from_query(self, query: str) -> List[str]:
        """
        Use LLM to intelligently extract product names from comparison queries.
        
        Example:
        Query: "Compare Apple MacBook Air M2 and Dell XPS 15"
        Returns: ["MacBook Air M2", "Dell XPS 15"]
        """
        prompt = f"""You are an expert at extracting product names from e-commerce queries.

Given a comparison query, extract ONLY the specific product names being compared.

Rules:
- Extract full product names including model numbers
- Remove words like "compare", "vs", "versus", "between", "and"
- Each product should be on a separate line
- If no clear products found, return "NONE"

Query: "{query}"

Extracted product names (one per line):"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content.strip()
            
            if content == "NONE":
                return []
            
            # Parse line-by-line
            product_names = [line.strip() for line in content.split('\n') if line.strip()]
            return product_names
        
        except Exception as e:
            print(f"⚠️ Error extracting product names: {e}")
            return []
    
    def find_products_by_names(self, product_names: List[str]) -> List[str]:
        """
        Find product IDs by searching for product names.
        Returns list of product IDs.
        """
        product_ids = []
        
        for name in product_names:
            # Try exact search first
            results = self.graph_tools.search_products_by_name(name, limit=5)
            
            if results:
                # Take the best match (first result)
                product_ids.append(results[0]['id'])
            else:
                # Try partial match with key terms
                key_terms = [term for term in name.split() if len(term) > 3]
                for term in key_terms:
                    results = self.graph_tools.search_products_by_name(term, limit=3)
                    if results:
                        product_ids.append(results[0]['id'])
                        break
        
        return product_ids
    
    def compare_products(self, product_ids: List[str]) -> Dict:
        """
        Compare multiple products side-by-side.
        
        Returns:
            Dictionary with comparison data for all products
        """
        comparisons = {
            'products': [],
            'price_winner': None,
            'rating_winner': None,
            'spec_comparison': {}
        }
        
        for product_id in product_ids:
            # Get product details
            product = self.graph_tools.get_product_by_id(product_id)
            if not product:
                continue
            
            # Get review sentiment
            sentiment = self.vector_tools.get_product_sentiment_summary(product_id)
            
            # Get specs
            specs = self.graph_tools.get_product_specs(product_id)
            
            comparisons['products'].append({
                'id': product_id,
                'name': product['name'],
                'brand': product['brand'],
                'category': product['category'],
                'price': product['price'],
                'review_count': sentiment['review_count'],
                'average_rating': sentiment.get('average_rating', 0),
                'specs': specs
            })
        
        # Determine winners
        if comparisons['products']:
            # Price winner (lowest price)
            comparisons['price_winner'] = min(
                comparisons['products'], 
                key=lambda x: x['price']
            )['id']
            
            # Rating winner (highest rating)
            comparisons['rating_winner'] = max(
                comparisons['products'],
                key=lambda x: x['average_rating'] if x['average_rating'] > 0 else 0
            )['id']
            
            # Compare common specs
            comparisons['spec_comparison'] = self._compare_specs(comparisons['products'])
        
        return comparisons
    
    def _compare_specs(self, products: List[Dict]) -> Dict:
        """Compare specifications across products."""
        if not products:
            return {}
        
        # Find common spec keys
        all_specs = [set(p['specs'].keys()) for p in products]
        common_specs = set.intersection(*all_specs) if all_specs else set()
        
        spec_comparison = {}
        for spec_name in common_specs:
            spec_comparison[spec_name] = {
                p['name']: p['specs'][spec_name] for p in products
            }
        
        return spec_comparison
    
    def get_comparison_table(self, product_ids: List[str]) -> str:
        """
        Generate a formatted comparison table.
        
        Returns:
            Markdown-formatted comparison table
        """
        comparison = self.compare_products(product_ids)
        
        if not comparison['products']:
            return "No products found for comparison."
        
        # Build markdown table
        table = "| Feature | " + " | ".join([p['name'][:30] for p in comparison['products']]) + " |\n"
        table += "|---------|" + "|".join(["--------" for _ in comparison['products']]) + "|\n"
        
        # Price row
        table += "| **Price** | " + " | ".join([f"₹{p['price']:,.2f}" for p in comparison['products']]) + " |\n"
        
        # Brand row
        table += "| **Brand** | " + " | ".join([p['brand'] for p in comparison['products']]) + " |\n"
        
        # Category row
        table += "| **Category** | " + " | ".join([p['category'] for p in comparison['products']]) + " |\n"
        
        # Rating row
        table += "| **Avg Rating** | " + " | ".join([f"{p['average_rating']:.1f}/5" for p in comparison['products']]) + " |\n"
        
        # Review count row
        table += "| **Reviews** | " + " | ".join([str(p['review_count']) for p in comparison['products']]) + " |\n"
        
        # Add common specs
        if comparison['spec_comparison']:
            for spec_name, spec_values in list(comparison['spec_comparison'].items())[:5]:
                table += f"| **{spec_name}** | "
                table += " | ".join([spec_values.get(p['name'], 'N/A') for p in comparison['products']])
                table += " |\n"
        
        return table
    
    def recommend_best(self, product_ids: List[str], criteria: Dict) -> Dict:
        """
        Recommend the best product based on given criteria.
        
        Args:
            product_ids: List of product IDs to compare
            criteria: Dict with weights like {'price': 0.4, 'rating': 0.6}
        
        Returns:
            Dict with recommendation and reasoning
        """
        comparison = self.compare_products(product_ids)
        
        if not comparison['products']:
            return {'recommended_id': None, 'reason': 'No products found'}
        
        # Normalize scores and calculate weighted score
        products = comparison['products']
        
        # Price normalization (lower is better)
        max_price = max(p['price'] for p in products)
        min_price = min(p['price'] for p in products)
        price_range = max_price - min_price if max_price != min_price else 1
        
        # Rating normalization (higher is better)
        max_rating = max(p['average_rating'] for p in products) or 1
        
        for product in products:
            # Price score (inverted - lower price = higher score)
            price_score = 1 - ((product['price'] - min_price) / price_range) if price_range > 0 else 0.5
            
            # Rating score
            rating_score = product['average_rating'] / max_rating if max_rating > 0 else 0
            
            # Weighted total
            product['score'] = (
                price_score * criteria.get('price', 0.5) +
                rating_score * criteria.get('rating', 0.5)
            )
        
        # Find best product
        best_product = max(products, key=lambda x: x['score'])
        
        # Generate reasoning
        reasons = []
        if best_product['price'] == min_price:
            reasons.append("lowest price")
        if best_product['average_rating'] == max_rating:
            reasons.append("highest rating")
        if best_product['review_count'] > 10:
            reasons.append(f"{best_product['review_count']} customer reviews")
        
        return {
            'recommended_id': best_product['id'],
            'recommended_name': best_product['name'],
            'score': best_product['score'],
            'reason': f"Best choice based on {', '.join(reasons)}" if reasons else "Best overall score",
            'details': best_product
        }
    
    def find_similar_products(self, product_id: str, limit: int = 5) -> List[Dict]:
        """Find products similar to the given product."""
        product = self.graph_tools.get_product_by_id(product_id)
        if not product:
            return []
        
        # Find products in same category with similar price
        price = product['price']
        price_range = price * 0.2  # 20% price tolerance
        
        similar = self.graph_tools.get_products_by_category(
            product['category'], 
            limit=limit * 2
        )
        
        # Filter by price range and exclude the source product
        filtered = [
            p for p in similar
            if p['id'] != product_id 
            and abs(p['price'] - price) <= price_range
        ]
        
        return filtered[:limit]

# Singleton instance
_compare_tools_instance = None

def get_compare_tools() -> CompareTools:
    """Get or create the CompareTools singleton instance."""
    global _compare_tools_instance
    if _compare_tools_instance is None:
        _compare_tools_instance = CompareTools()
    return _compare_tools_instance
