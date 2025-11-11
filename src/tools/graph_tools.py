"""
Graph Tools: Neo4j knowledge graph query tools (ENHANCED).
Used by Graph Agent to query product catalog with advanced filtering.
"""

from typing import List, Dict, Optional
from src.config import Config

# Category and Brand Synonym Mapping
CATEGORY_SYNONYMS = {
    "phone": "Smartphones",
    "phones": "Smartphones",
    "mobile": "Smartphones",
    "mobiles": "Smartphones",
    "mobile phone": "Smartphones",
    "mobile phones": "Smartphones",
    "smartphone": "Smartphones",
    "cellphone": "Smartphones",
    
    "laptop": "Laptops",
    "laptops": "Laptops",
    "computer": "Laptops",
    "computers": "Laptops",
    "notebook": "Laptops",
    
    "headphone": "Headphones",
    "headphones": "Headphones",
    "earphone": "Headphones",
    "earphones": "Headphones",
    "earbud": "Headphones",
    "earbuds": "Headphones",
    
    "tablet": "Tablets",
    "tablets": "Tablets",
    "ipad": "Tablets",
    
    "watch": "Smartwatches",
    "watches": "Smartwatches",
    "smartwatch": "Smartwatches",
    
    "speaker": "Speakers",
    "speakers": "Speakers",
    
    "camera": "Cameras",
    "cameras": "Cameras",
    
    "console": "Gaming Consoles",
    "consoles": "Gaming Consoles",
    "gaming console": "Gaming Consoles"
}

