"""
Product display components: Product cards and comparison tables.
"""

import streamlit as st
from typing import Dict, List


def render_product_card(product: Dict, show_reviews: bool = False):
    """
    Render a beautiful product card.
    
    Args:
        product: Product dict with name, brand, price, etc.
        show_reviews: Whether to show review summary
    """
    
    with st.container():
        # Product header
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"### {product['name']}")
            st.caption(f"by **{product['brand']}** • {product.get('category', 'N/A')}")
        
        with col2:
            st.markdown(f"### ₹{product['price']:,.2f}")
        
        # Reviews (if available)
        if show_reviews and 'average_rating' in product:
            rating = product['average_rating']
            review_count = product.get('review_count', 0)
            
            # Star rating visualization
            stars = "⭐" * int(rating) + "☆" * (5 - int(rating))
            st.markdown(f"{stars} **{rating:.1f}/5** ({review_count} reviews)")
        
        # Specs (if available)
        if 'specs' in product and product['specs']:
            with st.expander("📋 Specifications"):
                specs = product['specs']
                for key, value in specs.items():
                    if key not in ['id', 'name', 'price']:
                        st.text(f"• {key}: {value}")
        
        st.markdown("---")


def render_product_list(products: List[Dict], title: str = "Products"):
    """
    Render a list of product cards.
    
    Args:
        products: List of product dicts
        title: Section title
    """
    
    st.subheader(f"📦 {title}")
    
    if not products:
        st.info("No products found matching your criteria.")
        return
    
    for product in products:
        render_product_card(product, show_reviews=True)
