import asyncio
import json
import socketio
import sys
from pprint import pprint

# Import all utils functions
from bot.utils import (
    send_message,
    send_typing,
    get_latest_messages,
    parse_message_content,
    get_message_context,
    get_response_from_model_sync
)
from bot.env import WEBUI_URL, TOKEN, OPENWEBUI_API_KEY

# You can set these variables for testing
TEST_CHANNEL_ID = "52fbc987-8e63-4849-a9c4-c6d0bf670ab2"  # Replace with an actual channel ID for testing
TEST_BOT_ID = "your_bot_id"  # Optional: Replace with your bot's user ID
TEST_MESSAGE = "This is a test message from the utility test script"
TEST_MODEL_ID = "your_model_id"  # Replace with an actual model ID for testing

class OpenWebUIAPIClient:
    """Mock API client for testing get_response_from_model_sync"""
    def get_chat_completion_with_messages(self, model_id, messages):
        # This is a mock implementation - replace with actual implementation when available
        print(f"Calling model {model_id} with messages:")
        pprint(messages)
        
        class MockChoice:
            class MockMessage:
                content = "This is a mock response from the model"
            message = MockMessage()
        
        class MockResult:
            choices = [MockChoice()]
            
        return MockResult()

async def test_send_message():
    """Test sending a message to a channel"""
    print("\n=== Testing send_message ===")
    try:
        if not TEST_CHANNEL_ID or TEST_CHANNEL_ID == "your_test_channel_id":
            print("⚠️ Skipping: Please set TEST_CHANNEL_ID to a valid channel ID")
            return

        print(f"Sending message to channel {TEST_CHANNEL_ID}: {TEST_MESSAGE}")
        result = await send_message(TEST_CHANNEL_ID, TEST_MESSAGE)
        print("Result:")
        pprint(result)
        print("✅ send_message test completed")
    except Exception as e:
        print(f"❌ Error in send_message: {e}")

async def test_send_typing():
    """Test sending typing indicator"""
    print("\n=== Testing send_typing ===")
    try:
        if not TEST_CHANNEL_ID or TEST_CHANNEL_ID == "your_test_channel_id":
            print("⚠️ Skipping: Please set TEST_CHANNEL_ID to a valid channel ID")
            return
            
        # Create a socketio client
        sio = socketio.AsyncClient()
        
        print(f"Connecting to {WEBUI_URL}...")
        await sio.connect(WEBUI_URL, headers={"Authorization": f"Bearer {TOKEN}"})
        print("Connected")
        
        print(f"Sending typing indicator to channel {TEST_CHANNEL_ID}")
        await send_typing(sio, TEST_CHANNEL_ID)
        print("Typing indicator sent")
        
        # Wait a moment and disconnect
        await asyncio.sleep(2)
        await sio.disconnect()
        print("✅ send_typing test completed")
    except Exception as e:
        print(f"❌ Error in send_typing: {e}")

async def test_get_latest_messages():
    """Test getting latest messages from a channel"""
    print("\n=== Testing get_latest_messages ===")
    try:
        if not TEST_CHANNEL_ID or TEST_CHANNEL_ID == "your_test_channel_id":
            print("⚠️ Skipping: Please set TEST_CHANNEL_ID to a valid channel ID")
            return
            
        print(f"Getting latest messages from channel {TEST_CHANNEL_ID}")
        messages = await get_latest_messages(TEST_CHANNEL_ID, bot_id=TEST_BOT_ID)
        print(f"Retrieved {len(messages)} messages")
        print("First few messages:")
        for i, msg in enumerate(messages[:3]):
            print(f"\nMessage {i+1}:")
            print(f"Role: {msg['role']}")
            # Pretty print the JSON content
            try:
                content = json.loads(msg['content'])
                print("Content:")
                pprint(content)
            except:
                print(f"Content: {msg['content']}")
            
        print("✅ get_latest_messages test completed")
    except Exception as e:
        print(f"❌ Error in get_latest_messages: {e}")

