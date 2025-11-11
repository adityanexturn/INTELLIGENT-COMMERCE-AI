"""Quick test to verify Firebase is working"""
from src.tools.firebase_tools import get_firebase_tools

# Test Firebase
firebase = get_firebase_tools()

# Create a test conversation
print("Creating test conversation...")
conv_id = firebase.create_new_conversation()
print(f"✓ Created conversation: {conv_id}")

# Save a test message
print("Saving test message...")
firebase.save_message(conv_id, "user", "Hello Firebase!")
print("✓ Message saved")

# Retrieve messages
print("Retrieving messages...")
messages = firebase.get_messages_for_conversation(conv_id)
print(f"✓ Retrieved {len(messages)} message(s)")
print(f"  Message: {messages[0]['content']}")

# Get all conversations
print("\nGetting all conversations...")
convs = firebase.get_all_conversations()
print(f"✓ Found {len(convs)} conversation(s)")

# Clean up
print("\nDeleting test conversation...")
firebase.delete_conversation(conv_id)
print("✓ Test complete!")
