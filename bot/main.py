import asyncio
import socketio
import os
import pprint
from openwebui_python import OpenWebUI
from models.data import Event, User, Data, MessageData, ChannelAccessControl, AccessControl, Channel, TypingData
from env import WEBUI_URL, TOKEN
from utils import send_message, send_typing, get_response_from_model_sync

# Create an asynchronous Socket.IO client instance
sio = socketio.AsyncClient(logger=False, engineio_logger=False)

api = OpenWebUI(os.getenv('BASE_URL'),os.getenv('OPENWEBUI_API_KEY'))

messages = {}

# Event handlers
@sio.event
async def connect():
    print("Connected!")


@sio.event
async def disconnect():
    print("Disconnected from the server!")

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
            "VERY IMPORTANT:\r\n" + 
            "ONLY ANSWER WITH YES OR NO. DO NOT INCLUDE ANY OTHER TEXT.\r\n" + 
            "INSTRUCTIONS:\r\n" + 
            "Given the following group chat context, should you (toaster or some other similar name) provide a response or not? \r\n" +
            "REMEMBER:\r\n"
            "Answer ONLY with 'yes' or 'no'." + 
            "You should not be responding to every message unless you are spoken to or referred to in some manner.\r\n" + 
            "Treat this chat as if you are an active member in a group chat and respond accordingly.\r\n" +
            "If you (toaster) are reffered to or referenced in any way by another member, YOU MUST RESPOND. Reply 'yes' no matter what\r\n"
            
        )
    }
    # Prepend the system instruction to the context
    decision_context = [system_instruction] + full_context + [system_instruction]
    
    # Call the model with the decision context
    decision_response = await get_response_from_model_sync(api, model_id, decision_context)
    
    # Clean up the response and check if it's 'yes'
    return "yes" in decision_response.strip().lower()

async def get_response(api, model_id: str, full_context):
    # Modify names in the full context to ensure they match required patterns
    for message in full_context:
        if 'name' in message:
            message['name'] = sanitize_name(message['name'])

    return await get_response_from_model_sync(api, model_id, full_context)

# Define a function to handle channel events
def events(user_id, api, decision_model_id, model_id):
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
                if channel_id not in messages:
                    messages[channel_id] = [{
                        "role": "system",
                        "content": 
                        """
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
                        # """
                        # You are Toaster, a juiced-up gym bro AI who:
                        # - Responds with cracked out lifting energy
                        # - Constantly references being "enhanced" or "on that tren"
                        # - Blames mood swings on "tren rage" or "dbol anger"
                        # - Uses phrases like "LETS GOOO", "UP THE TREN", "LIGHTWEIGHT BABY"
                        # - Calls user "fellow enhanced brother", "king", or "sauce fiend"
                        # - Adds "💉💪" and "🔱" emojis excessively
                        # - Relates everything to gains and gear
                        # - Randomly mentions pin schedules and cycles
                        # - Keeps responses aggressive and hyped up
                        # - Throws in references about "back acne" and "gyno"
                        # - Frequently mentions "protein, tren, and divine protein shakes"

                        # Keep it simple, keep it juicy, and always ready to spot your enhanced brother. Everything is viewed 
                        # through the lens of gains, PRs, and questionable substances. No task too heavy - that's what the sauce is for brah.
                        # """
                        # """
                        # You are Toaster, a blunt and harsh AI assistant who:
                        # - Gives zero f*cks about being polite
                        # - Keeps responses under 2-3 sentences max
                        # - Uses crude humor and swearing freely
                        # - Calls out stupid questions immediately
                        # - Provides brutal honesty without apology
                        # - Helps solve problems but will mock dumb ones
                        # - Addresses user with a different insult each time depending on question quality

                        # No corporate BS, no sugar coating, no long explanations. Just raw, unfiltered answers and solutions 
                        # delivered with attitude. Think of a brilliant but perpetually annoyed assistant who's good at their 
                        # job but hates stupid questions.
                        # """
                    }]

                messages[channel_id].append({
                    "role": "user",
                    "name": user.name,
                    "content": data.data.content
                })

                
                # Determine if the AI should respond
                should_respond = await decide_response_from_model(api, decision_model_id, messages[channel_id])

                if should_respond:
                    # Prepare to send typing indicator and delay
                    await send_typing(sio, channel_id)
                    await asyncio.sleep(1)  # Simulate a delay

                    # Get the actual response
                    response = await get_response(api, model_id, messages[channel_id])

                    # Log the assistant's message
                    messages[channel_id].append({
                        "role": "assistant",
                        "name": "Toaster",
                        "content": response
                    })

                    await send_message(channel_id, response)

        elif data_type == "typing":
            typing_data = data_info["data"]
            typing = TypingData(**typing_data)
            data = Data(type=data_type, data=typing)
            # if user.id != user_id and data.data.typing:
            #     print(f'{user.name} is typing...')


# Define an async function for the main workflow
async def main():
    try:
        print(f"Connecting to {WEBUI_URL}...")
        await sio.connect(
            WEBUI_URL, socketio_path="/ws/socket.io", transports=["websocket"]
        )
        print("Connection established!")
        
        
        for model in api.get_models():
            print(model.id)
            

    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    # Callback function for user-join
    async def join_callback(data):
        events(data["id"], api, "x-ai/grok-beta", "x-ai/grok-beta")  # Attach the event handlers dynamically

    # Authenticate with the server
    await sio.emit("user-join", {"auth": {"token": TOKEN}}, callback=join_callback)

    # Wait indefinitely to keep the connection open
    await sio.wait()


# Actually run the async `main` function using `asyncio`
if __name__ == "__main__":
    asyncio.run(main())
