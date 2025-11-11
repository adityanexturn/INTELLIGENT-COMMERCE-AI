from src.config import Config

driver = Config.get_neo4j_driver()

with driver.session() as session:
    # Count nodes
    print("=== DATABASE OVERVIEW ===\n")
    
    result = session.run("""
        MATCH (p:Product) RETURN count(p) as count
    """)
    print(f"Products: {result.single()['count']}")
    
    result = session.run("""
        MATCH (b:Brand) RETURN count(b) as count
    """)
    print(f"Brands: {result.single()['count']}")
    
    result = session.run("""
        MATCH (c:Category) RETURN count(c) as count
    """)
    print(f"Categories: {result.single()['count']}")
    
    result = session.run("""
        MATCH (r:Review) RETURN count(r) as count
    """)
    print(f"Reviews: {result.single()['count']}")
    
    # Sample products
    print("\n=== SAMPLE PRODUCTS ===\n")
    result = session.run("""
        MATCH (p:Product)-[:MANUFACTURED_BY]->(b:Brand)
        MATCH (p)-[:BELONGS_TO]->(c:Category)
        OPTIONAL MATCH (p)-[:HAS_REVIEW]->(r:Review)
        RETURN p.name, p.price, b.name as brand, c.name as category, count(r) as reviews
        ORDER BY p.price DESC
        LIMIT 10
    """)
    
    for record in result:
        print(f"• {record['p.name']}")
        print(f"  Brand: {record['brand']} | Category: {record['category']}")
        print(f"  Price: ₹{record['p.price']:.2f} | Reviews: {record['reviews']}")
        print()

driver.close()
