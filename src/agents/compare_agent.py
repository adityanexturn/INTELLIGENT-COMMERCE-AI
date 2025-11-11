"""
Compare Agent: Product comparison specialist (REDESIGNED).
Expert on side-by-side analysis with intelligent product extraction.
"""

from typing import List, Dict, Any
from langchain_openai import ChatOpenAI

from src.config import Config
from src.tools.compare_tools import get_compare_tools

class CompareAgent:
    """Enhanced specialist agent for comparing products."""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=Config.OPENAI_API_KEY,
            model=Config.OPENAI_MODEL,
            temperature=0.3
        )
        self.compare_tools = get_compare_tools()
        
        self.system_prompt = """You are the Compare Agent, a specialist in product comparison and recommendation.

Your expertise:
- Extracting product names from comparison queries
- Comparing products side-by-side with specs
- Identifying winners in specific categories
- Providing data-driven recommendations
- Helping users decide between options

Comparison methodology:
1. **Price comparison**: Identify best value
2. **Rating comparison**: Highlight highest-rated
3. **Spec comparison**: Compare key specifications
4. **Review sentiment**: Analyze customer feedback
5. **Trade-offs**: Explain pros and cons

Communication style:
- Be objective and data-driven
- Clearly state winners and losers
- Explain trade-offs honestly
- Use comparison tables for clarity
- Make final recommendation with reasoning
"""
    
    def process(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process comparison queries with intelligent product extraction.
        
        Args:
            query: Comparison query
            context: Optional context (can include product_ids)
        
        Returns:
            Dict with comparison results and thinking steps
        """
        thinking_steps = []
        thinking_steps.append("📊 Analyzing query for product information needs...")
        
        # Get product IDs - either from context or extract from query
        product_ids = context.get('product_ids', []) if context else []
        
        if not product_ids:
            # Extract product names using LLM
            thinking_steps.append("🔍 Extracting product names from query...")
            product_names = self.compare_tools.extract_product_names_from_query(query)
            
            if product_names:
                thinking_steps.append(f"   Found products: {', '.join(product_names)}")
                product_ids = self.compare_tools.find_products_by_names(product_names)
            else:
                return {
                    "agent": "Compare Agent",
                    "results": None,
                    "thinking": thinking_steps + ["⚠️ Could not extract products to compare"],
                    "success": False,
                    "error": "No products identified for comparison"
                }
        
        if len(product_ids) < 2:
            return {
                "agent": "Compare Agent",
                "results": None,
                "thinking": thinking_steps + ["⚠️ Need at least 2 products to compare"],
                "success": False,
                "error": "Insufficient products for comparison"
            }
        
        if len(product_ids) > 5:
            thinking_steps.append("⚠️ Too many products, limiting to top 5")
            product_ids = product_ids[:5]
        
        thinking_steps.append(f"🔄 Comparing {len(product_ids)} products...")
        
        # Perform comparison
        thinking_steps.append("📊 Gathering product details and reviews...")
        comparison = self.compare_tools.compare_products(product_ids)
        
        thinking_steps.append(f"✓ Compared {len(comparison['products'])} products")
        
        # Determine recommendation criteria from query
        criteria = {'price': 0.5, 'rating': 0.5}  # Default balanced
        
        if query:
            query_lower = query.lower()
            if any(word in query_lower for word in ['cheap', 'budget', 'affordable', 'save money', 'value']):
                criteria = {'price': 0.7, 'rating': 0.3}
                thinking_steps.append("💰 Prioritizing budget-friendly options")
            elif any(word in query_lower for word in ['best', 'quality', 'top', 'premium', 'highest rated']):
                criteria = {'price': 0.3, 'rating': 0.7}
                thinking_steps.append("⭐ Prioritizing quality and ratings")
        
        # Get recommendation
        recommendation = self.compare_tools.recommend_best(product_ids, criteria)
        thinking_steps.append(f"🏆 Recommended: {recommendation['recommended_name']}")
        
        return {
            "agent": "Compare Agent",
            "comparison": comparison,
            "recommendation": recommendation,
            "thinking": thinking_steps,
            "success": True
        }
    
    def format_response(self, comparison: Dict, recommendation: Dict) -> str:
        """Format comparison results with natural language summary."""
        if not comparison or not comparison['products']:
            return "Unable to compare products. Please specify product names clearly."
        
        products = comparison['products']
        response = "## 📊 Product Comparison\n\n"
        
        # Comparison table
        response += "| Product | Brand | Price | Rating | Reviews |\n"
        response += "|---------|-------|-------|--------|----------|\n"
        
        for product in products:
            is_winner = product['id'] == recommendation['recommended_id']
            name = f"**{product['name']}**" if is_winner else product['name']
            response += f"| {name} | {product['brand']} | ₹{product['price']:,.2f} | "
            response += f"{product['average_rating']:.1f}/5 | {product['review_count']} |\n"
        
        response += "\n"
        
        # Spec comparison if available
        if comparison.get('spec_comparison'):
            response += "### 🔧 Specifications\n\n"
            for spec_name, spec_values in list(comparison['spec_comparison'].items())[:5]:
                response += f"**{spec_name}:**\n"
                for prod_name, value in spec_values.items():
                    response += f"  • {prod_name}: {value}\n"
                response += "\n"
        
        # Winners
        price_winner = next(p for p in products if p['id'] == comparison['price_winner'])
        rating_winner = next(p for p in products if p['id'] == comparison['rating_winner'])
        
        response += "### 🏆 Winners\n\n"
        response += f"- **Best Price**: {price_winner['name']} (₹{price_winner['price']:,.2f})\n"
        response += f"- **Highest Rated**: {rating_winner['name']} ({rating_winner['average_rating']:.1f}/5)\n\n"
        
        # Final recommendation with reasoning
        response += f"### 💡 Our Recommendation\n\n"
        response += f"**{recommendation['recommended_name']}**\n\n"
        response += f"*{recommendation['reason']}*\n\n"
        
        # Natural language summary
        response += "**Summary:** "
        if recommendation['recommended_id'] == comparison['price_winner']:
            response += f"The {recommendation['recommended_name']} offers the best value for money with competitive features. "
        elif recommendation['recommended_id'] == comparison['rating_winner']:
            response += f"The {recommendation['recommended_name']} has the highest customer satisfaction ratings. "
        else:
            response += f"The {recommendation['recommended_name']} provides the best overall balance of price and quality. "
        
        response += "Consider your budget and specific needs before making your final decision!"
        
        return response
