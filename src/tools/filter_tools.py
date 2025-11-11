"""
Filter Tools: Product filtering and sorting tools (ENHANCED).
Used by Filter Agent with spec-based filtering support.
"""

from typing import List, Dict, Optional, Tuple
from src.config import Config

class FilterTools:
    """Enhanced tools for filtering and sorting products."""
    
    def __init__(self):
        self.driver = Config.get_neo4j_driver()
    
    def filter_by_price(self, min_price: float = 0, 
                       max_price: float = float('inf'),
                       limit: int = 20) -> List[Dict]:
        """Filter products by price range."""
        with self.driver.session() as session:
            query = """
            MATCH (p:Product)
            WHERE p.price >= $min_price AND p.price <= $max_price
            MATCH (p)-[:MANUFACTURED_BY]->(b:Brand)
            MATCH (p)-[:BELONGS_TO]->(c:Category)
            RETURN p.id as id, p.name as name, p.price as price,
                   b.name as brand, c.name as category
            ORDER BY p.price ASC
            LIMIT $limit
            """
            result = session.run(query, min_price=min_price, 
                               max_price=max_price, limit=limit)
            return [dict(record) for record in result]
    
    def filter_by_brand_and_price(self, brand: str, 
                                  min_price: float = 0,
                                  max_price: float = float('inf'),
                                  limit: int = 20) -> List[Dict]:
        """Filter products by brand and price range."""
        with self.driver.session() as session:
            query = """
            MATCH (p:Product)-[:MANUFACTURED_BY]->(b:Brand {name: $brand})
            WHERE p.price >= $min_price AND p.price <= $max_price
            MATCH (p)-[:BELONGS_TO]->(c:Category)
            RETURN p.id as id, p.name as name, p.price as price,
                   b.name as brand, c.name as category
            ORDER BY p.price ASC
            LIMIT $limit
            """
            result = session.run(query, brand=brand, min_price=min_price,
                               max_price=max_price, limit=limit)
            return [dict(record) for record in result]
    
    def filter_by_category_and_price(self, category: str,
                                    min_price: float = 0,
                                    max_price: float = float('inf'),
                                    limit: int = 20) -> List[Dict]:
        """Filter products by category and price range."""
        with self.driver.session() as session:
            query = """
            MATCH (p:Product)-[:BELONGS_TO]->(c:Category {name: $category})
            WHERE p.price >= $min_price AND p.price <= $max_price
            MATCH (p)-[:MANUFACTURED_BY]->(b:Brand)
            RETURN p.id as id, p.name as name, p.price as price,
                   b.name as brand, c.name as category
            ORDER BY p.price ASC
            LIMIT $limit
            """
            result = session.run(query, category=category, min_price=min_price,
                               max_price=max_price, limit=limit)
            return [dict(record) for record in result]
    
    def filter_by_spec(self, spec_name: str, operator: str, 
                      spec_value: str, category: Optional[str] = None,
                      limit: int = 20) -> List[Dict]:
        """
        Filter products by specification constraint.
        
        Args:
            spec_name: Name of spec (e.g., "RAM", "Storage")
            operator: Comparison operator (">", "<", ">=", "<=", "=", "contains")
            spec_value: Value to compare against (e.g., "12GB", "256GB")
            category: Optional category filter
            limit: Max results
        
        Returns:
            List of matching products
        """
        with self.driver.session() as session:
            # Build WHERE clause based on operator
            if operator == "contains":
                where_clause = f"p.`{spec_name}` CONTAINS $spec_value"
            elif operator in [">", "<", ">=", "<=", "="]:
                # Try to extract numeric value for comparison
                where_clause = f"toFloat(p.`{spec_name}`) {operator} toFloat($spec_value)"
            else:
                where_clause = f"p.`{spec_name}` = $spec_value"
            
            if category:
                query = f"""
                MATCH (p:Product)-[:BELONGS_TO]->(c:Category {{name: $category}})
                MATCH (p)-[:MANUFACTURED_BY]->(b:Brand)
                WHERE {where_clause} AND p.`{spec_name}` IS NOT NULL
                RETURN p.id as id, p.name as name, p.price as price,
                       b.name as brand, c.name as category,
                       p.`{spec_name}` as spec_value
                ORDER BY p.price ASC
                LIMIT $limit
                """
            else:
                query = f"""
                MATCH (p:Product)
                MATCH (p)-[:MANUFACTURED_BY]->(b:Brand)
                MATCH (p)-[:BELONGS_TO]->(c:Category)
                WHERE {where_clause} AND p.`{spec_name}` IS NOT NULL
                RETURN p.id as id, p.name as name, p.price as price,
                       b.name as brand, c.name as category,
                       p.`{spec_name}` as spec_value
                ORDER BY p.price ASC
                LIMIT $limit
                """
            
            try:
                result = session.run(query, 
                                   category=category,
                                   spec_value=spec_value,
                                   limit=limit)
                return [dict(record) for record in result]
            except Exception as e:
                print(f"⚠️ Spec filter error: {e}")
                return []
    
    def get_cheapest_by_category(self, category: str, limit: int = 5) -> List[Dict]:
        """Get the cheapest products in a category."""
        return self.filter_by_category_and_price(category, limit=limit)
    
    def get_most_expensive_by_category(self, category: str, limit: int = 5) -> List[Dict]:
        """Get the most expensive products in a category."""
        with self.driver.session() as session:
            query = """
            MATCH (p:Product)-[:BELONGS_TO]->(c:Category {name: $category})
            MATCH (p)-[:MANUFACTURED_BY]->(b:Brand)
            RETURN p.id as id, p.name as name, p.price as price,
                   b.name as brand, c.name as category
            ORDER BY p.price DESC
            LIMIT $limit
            """
            result = session.run(query, category=category, limit=limit)
            return [dict(record) for record in result]
    
    def get_price_range_for_category(self, category: str) -> Tuple[float, float]:
        """Get min and max prices for a category."""
        with self.driver.session() as session:
            query = """
            MATCH (p:Product)-[:BELONGS_TO]->(c:Category {name: $category})
            RETURN min(p.price) as min_price, max(p.price) as max_price
            """
            result = session.run(query, category=category)
            record = result.single()
            if record:
                return (record['min_price'] or 0, record['max_price'] or 0)
            return (0, 0)
    
    def sort_products_by_price(self, products: List[Dict], 
                              ascending: bool = True) -> List[Dict]:
        """Sort a list of products by price."""
        return sorted(products, key=lambda x: x['price'], 
                     reverse=not ascending)
    
    def sort_products_by_rating(self, products: List[Dict],
                               ascending: bool = False) -> List[Dict]:
        """Sort products by rating (highest first by default)."""
        return sorted(products, 
                     key=lambda x: x.get('average_rating', 0),
                     reverse=not ascending)
    
    def apply_multiple_filters(self, brand: Optional[str] = None,
                              category: Optional[str] = None,
                              min_price: float = 0,
                              max_price: float = float('inf'),
                              spec_filters: Optional[List[Dict]] = None,
                              limit: int = 20) -> List[Dict]:
        """
        Apply multiple filters at once including specs.
        
        Args:
            brand: Brand name filter
            category: Category filter
            min_price: Minimum price
            max_price: Maximum price
            spec_filters: List of spec filters like [{"name": "RAM", "operator": ">", "value": "12GB"}]
            limit: Max results
        """
        with self.driver.session() as session:
            # Build dynamic query
            conditions = ["p.price >= $min_price", "p.price <= $max_price"]
            params = {
                'min_price': min_price,
                'max_price': max_price,
                'limit': limit
            }
            
            brand_match = ""
            category_match = ""
            
            if brand:
                brand_match = "-[:MANUFACTURED_BY]->(b:Brand {name: $brand})"
                params['brand'] = brand
            else:
                brand_match = "-[:MANUFACTURED_BY]->(b:Brand)"
            
            if category:
                category_match = "-[:BELONGS_TO]->(c:Category {name: $category})"
                params['category'] = category
            else:
                category_match = "-[:BELONGS_TO]->(c:Category)"
            
            # Add spec filters
            if spec_filters:
                for i, spec_filter in enumerate(spec_filters):
                    spec_name = spec_filter['name']
                    operator = spec_filter['operator']
                    spec_value = spec_filter['value']
                    
                    if operator == "contains":
                        conditions.append(f"p.`{spec_name}` CONTAINS $spec_value_{i}")
                    else:
                        conditions.append(f"toFloat(p.`{spec_name}`) {operator} toFloat($spec_value_{i})")
                    
                    params[f'spec_value_{i}'] = spec_value
            
            query = f"""
            MATCH (p:Product){brand_match}
            MATCH (p){category_match}
            WHERE {' AND '.join(conditions)}
            RETURN p.id as id, p.name as name, p.price as price,
                   b.name as brand, c.name as category
            ORDER BY p.price ASC
            LIMIT $limit
            """
            
            try:
                result = session.run(query, **params)
                return [dict(record) for record in result]
            except Exception as e:
                print(f"⚠️ Multi-filter error: {e}")
                # Fallback to basic filters without specs
                if spec_filters:
                    return self.apply_multiple_filters(brand, category, min_price, max_price, None, limit)
                return []
    
    def close(self):
        """Close the Neo4j connection."""
        self.driver.close()

# Singleton instance
_filter_tools_instance = None

def get_filter_tools() -> FilterTools:
    """Get or create the FilterTools singleton instance."""
    global _filter_tools_instance
    if _filter_tools_instance is None:
        _filter_tools_instance = FilterTools()
    return _filter_tools_instance
