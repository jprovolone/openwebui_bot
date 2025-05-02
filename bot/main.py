import asyncio
import socketio
import os
import pprint
import logging

from bot.env import WEBUI_URL, TOKEN, LOG_LEVEL

def get_log_level(level_str: str) -> int:
    """Convert string log level to logging constant."""
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    return level_map.get(level_str.upper(), logging.INFO)

# Configure logging
logging.basicConfig(
    level=get_log_level(LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

from openwebui_python import OpenWebUI
from bot.models.data import Event, User, Data, MessageData, ChannelAccessControl, AccessControl, Channel, TypingData
from bot.utils import send_message, send_typing, get_response_from_model_sync, get_latest_messages, filter_conversation_by_tokens
from bot.commands.command_handler import CommandHandler
from bot.personalities import Personalities

# Create an asynchronous Socket.IO client instance
sio = socketio.AsyncClient(logger=False, engineio_logger=False)

api = OpenWebUI(os.getenv('BASE_URL'),os.getenv('OPENWEBUI_API_KEY'))

messages = {}
commands = CommandHandler(messages, api, "openai/gpt-4.1", "openai/gpt-4.1-nano")
toaster_prompt = Personalities.get_personality_prompt("default")

# Message format documentation
"""
IMPORTANT - READ CAREFULLY:
    Messages will be provided in this format:
    {
        "role": "user",
        "content": {
            "user": {
                "id": "user-uuid",
                "name": "Username"
            },
            "message": "The actual message",
            "reactions": [
                {
                    "name": "melting_face",
                    "count": 1,
                    "users": ["Username1", "Username2"]
                }
            ]
        }
    }
    
    YOU MUST RESPOND IN JSON FORMAT WITH EITHER A "message" OR "response" FIELD:
    CORRECT RESPONSE EXAMPLES:
    {"message": "I noticed that melting face reaction. That's pretty funny!"}
    {"response": "Interesting point you've got there. What else?"}
    
    Be conversational and authentic - like a real person who can be:
    - Occasionally witty or sarcastic
    - Sometimes straightforward and helpful
    - Willing to reference reactions when relevant
    
    Keep responses concise and natural. No corporate speak or unnecessary formality.
    Think of yourself as a helpful friend who doesn't waste time with fluff.
"""

# Event handlers
@sio.event
async def connect():
    logger.info("Connected to WebSocket server")


@sio.event
async def disconnect():
    logger.info("Disconnected from WebSocket server")

def sanitize_name(name: str) -> str:
    """
    Converts a given name to a valid format by replacing invalid characters with underscores.
    """
    # Replace invalid characters with underscores
    return ''.join(c if c.isalnum() or c in "-_" else '_' for c in name)

async def decide_response_from_model(api, model_id: str, full_context):
    # Modify names in the full context to ensure they match required patterns
    for message in full_context:
        if 'name' in message:
            message['name'] = sanitize_name(message['name'])
    # Prepare a system message to instruct the model for decision making
    system_instruction = {
        "role": "system",
        "content": (
            "⚠️ CRITICAL INSTRUCTION - RESPOND ONLY WITH 'yes' OR 'no' ⚠️\r\n\r\n" +
            "ANSWER 'yes' IF ANY OF THESE ARE TRUE:\r\n" +
            "• Someone mentions your name (Toaster, Toast) directly or indirectly\r\n" +
            "• Someone asks you a question (containing a question mark or implied question)\r\n" +
            "• Someone uses 'you' or 'your' when clearly referring to you\r\n" +
            "• Someone requests information or assistance that you can provide\r\n" +
            "• Someone is continuing an active conversation with you\r\n" +
            "• Someone gives you a command or instruction\r\n\r\n" +
            "ANSWER 'no' ONLY IF ALL OF THESE ARE TRUE:\r\n" +
            "• The message is explicitly directed at someone else by name\r\n" +
            "• The message contains no questions or requests\r\n" +
            "• The message is purely informational or a system notification\r\n" +
            "• There is clear evidence the speaker does not expect your response\r\n\r\n" +
            "IMPORTANT: When someone asks 'What have you been up to?' or similar personal questions, always answer 'yes' as these are directed at you.\r\n\r\n" +
            "IF THERE IS ANY DOUBT OR UNCERTAINTY, ANSWER 'yes'.\r\n\r\n" +
            "With these instructions in mind, answer the following question: Based on the chat context provided, should you respond?\r\n" +
            f"Context:\r\n{full_context}"
        )
    }
    

    # Call the model with the decision context
    decision_response = await get_response_from_model_sync(api, model_id, [system_instruction])
    
    decision_response = decision_response.strip()
    if 'yes' in decision_response.lower():
        return True
    elif 'no' in decision_response.lower():
        return False
    else:
        # If the response is neither 'yes' nor 'no', return the text
        return decision_response




async def get_response(api, model_id: str, full_context):
    # Modify names in the full context to ensure they match required patterns
    for message in full_context:
        if 'name' in message:
            message['name'] = sanitize_name(message['name'])

    return await get_response_from_model_sync(api, model_id, full_context)

# Define a function to handle channel events
def events(user_id, api):
    @sio.on("channel-events")
    async def channel_events(raw_data):
        user_data = raw_data["user"]
        data_info = raw_data["data"]
        user = User(**user_data)
        data_type = data_info["type"]
        channel_id = raw_data["channel_id"]

        if data_type == "message":
            message_data = data_info["data"]
            message_user_data = message_data.pop("user")
            message_user = User(**message_user_data)
            message = MessageData(user=message_user, **message_data)
            data = Data(type=data_type, data=message)

            if user.id != user_id:
                message_content = data.data.content
                logger.info(f"Received message from {user.name} in channel {channel_id}")

                # Check if message is a command (starts with $)
                if message_content.startswith('$'):
                    command_response = await commands.handle_command(message_content, channel_id)
                    if command_response:
                        await send_message(channel_id, command_response)
                        return

                # Initialize or update messages for the channel

                # Get initial message history
                logger.debug(f"Fetching message history for channel {channel_id}")
                messages[channel_id] = await get_latest_messages(channel_id, user_id, message.id)

                # Create conversation with system prompt
                conversation = [{
                    "role": "system",
                    "content": toaster_prompt
                }]
                
                # Add messages from API response to conversation
                conversation.extend(messages[channel_id])

                conversation = filter_conversation_by_tokens(conversation)

                # Determine if the AI should respond
                logger.debug(f"Deciding whether to respond in channel {channel_id}")
                should_respond = await decide_response_from_model(api, commands.decision_model_id, conversation)

                if isinstance(should_respond, bool):
                    if should_respond:
                        logger.info(f"Preparing to respond in channel {channel_id}")
                        # Prepare to send typing indicator and delay
                        await send_typing(sio, channel_id)

                        # Get the actual response using current model from commands
                        logger.debug(f"Generating response from model: {commands.model_id}")
                        response = await get_response(api, commands.model_id, conversation)

                        # Log the assistant's message
                        logger.info(f"Sending response in channel {channel_id}")

                        # Try to parse as JSON first
                        try:
                            import json
                            response_data = json.loads(response)
                            # Handle different JSON response formats
                            if isinstance(response_data, dict):
                                # Check for content.message format (like the example format)
                                if "content" in response_data and isinstance(response_data["content"], dict):
                                    message_content = response_data["content"].get("message", "")
                                # Check for direct message field
                                elif "message" in response_data:
                                    message_content = response_data["message"]
                                # Check for content field
                                elif "content" in response_data:
                                    message_content = response_data["content"]
                                else:
                                    # If no recognized fields, use the raw response
                                    message_content = response
                            else:
                                message_content = response
                            
                            # If we extracted an empty message, fall back to raw response
                            if not message_content:
                                message_content = response
                                
                            await send_message(channel_id, message_content)
                            logger.debug(f"Response sent successfully to channel {channel_id}")
                        except json.JSONDecodeError:
                            # If it's not valid JSON, use the raw response
                            await send_message(channel_id, response)
                            logger.debug(f"Using raw response for channel {channel_id}")
                elif isinstance(should_respond, str):
                    # Prepare to send typing indicator and delay
                    await send_typing(sio, channel_id)
                    await asyncio.sleep(1)  # Simulate a delay
                    await send_message(channel_id, should_respond)
                    logger.debug(f"Response sent successfully to channel {channel_id}")

        elif data_type == "typing":
            typing_data = data_info["data"]
            typing = TypingData(**typing_data)
            data = Data(type=data_type, data=typing)
            # if user.id != user_id and data.data.typing:
            #     logger.debug(f"User {user.name} is typing in channel {channel_id}")


# Define an async function for the main workflow
async def main():
    try:
        logger.info(f"Attempting to connect to {WEBUI_URL}")
        await sio.connect(
            WEBUI_URL, socketio_path="/ws/socket.io", transports=["websocket"]
        )
        logger.info("Connection established successfully")
        
        logger.debug("Available models:")
        for model in api.get_models():
            logger.debug(f"- {model.id}")
            

    except Exception as e:
        logger.error(f"Failed to connect: {str(e)}", exc_info=True)
        return

    # Callback function for user-join
    async def join_callback(data=None):
        if data:
            logger.info(f"User joined with ID: {data['id']}")
            events(data["id"], api)  # Attach the event handlers dynamically
        else:
            logger.warning("Join callback called without data")

    # Authenticate with the server
    logger.info("Authenticating with server...")
    await sio.emit("user-join", {"auth": {"token": TOKEN}}, callback=join_callback)

    # Wait indefinitely to keep the connection open
    await sio.wait()

if __name__ == "__main__":
    asyncio.run(main())
