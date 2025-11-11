import streamlit as st
from src.tools.memory_tools import get_memory_tools
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def send_feedback_email(rating, feedback_text):
    """Send feedback via email using Gmail SMTP"""
    
    # Email configuration from environment variables
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    receiver_email = os.getenv("RECEIVER_EMAIL")
    

    # Create email content
    subject = "🛒 User Feedback - Intelligent Commerce AI"
    body = f"""
    New Feedback Received!
    
    ⭐ Rating: {rating} stars {"⭐" * rating}
    
    📝 Feedback Message:
    {feedback_text if feedback_text else "(No additional comments)"}
    
    ---
    Sent from Intelligent Commerce AI Chatbot by Aditya 😘
    """
    
    # Create email message
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))
    
    try:
        # Connect to Gmail SMTP server with SSL on port 465
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            # Login to Gmail
            server.login(sender_email, sender_password)
            
            # Send email
            server.sendmail(sender_email, receiver_email, message.as_string())
        
        return True
    except Exception as e:
        print(f"❌ Failed to send feedback email: {e}")
        return False


def render_sidebar():
    memory_tools = get_memory_tools()

    if "current_conversation_id" not in st.session_state:
        all_convs = memory_tools.get_all_conversations()
        if all_convs:
            st.session_state.current_conversation_id = all_convs[0]['id']
        else:
            st.session_state.current_conversation_id = memory_tools.create_new_conversation()

    # Display robot GIF logo at the top
    st.sidebar.image("assets/robot.gif", use_container_width=True)

    st.sidebar.subheader("💬 Chat History")

    # Chat search input
    if "chat_search" not in st.session_state:
        st.session_state.chat_search = ""

    search_term = st.sidebar.text_input("🔍 Search chats", st.session_state.chat_search)
    st.session_state.chat_search = search_term

    # Fetch conversations with search filter
    conversations = memory_tools.get_all_conversations(search_term=search_term)

    # New Chat button
    if st.sidebar.button("➕ New Chat", use_container_width=True):
        new_id = memory_tools.create_new_conversation()
        st.session_state.current_conversation_id = new_id
        st.session_state.messages = []
        st.rerun()

    # Delete All button only if there are chats
    if conversations:
        if st.sidebar.button("🗑️ Delete All Chats", use_container_width=True):
            memory_tools.delete_all_conversations()
            st.session_state.messages = []
            st.session_state.current_conversation_id = None
            st.rerun()

    st.sidebar.markdown("---")

    # Display conversation list
    for conv in conversations:
        cols = st.sidebar.columns([5, 1])
        selected = conv['id'] == st.session_state.get("current_conversation_id")

        chat_label = ("🔵 " if selected else "⚪ ") + conv['title']

        # Chat selection button
        with cols[0]:
            if st.button(chat_label, key=f"conv_{conv['id']}", use_container_width=True):
                st.session_state.current_conversation_id = conv['id']
                st.session_state.messages = memory_tools.get_messages_for_conversation(conv['id'])
                st.rerun()

        # Delete individual chat button
        with cols[1]:
            if st.button("🗑️", key=f"delete_{conv['id']}"):
                memory_tools.delete_conversation(conv['id'])
                # Remove current conversation if it was deleted
                if conv['id'] == st.session_state.get("current_conversation_id"):
                    all_convs = memory_tools.get_all_conversations()
                    if all_convs:
                        st.session_state.current_conversation_id = all_convs[0]['id']
                        st.session_state.messages = memory_tools.get_messages_for_conversation(all_convs[0]['id'])
                    else:
                        st.session_state.current_conversation_id = None
                        st.session_state.messages = []
                st.rerun()

    st.sidebar.markdown("---")

    # Feedback section with email functionality
    st.sidebar.subheader("⭐ Feedback")
    with st.sidebar.form("feedback_form"):
        rating = st.select_slider(
            "Rate your experience:", 
            options=[1, 2, 3, 4, 5], 
            value=5,
            format_func=lambda x: "⭐" * x
        )
        feedback_text = st.text_area(
            "Tell us more (optional):",
            placeholder="What did you like or dislike?",
            max_chars=500
        )
        if st.form_submit_button("📤 Send Feedback"):
            # Send feedback via email
            if send_feedback_email(rating, feedback_text):
                st.success("✅ Thank you for your feedback! Email sent successfully.")
                st.balloons()
            else:
                st.error("⚠️ Failed to send feedback email. Please try again later.")

    st.sidebar.markdown("---")
    st.sidebar.caption("🔧 Powered by: Neo4j, FAISS, LangGraph")
