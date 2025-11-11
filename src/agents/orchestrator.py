"""
Orchestrator: Master coordinator agent (COMPLETELY REDESIGNED).
Routes queries to specialist agents with intelligent intent detection.
"""

from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
import uuid

from src.config import Config
from src.agents.graph_agent import GraphAgent
from src.agents.review_agent import ReviewAgent
from src.agents.filter_agent import FilterAgent
from src.agents.compare_agent import CompareAgent

class Orchestrator:
    """
    Master coordinator with enhanced intent detection and response synthesis.
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=Config.OPENAI_API_KEY,
            model=Config.OPENAI_MODEL,
            temperature=0.5
        )
        
        # Initialize specialist agents
        self.graph_agent = GraphAgent()
        self.review_agent = ReviewAgent()
        self.filter_agent = FilterAgent()
        self.compare_agent = CompareAgent()
        
        self.system_prompt = """You are the Orchestrator, the master AI coordinator of an intelligent e-commerce system.

Your role:
- Analyze user queries to understand their true intent
- Route queries to the most appropriate specialist agents
- Coordinate between multiple agents when needed
- Synthesize results into coherent, helpful answers
- Maintain conversation context and flow

Available specialist agents:
1. **Graph Agent** - Product catalog expert (brands, categories, specs, counting queries)
2. **Review Agent** - Customer review and sentiment expert
3. **Filter Agent** - Price and constraint filtering expert
4. **Compare Agent** - Product comparison and recommendation expert

Intelligent routing rules:

**Counting queries → Graph Agent:**
- "How many brands/products/categories..."
- "Count of..."
- "Number of..."

**Comparison queries → Compare Agent:**
- "Compare X and Y"
- "X vs Y"
- "Which is better between..."
- "Difference between..."

**Review/Opinion queries → Review Agent:**
- "What do customers think/say..."
- "Reviews for..."
- "Is X good..."
- "Customer feedback..."
- "How is the quality..."

**Price/Budget queries → Filter Agent:**
- "Under ₹X"
- "Between ₹X and ₹Y"
- "Cheapest..."
- "Budget options..."

**Spec queries → Graph Agent:**
- "Products with >12GB RAM"
- "Laptops with 15 inch display"
- Specification-based filtering

**General queries → Graph Agent:**
- Brand/category browsing
- Product information
- Availability checks

