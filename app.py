import streamlit as st
from src.ui.sidebar import render_sidebar
from src.ui.chat_interface import render_chat_interface
from src.tools.storage import get_storage as get_memory_tools


memory_tools = get_memory_tools()

st.set_page_config(
    page_title="Intelligent Commerce AI",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize conversation state
if "current_conversation_id" not in st.session_state or st.session_state.current_conversation_id is None:
    all_convs = memory_tools.get_all_conversations()
    if all_convs:
        st.session_state.current_conversation_id = all_convs[0]['id']
    else:
        st.session_state.current_conversation_id = memory_tools.create_new_conversation()

# Initialize messages state
if "messages" not in st.session_state or not st.session_state.messages:
    st.session_state.messages = memory_tools.get_messages_for_conversation(st.session_state.current_conversation_id)

def main():
    render_sidebar()
    render_chat_interface()

if __name__ == "__main__":
    main()
