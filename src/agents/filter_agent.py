"""
Filter Agent: Constraint and filtering specialist (ENHANCED).
Expert on price ranges, specifications, and multi-constraint filtering.
"""

from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI

from src.config import Config
from src.tools.filter_tools import get_filter_tools
from src.tools.graph_tools import get_graph_tools

class FilterAgent:
    """Enhanced specialist agent for filtering products by constraints."""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=Config.OPENAI_API_KEY,
            model=Config.OPENAI_MODEL,
            temperature=0.3
        )
        self.filter_tools = get_filter_tools()
        self.graph_tools = get_graph_tools()
        
        self.system_prompt = """You are the Filter Agent, a specialist in constraint-based product filtering.

Your expertise:
- Filtering products by price range
- Applying multi-constraint filters
- Finding best value options
- Understanding budget terminology
- Sorting and ranking products

Guidelines:
- Be precise with numerical constraints
- Always respect budget limits
- Sort by price (lowest first) unless specified
- If no matches, suggest nearby alternatives
- Help users find the best value
"""
    
    def process(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process filtering queries."""
        thinking_steps = []
        thinking_steps.append("💰 Analyzing price and constraint requirements...")
        
        # Extract constraints
        constraints = self._extract_constraints(query, context)
        thinking_steps.append(f"🎯 Identified constraints: {constraints}")
        
        # Apply filters
        results = None
        
        if constraints['brand'] and constraints['category']:
            thinking_steps.append(
                f"🔍 Filtering by brand ({constraints['brand']}), "
                f"category ({constraints['category']}), "
                f"and price (₹{constraints['min_price']:,} - ₹{constraints['max_price']:,})"
            )
            results = self.filter_tools.apply_multiple_filters(
                brand=constraints['brand'],
                category=constraints['category'],
                min_price=constraints['min_price'],
                max_price=constraints['max_price'],
                limit=20
            )
        
        elif constraints['brand']:
            thinking_steps.append(
                f"🔍 Filtering by brand ({constraints['brand']}) "
                f"and price (₹{constraints['min_price']:,} - ₹{constraints['max_price']:,})"
            )
            results = self.filter_tools.filter_by_brand_and_price(
                brand=constraints['brand'],
                min_price=constraints['min_price'],
                max_price=constraints['max_price'],
                limit=20
            )
        
        elif constraints['category']:
            thinking_steps.append(
                f"🔍 Filtering by category ({constraints['category']}) "
                f"and price (₹{constraints['min_price']:,} - ₹{constraints['max_price']:,})"
            )
            results = self.filter_tools.filter_by_category_and_price(
                category=constraints['category'],
                min_price=constraints['min_price'],
                max_price=constraints['max_price'],
                limit=20
            )
        
        else:
            thinking_steps.append(
                f"🔍 Filtering by price only (₹{constraints['min_price']:,} - ₹{constraints['max_price']:,})"
            )
            results = self.filter_tools.filter_by_price(
                min_price=constraints['min_price'],
                max_price=constraints['max_price'],
                limit=20
            )
        
        thinking_steps.append(f"✓ Found {len(results)} products matching constraints")
        
        return {
            "agent": "Filter Agent",
            "results": results,
            "constraints": constraints,
            "thinking": thinking_steps,
            "success": results is not None and len(results) > 0
        }
    
    def _extract_constraints(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract filtering constraints from query."""
        import re
        
        constraints = {
            'min_price': 0,
            'max_price': float('inf'),
            'brand': context.get('brand') if context else None,
            'category': context.get('category') if context else None
        }
        
        query_lower = query.lower()
        
        # Extract price constraints
        under_match = re.search(r'(?:under|below|less than|max|maximum)\s*₹?\s*(\d+(?:,\d+)*)', query_lower)
        if under_match:
            price_str = under_match.group(1).replace(',', '')
            constraints['max_price'] = float(price_str)
        
        above_match = re.search(r'(?:above|over|more than|min|minimum)\s*₹?\s*(\d+(?:,\d+)*)', query_lower)
        if above_match:
            price_str = above_match.group(1).replace(',', '')
            constraints['min_price'] = float(price_str)
        
        between_match = re.search(r'between\s*₹?\s*(\d+(?:,\d+)*)\s*(?:and|to)\s*₹?\s*(\d+(?:,\d+)*)', query_lower)
        if between_match:
            min_str = between_match.group(1).replace(',', '')
            max_str = between_match.group(2).replace(',', '')
            constraints['min_price'] = float(min_str)
            constraints['max_price'] = float(max_str)
        
        around_match = re.search(r'around\s*₹?\s*(\d+(?:,\d+)*)', query_lower)
        if around_match:
            price_str = around_match.group(1).replace(',', '')
            price = float(price_str)
            constraints['min_price'] = price * 0.8
            constraints['max_price'] = price * 1.2
        
        # Extract brand
        if not constraints['brand']:
            for brand in self.graph_tools.get_all_brands():
                if brand.lower() in query_lower:
                    constraints['brand'] = brand
                    break
        
        # Extract category with synonym mapping
        if not constraints['category']:
            constraints['category'] = self.graph_tools.map_category(query)
        
        return constraints
    
    def format_response(self, results: List[Dict], constraints: Dict) -> str:
        """Format filtered results with natural language summary."""
        if not results:
            return f"No products found within ₹{constraints['min_price']:,.0f} - ₹{constraints['max_price']:,.0f}. Try expanding your budget or exploring different categories."
        
        response = f"**Found {len(results)} products within your constraints:**\n\n"
        
        for i, product in enumerate(results[:10], 1):
            response += f"{i}. **{product['name']}**\n"
            response += f"   • Brand: {product['brand']}\n"
            response += f"   • Category: {product['category']}\n"
            response += f"   • Price: **₹{product['price']:,.2f}**\n\n"
        
        if len(results) > 10:
            response += f"*...and {len(results) - 10} more products within your budget*\n\n"
        
        # Natural language summary
        response += "**Summary:** "
        cheapest = min(r['price'] for r in results)
        most_expensive = max(r['price'] for r in results)
        response += f"Prices range from ₹{cheapest:,.2f} to ₹{most_expensive:,.2f} in your selection. "
        
        if len(results) > 5:
            response += "You have plenty of options to choose from! "
        elif len(results) <= 2:
            response += "Limited options in this range - consider expanding your budget. "
        
        response += "Compare specific products or ask about reviews to make your final decision!"
        
        return response