def test_parse_message_content():
    """Test parsing message content"""
    print("\n=== Testing parse_message_content ===")
    try:
        # Test case 1: Regular text content
        message1 = {"role": "user", "content": "Hello world"}
        result1 = parse_message_content(message1)
        print(f"Test case 1 (plain text):")
        print(f"Input: {message1}")
        print(f"Result: {result1}")
        
        # Test case 2: JSON string content
        json_content = json.dumps({
            "user": {"id": "user123", "name": "Test User"},
            "message": "This is a test message",
            "reactions": []
        })
        message2 = {"role": "user", "content": json_content}
        result2 = parse_message_content(message2)
        print(f"\nTest case 2 (JSON content):")
        print(f"Input: content is a JSON string")
        print(f"Result: {result2}")
        
        # Test case 3: Malformed JSON
        message3 = {"role": "user", "content": "{This is not valid JSON}"}
        result3 = parse_message_content(message3)
        print(f"\nTest case 3 (invalid JSON):")
        print(f"Input: {message3}")
        print(f"Result: {result3}")
        
        print("✅ parse_message_content test completed")
    except Exception as e:
        print(f"❌ Error in parse_message_content: {e}")

def test_get_message_context():
    """Test getting message context"""
    print("\n=== Testing get_message_context ===")
    try:
        # Create sample messages with different formats
        messages = [
            {"role": "system", "content": "System message"},
            {"role": "user", "content": "Plain text message"},
            {"role": "assistant", "content": json.dumps({
                "message": "JSON formatted message",
                "user": {"id": "bot123", "name": "Bot"}
            })},
            {"role": "user", "content": "Another plain message"}
        ]
        
        # Test with different parameters
        print("Test case 1: Get all except system messages")
        result1 = get_message_context(messages)
        print("Result:")
        pprint(result1)
        
        print("\nTest case 2: Include system messages")
        result2 = get_message_context(messages, exclude_system=False)
        print("Result:")
        pprint(result2)
        
        print("\nTest case 3: Get only last 2 messages")
        result3 = get_message_context(messages, last_n=2)
        print("Result:")
        pprint(result3)
        
        print("✅ get_message_context test completed")
    except Exception as e:
        print(f"❌ Error in get_message_context: {e}")

async def test_get_response_from_model_sync():
    """Test getting response from model synchronously"""
    print("\n=== Testing get_response_from_model_sync ===")
    try:
        if not TEST_MODEL_ID or TEST_MODEL_ID == "your_model_id":
            print("⚠️ Skipping: Please set TEST_MODEL_ID to a valid model ID")
            return
            
        # Create mock API client
        api_client = OpenWebUIAPIClient()
        
        # Test messages
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Tell me about OpenWebUI."}
        ]
        
        print(f"Getting response from model {TEST_MODEL_ID}")
        response = await get_response_from_model_sync(api_client, TEST_MODEL_ID, messages)
        
        print(f"Response: {response}")
        print("✅ get_response_from_model_sync test completed")
    except Exception as e:
        print(f"❌ Error in get_response_from_model_sync: {e}")

async def run_all_tests():
    """Run all utility tests"""
    print("=" * 50)
    print("STARTING OPENWEBUI UTILS TESTS")
    print(f"API URL: {WEBUI_URL}")
    print("=" * 50)
    
    # Run individual tests
    await test_send_message()
    await test_send_typing()
    await test_get_latest_messages()
    test_parse_message_content()
    test_get_message_context()
    await test_get_response_from_model_sync()
    
    print("\n" + "=" * 50)
    print("ALL TESTS COMPLETED")
    print("=" * 50)

if __name__ == "__main__":
    # Check configuration
    if not WEBUI_URL or not TOKEN:
        print("Error: Missing required environment variables WEBUI_URL and TOKEN")
        print("Please set these variables in your .env file")
        sys.exit(1)
        
    # Parse command line arguments to run specific tests
    if len(sys.argv) > 1:
        tests_to_run = sys.argv[1:]
        async def run_selected_tests():
            for test_name in tests_to_run:
                if test_name == "send_message":
                    await test_send_message()
                elif test_name == "send_typing":
                    await test_send_typing()
                elif test_name == "get_latest_messages":
                    await test_get_latest_messages()
                elif test_name == "parse_message_content":
                    test_parse_message_content()
                elif test_name == "get_message_context":
                    test_get_message_context()
                elif test_name == "get_response_from_model_sync":
                    await test_get_response_from_model_sync()
                else:
                    print(f"Unknown test: {test_name}")
        
        asyncio.run(run_selected_tests())
    else:
        # Run all tests
        asyncio.run(run_all_tests())
