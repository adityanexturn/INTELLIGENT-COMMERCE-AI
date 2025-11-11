"""
Main chat interface for Intelligent Commerce AI with persistent chat history.
"""

import streamlit as st
from src.agents.orchestrator import get_orchestrator
from src.tools.memory_tools import get_memory_tools
import uuid


def render_chat_interface():
    """Render the main chat interface with persistent storage."""
    
    memory_tools = get_memory_tools()
    current_conv_id = st.session_state.get("current_conversation_id")
    
    # Load messages from persistent storage for current conversation if not loaded
    if "messages" not in st.session_state or not st.session_state.messages:
        if current_conv_id:
            st.session_state.messages = memory_tools.get_messages_for_conversation(current_conv_id)
        else:
            st.session_state.messages = []

    # Initialize other session state variables as needed
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if 'response_count' not in st.session_state:
        st.session_state.response_count = 0
    if 'thinking_steps' not in st.session_state:
        st.session_state.thinking_steps = {}

    # Custom CSS for centered title with gradient and sample questions
    st.markdown("""
        <style>
        .main-title {
            text-align: center;
            font-size: 3.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 50%, #60a5fa 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem;
            letter-spacing: 2px;
            margin-top: -1rem;
        }
        .sub-title {
            text-align: center;
            font-size: 1.1rem;
            color: #94a3b8;
            margin-bottom: 2rem;
        }
        </style>
    """, unsafe_allow_html=True)

    # Centered Title with gradient - ALL CAPS
    st.markdown('<div class="main-title">🛒 INTELLIGENT COMMERCE AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Powered by Multi-Agent System | Ask me anything about products!</div>', unsafe_allow_html=True)

    # Sample questions (only show when chat is empty)
    if not st.session_state.messages:
        st.markdown("### 💡 Try these questions:")
        
        col1, col2 = st.columns(2)
        
        sample_questions = [
            {
                "question": "What are the specifications of Apple MacBook Air M2?",
                "agent": "🔍 Graph Agent",
                "icon": "💻"
            },
            {
                "question": "Show me all Samsung products available",
                "agent": "🎯 Filter Agent",
                "icon": "📱"
            },
            {
                "question": "Compare Sony WH-1000XM5 and Bose QuietComfort 45",
                "agent": "⚖️ Compare Agent",
                "icon": "🎧"
            },
            {
                "question": "What do customers say about Dell XPS 15?",
                "agent": "⭐ Review Agent",
                "icon": "💬"
            },
            {
                "question": "Find me gaming laptops under ₹2,00,000",
                "agent": "🎯 Filter Agent",
                "icon": "🎮"
            }
        ]
        
        for idx, q in enumerate(sample_questions):
            col = col1 if idx % 2 == 0 else col2
            with col:
                if st.button(
                    f"{q['icon']} {q['question']}",
                    key=f"sample_q_{idx}",
                    use_container_width=True,
                    help=f"Powered by {q['agent']}"
                ):
                    # Set the question as user input and process
                    st.session_state.selected_question = q['question']
                    st.rerun()
        
        st.markdown("---")

    # Handle sample question selection
    if "selected_question" in st.session_state:
        prompt = st.session_state.selected_question
        del st.session_state.selected_question
        process_user_query(prompt, current_conv_id, memory_tools)

    # Display chat history from memory
    for idx, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            # Show thinking process if assistant message
            if message["role"] == "assistant" and idx in st.session_state.thinking_steps:
                with st.expander("🧠 Show Thinking Process"):
                    steps = st.session_state.thinking_steps[idx]
                    for step in steps["steps"]:
                        st.text(step)
                    st.info(f"Agents used: {', '.join(steps['agents_used'])}")

    # Chat input
    if prompt := st.chat_input("Ask about products, compare items, or find deals..."):
        process_user_query(prompt, current_conv_id, memory_tools)

    # Feedback prompt shown once per session after 2 responses
    if st.session_state.get('show_feedback', False):
        st.info("⭐ How was your experience? Share feedback in the sidebar!")
        st.session_state.show_feedback = False  # Only show once


def process_user_query(prompt, current_conv_id, memory_tools):
    """Process user query and generate response"""
    
    # Save user message persistently
    if current_conv_id:
        memory_tools.save_message(current_conv_id, "user", prompt)

    # Append user message to session state
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    # Update conversation title if still default or empty
    conversations = memory_tools.get_all_conversations()
    conv = next((c for c in conversations if c['id'] == current_conv_id), None)
    if conv and (conv['title'] == "New Chat" or not conv['title']):
        new_title = prompt[:50].strip() or "New Chat"
        memory_tools.update_conversation_title(current_conv_id, new_title)

    # Display user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)

    # Process user query with orchestrator
    with st.chat_message("assistant"):
        with st.spinner("🤔 Thinking..."):
            orchestrator = get_orchestrator()
            result = orchestrator.process(prompt, st.session_state.session_id)
            answer = result["final_answer"]

            # Display assistant answer
            st.markdown(answer)

            # Store thinking steps for display
            message_idx = len(st.session_state.messages)
            st.session_state.thinking_steps[message_idx] = {
                "steps": result["steps"],
                "agents_used": result["agents_used"]
            }

            # Show thinking process expander
            with st.expander("🧠 Show Thinking Process"):
                for step in result["steps"]:
                    st.text(step)
                st.info(f"Agents used: {', '.join(result['agents_used'])}")

    # Append assistant message to session state and persist
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })
    if current_conv_id:
        memory_tools.save_message(current_conv_id, "assistant", answer)

    # Increment response count and show feedback prompt after 2 responses
    st.session_state.response_count += 1
    if st.session_state.response_count == 2:
        st.session_state.show_feedback = True

    # Rerun to refresh UI with new messages
    st.rerun()
