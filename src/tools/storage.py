"""
Storage Selector: Tries SQLite/Turso first, falls back to Firebase.
Drop-in replacement for memory_tools with zero breaking changes.
"""

from typing import List, Dict

class Storage:
    def __init__(self):
        # Try to import existing memory tools
        try:
            from src.tools.memory_tools import get_memory_tools
            self.primary = get_memory_tools()
            self.has_primary = True
        except Exception:
            self.has_primary = False
        
        # Always have Firebase as fallback
        from src.tools.firebase_tools import get_firebase_tools
        self.fallback = get_firebase_tools()
    
    def get_all_conversations(self, search_term: str = "") -> List[Dict]:
        if self.has_primary:
            try:
                return self.primary.get_all_conversations(search_term)
            except Exception:
                pass
        return self.fallback.get_all_conversations(search_term)
    
    def create_new_conversation(self) -> str:
        if self.has_primary:
            try:
                return self.primary.create_new_conversation()
            except Exception:
                pass
        return self.fallback.create_new_conversation()
    
    def get_messages_for_conversation(self, conversation_id: str) -> List[Dict]:
        if self.has_primary:
            try:
                return self.primary.get_messages_for_conversation(conversation_id)
            except Exception:
                pass
        return self.fallback.get_messages_for_conversation(conversation_id)
    
    def save_message(self, conversation_id: str, role: str, content: str):
        if self.has_primary:
            try:
                self.primary.save_message(conversation_id, role, content)
                return
            except Exception:
                pass
        self.fallback.save_message(conversation_id, role, content)
    
    def update_conversation_title(self, conversation_id: str, new_title: str):
        if self.has_primary:
            try:
                self.primary.update_conversation_title(conversation_id, new_title)
                return
            except Exception:
                pass
        self.fallback.update_conversation_title(conversation_id, new_title)
    
    def delete_conversation(self, conversation_id: str):
        if self.has_primary:
            try:
                self.primary.delete_conversation(conversation_id)
                return
            except Exception:
                pass
        self.fallback.delete_conversation(conversation_id)
    
    def delete_all_conversations(self):
        if self.has_primary:
            try:
                self.primary.delete_all_conversations()
                return
            except Exception:
                pass
        self.fallback.delete_all_conversations()

# Singleton
_storage_instance = None

def get_storage() -> Storage:
    """Get or create the Storage singleton instance."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = Storage()
    return _storage_instance
