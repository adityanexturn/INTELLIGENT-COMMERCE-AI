"""
Firebase Tools: Persistent storage for chat history.
"""

import firebase_admin
from firebase_admin import credentials, db
from typing import List, Dict
import time
import json

from src.config import Config

class FirebaseTools:
    def __init__(self):
        # Initialize Firebase (only once)
        if not firebase_admin._apps:
            cred = credentials.Certificate(json.loads(Config.FIREBASE_SERVICE_ACCOUNT_JSON))
            firebase_admin.initialize_app(cred, {'databaseURL': Config.FIREBASE_URL})
    
    def get_all_conversations(self, search_term: str = "") -> List[Dict]:
        """Get all conversations, optionally filtered by search term."""
        ref = db.reference('/conversations')
        conversations = ref.get()
        
        if not conversations:
            return []
        
        # Convert dict to list and sort by last_updated
        conv_list = []
        for conv_id, conv_data in conversations.items():
            conv_data['id'] = conv_id  # Add ID to the data
            conv_list.append(conv_data)
        
        conv_list.sort(key=lambda x: x.get('last_updated', 0), reverse=True)
        
        if search_term:
            return [c for c in conv_list if search_term.lower() in c.get('title', '').lower()]
        
        return conv_list
    
    def create_new_conversation(self) -> str:
        """Create a new conversation and return its ID."""
        ref = db.reference('/conversations')
        new_conv = ref.push({
            'title': 'New Chat',
            'created_at': time.time(),
            'last_updated': time.time()
        })
        return new_conv.key
    
    def get_messages_for_conversation(self, conversation_id: str) -> List[Dict]:
        """Get all messages for a specific conversation."""
        ref = db.reference(f'/messages/{conversation_id}')
        messages = ref.get()
        
        if not messages:
            return []
        
        # Convert to list and sort by timestamp
        msg_list = []
        for msg_id, msg_data in messages.items():
            msg_list.append(msg_data)
        
        msg_list.sort(key=lambda x: x.get('timestamp', 0))
        return msg_list
    
    def save_message(self, conversation_id: str, role: str, content: str):
        """Save a message to a conversation."""
        msg_ref = db.reference(f'/messages/{conversation_id}')
        msg_ref.push({
            'role': role,
            'content': content,
            'timestamp': time.time()
        })
        
        # Update conversation timestamp
        conv_ref = db.reference(f'/conversations/{conversation_id}')
        conv_ref.update({'last_updated': time.time()})
    
    def update_conversation_title(self, conversation_id: str, new_title: str):
        """Update the title of a conversation."""
        ref = db.reference(f'/conversations/{conversation_id}')
        ref.update({'title': new_title})
    
    def delete_conversation(self, conversation_id: str):
        """Delete a conversation and its messages."""
        conv_ref = db.reference(f'/conversations/{conversation_id}')
        msg_ref = db.reference(f'/messages/{conversation_id}')
        
        conv_ref.delete()
        msg_ref.delete()
    
    def delete_all_conversations(self):
        """Delete all conversations and messages."""
        conv_ref = db.reference('/conversations')
        msg_ref = db.reference('/messages')
        
        conv_ref.delete()
        msg_ref.delete()

# Singleton
_firebase_tools_instance = None

def get_firebase_tools() -> FirebaseTools:
    """Get or create the FirebaseTools singleton instance."""
    global _firebase_tools_instance
    if _firebase_tools_instance is None:
        _firebase_tools_instance = FirebaseTools()
    return _firebase_tools_instance
