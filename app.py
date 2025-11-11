import streamlit as st

st.set_page_config(
    page_title="Intelligent Commerce AI",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Memory optimization for tokenizers (prevents torch warning)
import os
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

# Use resource cache for memory_tools (this ensures only one instance even if user refreshes)
@st.cache_resource
def get_cached_memory_tools():
    from src.tools.storage import get_storage as get_memory_tools
    return get_memory_tools()

memory_tools = get_cached_memory_tools()

from src.ui.sidebar import render_sidebar
from src.ui.chat_interface import render_chat_interface

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

# yes