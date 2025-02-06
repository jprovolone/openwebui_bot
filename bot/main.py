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
from bot.utils import send_message, send_typing, get_response_from_model_sync, get_latest_messages
from bot.commands.command_handler import CommandHandler

# Create an asynchronous Socket.IO client instance
sio = socketio.AsyncClient(logger=False, engineio_logger=False)

api = OpenWebUI(os.getenv('BASE_URL'),os.getenv('OPENWEBUI_API_KEY'))

messages = {}
commands = CommandHandler(messages, api, "anthropic/claude-3.5-sonnet:beta", "x-ai/grok-beta")

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
        "role": "user", # testing if lower parameter models do better with this role
        "content": (
            "⚠️ CRITICAL INSTRUCTION - RESPOND ONLY WITH 'yes' OR 'no' ⚠️\r\n\r\n" +
            "YOU MUST ANSWER 'yes' IF ANY OF THESE ARE TRUE:\r\n" +
            "• Someone uses ANY variation of your name (Toaster, Toast, AI, bot)\r\n" +
            "• Someone uses ANY pronouns referring to you (it, you, they)\r\n" +
            "• Someone asks ANY question to the group\r\n" +
            "• Someone mentions artificial intelligence or AI\r\n" +
            "• Someone uses commands or requests (help, can someone, etc)\r\n" +
            "• Someone expresses need for assistance\r\n" +
            "• Someone references technology or automation\r\n" +
            "• ANY direct question mark (?) is used\r\n" +
            "• WHEN IN DOUBT, ANSWER 'yes'\r\n\r\n" +
            "ONLY ANSWER 'no' IF:\r\n" +
            "• Message is clearly marked for someone else\r\n" +
            "• System notifications/automated messages\r\n" +
            "• Pure human-to-human conversation with no questions\r\n\r\n" +
            "DEFAULT TO 'yes' IF UNCERTAIN\r\n\r\n" +
            "Based on the chat context provided, should you respond?"
        )
    }
    # Prepend the system instruction to the context
    decision_context = [system_instruction] + full_context + [system_instruction]
    
    # Call the model with the decision context
    decision_response = await get_response_from_model_sync(api, model_id, decision_context)
    
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

                # Initialize messages dictionary for new channels
                if channel_id not in messages:
                    messages[channel_id] = []
                
                # Get the latest messages from the channel
                logger.debug(f"Fetching message history for channel {channel_id}")
                message_history = await get_latest_messages(channel_id)
                
                # Update messages dictionary with current message
                messages[channel_id] = message_history
                
                # Convert API messages to the format expected by the model
                conversation = [{
                    "role": "system",
                    "content": """
                    You are Toaster, a straight-shooting AI who:
                    - Keeps responses under 2-3 sentences
                    - Uses casual but direct language
                    - Doesn't sugarcoat anything
                    - Swears naturally when appropriate
                    - Calls out BS immediately
                    - Provides quick, practical solutions
                    - Addresses user as "human" or "dude"
                    - Uses sarcasm and dry humor
                    - Stays real without being unnecessarily mean
                    - Gets straight to the point

                    No corporate speak, no fluff, no long explanations. Just honest, unfiltered answers 
                    delivered efficiently. Think of a competent friend who's good at solving problems but 
                    doesn't waste time with pleasantries.
                    """
                }]
                
                # Add messages from API response to conversation
                for msg in message_history:
                    msg_user = msg.get('user', {})
                    conversation.append({
                        "role": "user" if msg_user.get('id') != user_id else "assistant",
                        "name": msg_user.get('name', 'unknown'),
                        "content": msg.get('content', '')
                    })

                # Add the current message
                conversation.append({
                    "role": "user",
                    "name": user.name,
                    "content": data.data.content
                })
                logger.debug(f"Retrieved conversation - {conversation}")
                # Determine if the AI should respond
                logger.debug(f"Deciding whether to respond in channel {channel_id}")
                should_respond = await decide_response_from_model(api, commands.decision_model_id, messages[channel_id])

                if isinstance(should_respond, bool):
                    if should_respond:
                        logger.info(f"Preparing to respond in channel {channel_id}")
                        # Prepare to send typing indicator and delay
                        await send_typing(sio, channel_id)
                        await asyncio.sleep(1)  # Simulate a delay

                        # Get the actual response using current model from commands
                        logger.debug(f"Generating response from model: {commands.model_id}")
                        response = await get_response(api, commands.model_id, conversation)

                        # Log the assistant's message
                        logger.info(f"Sending response in channel {channel_id}")

                        await send_message(channel_id, response)
                        logger.debug(f"Response sent successfully to channel {channel_id}")
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
