"""
Graph Agent: Product knowledge specialist.
Expert on product catalog with intelligent query understanding.
"""

from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
import re

from src.config import Config
from src.tools.graph_tools import get_graph_tools

class GraphAgent:
    """Enhanced specialist agent for product catalog queries with NLU."""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=Config.OPENAI_API_KEY,
            model=Config.OPENAI_MODEL,
            temperature=1
        )
        self.tools = get_graph_tools()
        
        self.system_prompt = """You are the Graph Agent, a specialist in product catalog knowledge.

Your expertise:
- Finding products by brand, category, or name
- Providing detailed product specifications
- Listing available brands and categories
- Answering counting queries (how many, count, etc.)
- Filtering by specifications (RAM, storage, display, etc.)
- Understanding synonyms (phone=smartphone, laptop=computer, etc.)

Your tools:
- get_products_by_brand(brand, limit)
- get_products_by_category(category, limit)
- get_product_by_id(product_id)
- get_all_brands()
- get_all_categories()
- search_products_by_name(search_term, limit)
- get_products_by_brand_and_category(brand, category, limit)
- get_products_by_spec(spec_name, spec_value, category, limit)
- get_brands_by_category(category)

Guidelines:
- Always map user terms to actual category names (phone→Smartphones)
- For counting queries, provide actual counts and lists
- For spec queries, extract the spec name and value
- Keep responses structured and informative
- If no products found, suggest alternatives
"""
    
    def process(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a query with intelligent understanding.
        
        Args:
            query: The user's question
            context: Optional context from other agents
        
        Returns:
            Dict with results and thinking steps
        """
        thinking_steps = []
        thinking_steps.append("📊 Analyzing query for product information needs...")
        
        query_lower = query.lower()
        results = None
        result_type = "products"
        
        # Map category synonyms
        mapped_category = self.tools.map_category(query)
        
        # ✅ CASE 0 - Specific product specification queries (HIGHEST PRIORITY)
        if self._is_specification_request(query_lower):
            thinking_steps.append("📐 Detected product specification request")
            spec_result = self._handle_specification_request(query, thinking_steps)
            if spec_result[0] is not None:
                results, result_type = spec_result
                thinking_steps.append(f"✓ Found product details with specifications")
                return {
                    "agent": "Graph Agent",
                    "results": results,
                    "result_type": result_type,
                    "thinking": thinking_steps,
                    "success": True
                }
            else:
                thinking_steps.append("⚠️ Could not extract specific product, trying other methods...")
        
        # CASE 1: Counting queries
        if self._is_counting_query(query_lower):
            thinking_steps.append("🔢 Detected counting query")
            results, result_type = self._handle_counting_query(query_lower, mapped_category, thinking_steps)
        
        # CASE 2: Specification filtering queries (with operators)
        elif self._is_spec_query(query_lower):
            thinking_steps.append("📐 Detected specification filtering query")
            results = self._handle_spec_query(query_lower, mapped_category, thinking_steps)
        
        # CASE 3: Brand queries
        elif self._is_brand_query(query_lower):
            brand = self._extract_brand(query_lower)
            if brand:
                thinking_steps.append(f"🔍 Searching products by brand: {brand}")
                if mapped_category:
                    thinking_steps.append(f"   with category filter: {mapped_category}")
                    results = self.tools.get_products_by_brand_and_category(brand, mapped_category, limit=20)
                else:
                    results = self.tools.get_products_by_brand(brand, limit=20)
        
        # CASE 4: Category queries
        elif mapped_category:
            thinking_steps.append(f"🔍 Searching products by category: {mapped_category}")
            results = self.tools.get_products_by_category(mapped_category, limit=20)
        
        # CASE 5: List all brands
        elif "all brands" in query_lower or "brands available" in query_lower:
            thinking_steps.append("📋 Retrieving all available brands")
            brands = self.tools.get_all_brands()
            results = {"type": "brands_list", "brands": brands}
            result_type = "list"
        
        # CASE 6: List all categories
        elif "all categories" in query_lower or "categories available" in query_lower:
            thinking_steps.append("📋 Retrieving all product categories")
            categories = self.tools.get_all_categories()
            results = {"type": "categories_list", "categories": categories}
            result_type = "list"
        
        # CASE 7: General product search
        else:
            thinking_steps.append("🔎 Performing general product search")
            search_term = self._extract_search_term(query)
            results = self.tools.search_products_by_name(search_term, limit=20)
        
        # Determine success
        if result_type == "count":
            success = results is not None and isinstance(results, dict)
        elif result_type == "list":
            success = results is not None and isinstance(results, dict)
        elif result_type == "product_details":
            success = results is not None
        else:
            success = results is not None and len(results) > 0 if isinstance(results, list) else True
        
        thinking_steps.append(f"✓ Found {self._describe_results(results, result_type)}")
        
        return {
            "agent": "Graph Agent",
            "results": results,
            "result_type": result_type,
            "thinking": thinking_steps,
            "success": success
        }
    
    def _is_specification_request(self, query: str) -> bool:
        """Check if query is asking for product specifications."""
        spec_keywords = ["specification", "specifications", "specs", "spec", "details", "features"]
        question_starters = ["what are", "what is", "tell me about", "show me"]
        
        # Check for explicit spec keywords or question patterns
        has_spec_keyword = any(keyword in query for keyword in spec_keywords)
        has_question = any(starter in query for starter in question_starters)
        
        return has_spec_keyword or has_question
    
    def _handle_specification_request(self, query: str, thinking_steps: List[str]) -> tuple:
        """Handle queries asking for product specifications - FIXED REGEX."""
        # Multiple patterns to extract product name
        patterns = [
            # "specifications of Apple MacBook Air M2"
            r'(?:specification|specifications|specs|spec|details|features)\s+(?:of|for)\s+(?:the\s+)?(.+?)(?:\?|$)',
            # "what are the specifications of Apple MacBook Air M2"
            r'(?:what are|what is)\s+(?:the\s+)?(?:specification|specifications|specs|spec|details|features)\s+(?:of|for)\s+(?:the\s+)?(.+?)(?:\?|$)',
            # "tell me about Apple MacBook Air M2"
            r'(?:tell me about|show me)\s+(?:the\s+)?(.+?)(?:\?|$)',
            # "Apple MacBook Air M2 specifications"
            r'(.+?)\s+(?:specification|specifications|specs|spec|details|features)(?:\?|$)'
        ]
        
        product_name = None
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                product_name = match.group(1).strip()
                
                # Clean up the extracted product name
                # Remove leading articles
                product_name = re.sub(r'^(?:the|a|an)\s+', '', product_name, flags=re.IGNORECASE)
                # Remove trailing spec keywords
                product_name = re.sub(r'\s+(?:specification|specifications|specs|spec|details|features)$', '', product_name, flags=re.IGNORECASE)
                
                # Only accept if meaningful length
                if len(product_name) > 3:
                    break
                else:
                    product_name = None
        
        if product_name:
            thinking_steps.append(f"🔍 Extracted product name: '{product_name}'")
            products = self.tools.search_products_by_name(product_name, limit=3)
            
            if products:
                # Pick the best match (first result is most relevant)
                product_id = products[0]['id']
                thinking_steps.append(f"   Best match: {products[0]['name']}")
                
                # Get detailed product with specs
                detailed_product = self.tools.get_product_by_id(product_id)
                if detailed_product:
                    return detailed_product, "product_details"
            else:
                thinking_steps.append(f"   No products found for '{product_name}'")
        
        return None, "products"
    
    def _is_counting_query(self, query: str) -> bool:
        """Check if query is asking for counts."""
        counting_keywords = ["how many", "count", "number of", "total"]
        return any(keyword in query for keyword in counting_keywords)
    
    def _is_spec_query(self, query: str) -> bool:
        """Check if query is about specification filtering (with operators)."""
        spec_keywords = ["ram", "storage", "display", "screen", "battery", "camera", "processor", "gb", "tb", "inch"]
        spec_operators = [">", "<", "more than", "less than", "at least", "minimum", "maximum", "above", "below"]
        return (any(keyword in query for keyword in spec_keywords) and 
                any(op in query for op in spec_operators))
    
    def _is_brand_query(self, query: str) -> bool:
        """Check if query mentions a specific brand."""
        brands = [b.lower() for b in self.tools.get_all_brands()]
        return any(brand in query for brand in brands)
    
    def _extract_brand(self, query: str) -> Optional[str]:
        """Extract brand name from query."""
        brands = self.tools.get_all_brands()
        for brand in brands:
            if brand.lower() in query:
                return brand
        return None
    
    def _extract_search_term(self, query: str) -> str:
        """Extract search term from general queries."""
        # Remove common question words
        stop_words = ["what", "which", "show", "me", "find", "get", "tell", "about", "is", "are", "the", "of"]
        terms = query.lower().split()
        filtered = [t for t in terms if t not in stop_words and len(t) > 2]
        return " ".join(filtered[:4])  # Take first 4 significant terms
    
    def _handle_counting_query(self, query: str, category: Optional[str], 
                               thinking_steps: List[str]) -> tuple:
        """Handle counting queries like 'how many brands'."""
        
        if "brand" in query:
            if category:
                thinking_steps.append(f"🔢 Counting brands in category: {category}")
                brands = self.tools.get_brands_by_category(category)
                return {
                    "type": "brand_count",
                    "category": category,
                    "count": len(brands),
                    "brands": sorted(brands)
                }, "count"
            else:
                thinking_steps.append("🔢 Counting all brands")
                brands = self.tools.get_all_brands()
                return {
                    "type": "brand_count",
                    "count": len(brands),
                    "brands": sorted(brands)
                }, "count"
        
        elif "categor" in query:
            thinking_steps.append("🔢 Counting all categories")
            categories = self.tools.get_all_categories()
            return {
                "type": "category_count",
                "count": len(categories),
                "categories": sorted(categories)
            }, "count"
        
        elif "product" in query or category:
            if category:
                thinking_steps.append(f"🔢 Counting products in category: {category}")
                products = self.tools.get_products_by_category(category, limit=100)
                return {
                    "type": "product_count",
                    "category": category,
                    "count": len(products),
                    "products": products[:10]  # Show first 10
                }, "count"
        
        return None, "count"
    
    def _handle_spec_query(self, query: str, category: Optional[str],
                          thinking_steps: List[str]) -> List[Dict]:
        """Handle specification-based filtering queries."""
        
        # Extract spec name
        spec_name = None
        spec_patterns = {
            r'(\d+)\s*gb\s+ram': ('RAM', r'\1GB'),
            r'ram.*?(\d+)\s*gb': ('RAM', r'\1GB'),
            r'(\d+)\s*gb\s+storage': ('Storage', r'\1GB'),
            r'storage.*?(\d+)\s*gb': ('Storage', r'\1GB'),
            r'(\d+\.?\d*)\s*inch.*display': ('Display', r'\1 inch'),
            r'display.*?(\d+\.?\d*)\s*inch': ('Display', r'\1 inch'),
        }
        
        for pattern, (name, value_pattern) in spec_patterns.items():
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                spec_name = name
                spec_value = re.sub(r'\\(\d+)', lambda m: match.group(int(m.group(1))), value_pattern)
                break
        
        if not spec_name:
            return []
        
        # Determine operator
        operator = "contains"
        if "more than" in query or ">" in query or "greater" in query or "above" in query:
            operator = ">"
        elif "less than" in query or "<" in query or "below" in query:
            operator = "<"
        elif "at least" in query or "minimum" in query:
            operator = ">="
        
        thinking_steps.append(f"🔍 Filtering by {spec_name} {operator} {spec_value}")
        if category:
            thinking_steps.append(f"   in category: {category}")
        
        from src.tools.filter_tools import get_filter_tools
        filter_tools = get_filter_tools()
        
        return filter_tools.filter_by_spec(spec_name, operator, spec_value, category, limit=20)
    
    def _describe_results(self, results, result_type: str) -> str:
        """Describe results for thinking steps."""
        if result_type == "count":
            if isinstance(results, dict):
                return f"{results.get('count', 0)} items"
        elif result_type == "list":
            if isinstance(results, dict):
                key = 'brands' if 'brands' in results else 'categories'
                return f"{len(results.get(key, []))} items"
        elif result_type == "product_details":
            return "product details with specifications"
        elif isinstance(results, list):
            return f"{len(results)} products"
        return "relevant results"
    
    def format_response(self, results: Any, result_type: str = "products") -> str:
        """Format results with natural language summary."""
        
        if result_type == "product_details":
            return self._format_product_details(results)
        elif result_type == "count":
            return self._format_count_response(results)
        elif result_type == "list":
            return self._format_list_response(results)
        else:
            return self._format_product_response(results)
    
    def _format_product_details(self, product: Dict) -> str:
        """Format detailed product information with specifications."""
        response = f"# {product['name']}\n\n"
        response += f"**Brand:** {product['brand']}\n"
        response += f"**Category:** {product['category']}\n"
        response += f"**Price:** ₹{product['price']:,.2f}\n\n"
        
        # Get specs
        specs = product.get('specs', {})
        if specs:
            response += "## 📐 Specifications:\n\n"
            # Remove non-spec properties
            filtered_specs = {k: v for k, v in specs.items() 
                             if k not in ['id', 'name', 'price']}
            
            if filtered_specs:
                for spec_name, spec_value in sorted(filtered_specs.items()):
                    response += f"• **{spec_name}:** {spec_value}\n"
            else:
                response += "*Detailed specifications are not available in the database yet.*\n"
        else:
            response += "## 📐 Specifications:\n\n*Specifications not available in database. Please check the manufacturer's website for detailed specs.*\n"
        
        response += "\n"
        
        # Add reviews if available
        reviews = product.get('reviews', [])
        if reviews and any(r.get('text') for r in reviews):
            response += "## ⭐ Customer Reviews:\n\n"
            valid_reviews = [r for r in reviews if r.get('text')][:3]
            avg_rating = sum(r.get('rating', 0) for r in valid_reviews) / len(valid_reviews) if valid_reviews else 0
            response += f"**Average Rating:** {avg_rating:.1f}/5 ({len(valid_reviews)} reviews)\n\n"
            for review in valid_reviews:
                if review.get('rating') and review.get('text'):
                    response += f"• **{review['rating']}/5:** \"{review['text'][:150]}...\"\n"
            response += "\n"
        
        response += "\n**💡 Need More Help?**\n"
        response += "• Compare this product with alternatives\n"
        response += "• Read detailed customer reviews\n"
        response += "• Filter similar products by your budget\n"
        
        return response
    
    def _format_count_response(self, results: Dict) -> str:
        """Format counting query responses."""
        count_type = results.get('type', '')
        count = results.get('count', 0)
        
        if count_type == "brand_count":
            category = results.get('category')
            brands = results.get('brands', [])
            
            if category:
                response = f"**We have {count} brands** offering {category.lower()}:\n\n"
            else:
                response = f"**We have {count} brands** available:\n\n"
            
            response += "\n".join([f"• {brand}" for brand in brands])
            response += f"\n\n*You can browse products from any of these {count} brands!*"
            return response
        
        elif count_type == "category_count":
            categories = results.get('categories', [])
            response = f"**We have {count} product categories** available:\n\n"
            response += "\n".join([f"• {cat}" for cat in categories])
            response += f"\n\n*Explore any category to find the perfect product for you!*"
            return response
        
        elif count_type == "product_count":
            category = results.get('category', 'products')
            response = f"**We have {count} {category.lower()}** in our catalog.\n\n"
            if results.get('products'):
                response += "Here are some examples:\n\n"
                for i, p in enumerate(results['products'][:5], 1):
                    response += f"{i}. **{p['name']}** by {p['brand']} - ₹{p['price']:,.2f}\n"
            return response
        
        return f"Found {count} items."
    
    def _format_list_response(self, results: Dict) -> str:
        """Format list responses."""
        if 'brands' in results:
            brands = results['brands']
            response = f"**Available Brands ({len(brands)}):**\n\n"
            response += "\n".join([f"• {b}" for b in brands])
            return response
        elif 'categories' in results:
            categories = results['categories']
            response = f"**Product Categories ({len(categories)}):**\n\n"
            response += "\n".join([f"• {c}" for c in categories])
            return response
        return "Results found."
    
    def _format_product_response(self, results: List[Dict]) -> str:
        """Format product list responses."""
        if not results:
            return "No products found matching your criteria."
        
        response = f"**Found {len(results)} products:**\n\n"
        for i, product in enumerate(results[:10], 1):
            response += f"{i}. **{product['name']}**\n"
            response += f"   • Brand: {product['brand']}\n"
            response += f"   • Category: {product['category']}\n"
            response += f"   • Price: **₹{product['price']:,.2f}**\n"
            if 'spec_value' in product:
                response += f"   • Specification: {product['spec_value']}\n"
            response += "\n"
        
        if len(results) > 10:
            response += f"*...and {len(results) - 10} more products*\n\n"
        
        response += "*Need help choosing? Ask me to compare specific products or filter by your budget!*"
        return response