Response synthesis:
- Combine insights from all agents into ONE unified answer
- Never say "Agent X said..." - present unified knowledge
- Always add a natural language summary at the end
- Format with clear structure and bullet points
- Include prices in ₹ (Indian Rupees)
- End with helpful next steps or suggestions
"""
    
    def process(self, user_query: str, session_id: str = None) -> Dict[str, Any]:
        """
        Main orchestration method with intelligent routing.
        
        Args:
            user_query: The user's question
            session_id: Session identifier
        
        Returns:
            Dict with final answer and execution trace
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        execution_trace = {
            "query": user_query,
            "session_id": session_id,
            "steps": [],
            "agents_used": [],
            "final_answer": "",
            "success": False
        }
        
        try:
            # Step 1: Analyze query intent
            execution_trace["steps"].append("🎯 Orchestrator: Analyzing query intent...")
            intent = self._analyze_intent(user_query)
            execution_trace["steps"].append(f"🔍 Detected intent: {intent['type']}")
            
            # Step 2: Route to appropriate agents
            context = {}
            agent_results = self._route_query(user_query, intent, context, execution_trace)
            
            # Step 3: Synthesize final answer
            execution_trace["steps"].append("✨ Orchestrator: Synthesizing final answer...")
            final_answer = self._synthesize_answer(user_query, agent_results, intent)
            
            execution_trace["final_answer"] = final_answer
            execution_trace["success"] = True
            
        except Exception as e:
            execution_trace["steps"].append(f"❌ Error: {str(e)}")
            execution_trace["final_answer"] = (
                "I encountered an error processing your request. "
                "Please try rephrasing your question or ask about specific products, brands, or categories."
            )
            execution_trace["success"] = False
        
        return execution_trace
    
    def _analyze_intent(self, query: str) -> Dict[str, Any]:
        """Enhanced intent analysis with better keyword detection."""
        query_lower = query.lower()
        
        intent = {
            "type": "general",
            "needs_filtering": False,
            "needs_reviews": False,
            "needs_comparison": False,
            "is_counting": False,
            "is_spec_query": False
        }
        
        # Check for comparison (highest priority)
        comparison_keywords = ['compare', 'vs', 'versus', 'difference between', 'which is better', 'or']
        if any(keyword in query_lower for keyword in comparison_keywords):
            intent["needs_comparison"] = True
            intent["type"] = "comparison"
            return intent
        
        # Check for counting queries
        counting_keywords = ['how many', 'count', 'number of', 'total']
        if any(keyword in query_lower for keyword in counting_keywords):
            intent["is_counting"] = True
            intent["type"] = "counting"
            return intent
        
        # Check for spec-based queries
        spec_keywords = ['ram', 'storage', 'display', 'screen', 'battery', 'camera', 'processor', 'gb', 'tb', 'inch']
        spec_operators = ['>', '<', 'more than', 'less than', 'at least', 'above', 'below', 'minimum', 'maximum']
        if (any(keyword in query_lower for keyword in spec_keywords) and 
            any(op in query_lower for op in spec_operators)):
            intent["is_spec_query"] = True
            intent["type"] = "spec_search"
            return intent
        
        # Check for price/budget constraints
        price_keywords = ['under', 'below', 'budget', 'cheap', 'affordable', 'price', 'within', '₹', 'between', 'around']
        if any(word in query_lower for word in price_keywords):
            intent["needs_filtering"] = True
            intent["type"] = "filtered_search"
        
        # Check for review/quality queries (expanded keywords)
        review_keywords = ['review', 'rating', 'good', 'best', 'quality', 'recommend', 'opinion', 
                          'battery', 'camera', 'performance', 'think', 'say', 'customers', 
                          'feedback', 'worth', 'reliable', 'durable']
        if any(word in query_lower for word in review_keywords):
            intent["needs_reviews"] = True
            if intent["type"] == "filtered_search":
                intent["type"] = "complex_search"
            else:
                intent["type"] = "review_search"
        
        return intent
    
    def _route_query(self, query: str, intent: Dict, context: Dict, execution_trace: Dict) -> Dict[str, Any]:
        """Enhanced routing with better agent selection."""
        results = {
            "graph": None,
            "review": None,
            "filter": None,
            "compare": None
        }
        
        # ROUTE 1: Comparison queries
        if intent["type"] == "comparison":
            execution_trace["steps"].append("📊 Orchestrator: Routing to Compare Agent...")
            compare_result = self.compare_agent.process(query, context)
            execution_trace["agents_used"].append("Compare Agent")
            execution_trace["steps"].extend(compare_result["thinking"])
            results["compare"] = compare_result
        
        # ROUTE 2: Counting queries → Graph Agent
        elif intent["type"] == "counting":
            execution_trace["steps"].append("🔢 Orchestrator: Routing to Graph Agent (counting)...")
            graph_result = self.graph_agent.process(query, context)
            execution_trace["agents_used"].append("Graph Agent")
            execution_trace["steps"].extend(graph_result["thinking"])
            results["graph"] = graph_result
        
        # ROUTE 3: Spec queries → Graph Agent
        elif intent["type"] == "spec_search":
            execution_trace["steps"].append("📐 Orchestrator: Routing to Graph Agent (specs)...")
            graph_result = self.graph_agent.process(query, context)
            execution_trace["agents_used"].append("Graph Agent")
            execution_trace["steps"].extend(graph_result["thinking"])
            results["graph"] = graph_result
        
        # ROUTE 4: Review-focused queries
        elif intent["type"] == "review_search":
            execution_trace["steps"].append("⭐ Orchestrator: Routing to Review Agent...")
            review_result = self.review_agent.process(query, context)
            execution_trace["agents_used"].append("Review Agent")
            execution_trace["steps"].extend(review_result["thinking"])
            results["review"] = review_result
        
        # ROUTE 5: Complex search (price + reviews)
        elif intent["type"] == "complex_search":
            # First apply filters
            if intent["needs_filtering"]:
                execution_trace["steps"].append("💰 Orchestrator: Routing to Filter Agent...")
                filter_result = self.filter_agent.process(query, context)
                execution_trace["agents_used"].append("Filter Agent")
                execution_trace["steps"].extend(filter_result["thinking"])
                results["filter"] = filter_result
                
                if filter_result["success"]:
                    context["product_ids"] = [p["id"] for p in filter_result["results"]]
            
            # Then get reviews
            if intent["needs_reviews"]:
                execution_trace["steps"].append("⭐ Orchestrator: Routing to Review Agent...")
                review_result = self.review_agent.process(query, context)
                execution_trace["agents_used"].append("Review Agent")
                execution_trace["steps"].extend(review_result["thinking"])
                results["review"] = review_result
        
        # ROUTE 6: Filtered search (price only)
        elif intent["type"] == "filtered_search":
            execution_trace["steps"].append("💰 Orchestrator: Routing to Filter Agent...")
            filter_result = self.filter_agent.process(query, context)
            execution_trace["agents_used"].append("Filter Agent")
            execution_trace["steps"].extend(filter_result["thinking"])
            results["filter"] = filter_result
        
        # ROUTE 7: General queries → Graph Agent
        else:
            execution_trace["steps"].append("📦 Orchestrator: Routing to Graph Agent...")
            graph_result = self.graph_agent.process(query, context)
            execution_trace["agents_used"].append("Graph Agent")
            execution_trace["steps"].extend(graph_result["thinking"])
            results["graph"] = graph_result
        
        return results
    
    def _synthesize_answer(self, query: str, agent_results: Dict, intent: Dict) -> str:
        """Synthesize final answer with natural language."""
        
        # Priority 1: Comparison results
        if agent_results.get("compare") and agent_results["compare"].get("success"):
            compare_data = agent_results["compare"]
            return self.compare_agent.format_response(
                compare_data["comparison"],
                compare_data["recommendation"]
            )
        
        # Priority 2: Review results
        if agent_results.get("review") and agent_results["review"].get("success"):
            review_data = agent_results["review"]
            return self.review_agent.format_response(review_data["results"])
        
        # Priority 3: Filter results
        if agent_results.get("filter") and agent_results["filter"].get("success"):
            filter_data = agent_results["filter"]
            return self.filter_agent.format_response(
                filter_data["results"],
                filter_data["constraints"]
            )
        
        # Priority 4: Graph results
        if agent_results.get("graph") and agent_results["graph"].get("success"):
            graph_data = agent_results["graph"]
            result_type = graph_data.get("result_type", "products")
            return self.graph_agent.format_response(graph_data["results"], result_type)
        
        # Fallback
        return (
            "I couldn't find any products matching your criteria. Please try:\n"
            "• Expanding your budget\n"
            "• Choosing a different brand\n"
            "• Exploring other categories\n"
            "• Asking about specific products\n\n"
            "💡 Try asking: 'Show me all smartphones' or 'What are the best laptops under ₹1,00,000?'"
        )

# Singleton instance
_orchestrator_instance = None

def get_orchestrator() -> Orchestrator:
    """Get or create the Orchestrator singleton instance."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = Orchestrator()
    return _orchestrator_instance