class GraphTools:
    """Enhanced tools for querying the Neo4j knowledge graph."""
    
    def __init__(self):
        self.driver = Config.get_neo4j_driver()
    
    def map_category(self, query: str) -> Optional[str]:
        """Map user query terms to actual category names."""
        query_lower = query.lower()
        for synonym, category in CATEGORY_SYNONYMS.items():
            if synonym in query_lower:
                return category
        return None
    
    def get_products_by_brand(self, brand: str, limit: int = 10) -> List[Dict]:
        """Get all products by a specific brand."""
        with self.driver.session() as session:
            query = """
            MATCH (p:Product)-[:MANUFACTURED_BY]->(b:Brand {name: $brand})
            MATCH (p)-[:BELONGS_TO]->(c:Category)
            RETURN p.id as id, p.name as name, p.price as price, 
                   b.name as brand, c.name as category
            LIMIT $limit
            """
            result = session.run(query, brand=brand, limit=limit)
            return [dict(record) for record in result]
    
    def get_products_by_category(self, category: str, limit: int = 10) -> List[Dict]:
        """Get all products in a specific category."""
        with self.driver.session() as session:
            query = """
            MATCH (p:Product)-[:BELONGS_TO]->(c:Category {name: $category})
            MATCH (p)-[:MANUFACTURED_BY]->(b:Brand)
            RETURN p.id as id, p.name as name, p.price as price,
                   b.name as brand, c.name as category
            LIMIT $limit
            """
            result = session.run(query, category=category, limit=limit)
            return [dict(record) for record in result]
    
    def get_product_by_id(self, product_id: str) -> Optional[Dict]:
        """Get detailed information about a specific product including specs."""
        with self.driver.session() as session:
            query = """
            MATCH (p:Product {id: $product_id})
            MATCH (p)-[:MANUFACTURED_BY]->(b:Brand)
            MATCH (p)-[:BELONGS_TO]->(c:Category)
            OPTIONAL MATCH (p)-[:HAS_REVIEW]->(r:Review)
            RETURN p.id as id, p.name as name, p.price as price,
                   b.name as brand, c.name as category,
                   collect({rating: r.rating, text: r.text}) as reviews,
                   properties(p) as specs
            """
            result = session.run(query, product_id=product_id)
            record = result.single()
            return dict(record) if record else None
    
    def get_products_by_spec(self, spec_name: str, spec_value: str, 
                            category: Optional[str] = None,
                            limit: int = 10) -> List[Dict]:
        """Get products matching a specific specification (e.g., RAM > 12GB)."""
        with self.driver.session() as session:
            if category:
                query = """
                MATCH (p:Product)-[:BELONGS_TO]->(c:Category {name: $category})
                MATCH (p)-[:MANUFACTURED_BY]->(b:Brand)
                WHERE p[$spec_name] =~ $spec_pattern
                RETURN p.id as id, p.name as name, p.price as price,
                       b.name as brand, c.name as category,
                       p[$spec_name] as spec_value
                LIMIT $limit
                """
            else:
                query = """
                MATCH (p:Product)
                MATCH (p)-[:MANUFACTURED_BY]->(b:Brand)
                MATCH (p)-[:BELONGS_TO]->(c:Category)
                WHERE p[$spec_name] =~ $spec_pattern
                RETURN p.id as id, p.name as name, p.price as price,
                       b.name as brand, c.name as category,
                       p[$spec_name] as spec_value
                LIMIT $limit
                """
            
            # Create regex pattern for spec matching
            spec_pattern = f".*{spec_value}.*"
            
            result = session.run(query, 
                               spec_name=spec_name, 
                               spec_pattern=spec_pattern,
                               category=category,
                               limit=limit)
            return [dict(record) for record in result]
    
    def get_brands_by_category(self, category: str) -> List[str]:
        """Get all brands that make products in a specific category."""
        with self.driver.session() as session:
            query = """
            MATCH (p:Product)-[:BELONGS_TO]->(c:Category {name: $category})
            MATCH (p)-[:MANUFACTURED_BY]->(b:Brand)
            RETURN DISTINCT b.name as brand
            ORDER BY b.name
            """
            result = session.run(query, category=category)
            return [record['brand'] for record in result]
    
    def get_all_brands(self) -> List[str]:
        """Get list of all available brands."""
        with self.driver.session() as session:
            query = """
            MATCH (b:Brand)
            RETURN b.name as brand
            ORDER BY b.name
            """
            result = session.run(query)
            return [record['brand'] for record in result]
    
    def get_all_categories(self) -> List[str]:
        """Get list of all product categories."""
        with self.driver.session() as session:
            query = """
            MATCH (c:Category)
            RETURN c.name as category
            ORDER BY c.name
            """
            result = session.run(query)
            return [record['category'] for record in result]
    
    def search_products_by_name(self, search_term: str, limit: int = 10) -> List[Dict]:
        """Search products by name (case-insensitive partial match)."""
        with self.driver.session() as session:
            query = """
            MATCH (p:Product)
            WHERE toLower(p.name) CONTAINS toLower($search_term)
            MATCH (p)-[:MANUFACTURED_BY]->(b:Brand)
            MATCH (p)-[:BELONGS_TO]->(c:Category)
            RETURN p.id as id, p.name as name, p.price as price,
                   b.name as brand, c.name as category
            LIMIT $limit
            """
            result = session.run(query, search_term=search_term, limit=limit)
            return [dict(record) for record in result]
    
    def get_products_by_brand_and_category(self, brand: str, category: str, 
                                          limit: int = 10) -> List[Dict]:
        """Get products filtered by both brand and category."""
        with self.driver.session() as session:
            query = """
            MATCH (p:Product)-[:MANUFACTURED_BY]->(b:Brand {name: $brand})
            MATCH (p)-[:BELONGS_TO]->(c:Category {name: $category})
            RETURN p.id as id, p.name as name, p.price as price,
                   b.name as brand, c.name as category
            LIMIT $limit
            """
            result = session.run(query, brand=brand, category=category, limit=limit)
            return [dict(record) for record in result]
    
    def get_product_count_by_category(self) -> Dict[str, int]:
        """Get count of products in each category."""
        with self.driver.session() as session:
            query = """
            MATCH (p:Product)-[:BELONGS_TO]->(c:Category)
            RETURN c.name as category, count(p) as count
            ORDER BY count DESC
            """
            result = session.run(query)
            return {record['category']: record['count'] for record in result}
    
    def get_product_specs(self, product_id: str) -> Dict[str, str]:
        """Get all specifications for a product."""
        with self.driver.session() as session:
            query = """
            MATCH (p:Product {id: $product_id})
            RETURN properties(p) as specs
            """
            result = session.run(query, product_id=product_id)
            record = result.single()
            if record:
                specs = dict(record['specs'])
                # Remove non-spec properties
                specs.pop('id', None)
                specs.pop('name', None)
                specs.pop('price', None)
                return specs
            return {}
    
    def close(self):
        """Close the Neo4j connection."""
        self.driver.close()

# Singleton instance
_graph_tools_instance = None

def get_graph_tools() -> GraphTools:
    """Get or create the GraphTools singleton instance."""
    global _graph_tools_instance
    if _graph_tools_instance is None:
        _graph_tools_instance = GraphTools()
    return _graph_tools_instance
