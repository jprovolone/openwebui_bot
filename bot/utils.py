import aiohttp
import socketio
import asyncio
from bot.env import WEBUI_URL, TOKEN, OPENWEBUI_API_KEY
import tiktoken
import json
import pprint

async def send_message(channel_id: str, message: str):
    url = f"{WEBUI_URL}/api/v1/channels/{channel_id}/messages/post"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    data = {"content": message}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status != 200:
                # Raise an exception if the request fails
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=await response.text(),
                    headers=response.headers,
                )
            # Return response JSON if successful
            return await response.json()


async def send_typing(sio: socketio.AsyncClient, channel_id: str):
    await sio.emit(
        "channel-events",
        {
            "channel_id": channel_id,
            "data": {"type": "typing", "data": {"typing": True}},
        },
    )

async def get_latest_messages(channel_id: str, bot_id: str = None, before_id: str = None, limit: int = 20):
    """
    Fetch the latest messages from a channel and return simplified format.
    
    Args:
        channel_id (str): The ID of the channel to fetch messages from
        bot_id (str): The bot's user ID to determine system messages
        before_id (str, optional): Get messages before this message ID to avoid duplicates
        limit (int, optional): Maximum number of messages to fetch. Defaults to 20.
        
    Returns:
        list: List of simplified message objects with role and content
    """
    url = f"{WEBUI_URL}/api/v1/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    params = {"limit": limit}
    if before_id:
        params["before"] = before_id

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status != 200:
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=await response.text(),
                    headers=response.headers,
                )
            messages = await response.json()

            # Build a map of user IDs to names from all messages
            user_map = {}
            for msg in messages:
                user = msg.get("user", {})
                if user.get("id") and user.get("name"):
                    user_map[user["id"]] = user["name"]

            # Filter out command messages and their bot responses
            filtered_messages = []
            skip_next_bot = False
            
            for msg in reversed(messages):
                if not msg.get("content"):
                    continue
                    
                # Skip command messages
                if msg.get("content").startswith("$"):
                    skip_next_bot = True
                    continue
                    
                # If we're looking for a bot message to skip
                if skip_next_bot and msg.get("user", {}).get("id") == bot_id:
                    skip_next_bot = False
                    continue
                
                # Create message data as a JSON string
                message_data = {
                    "role": "assistant" if msg.get("user", {}).get("id") == bot_id else "user",
                    "content": {
                        "user": {
                            "id": msg.get("user", {}).get("id", ""),
                            "name": msg.get("user", {}).get("name", "Unknown")
                        },
                        "message": msg.get("content", ""),
                        "reactions": [
                            {
                                "name": r.get('name', ''),
                                "count": r.get('count', 0),
                                "users": [user_map.get(user_id, "Unknown User") for user_id in r.get('user_ids', [])]
                            }
                            for r in msg.get('reactions', [])
                        ]
                    }
                }
                
                # Convert to JSON string with proper Unicode handling
                filtered_messages.append({
                    "role": message_data["role"],
                    "content": json.dumps(message_data["content"], ensure_ascii=False)
                })
            
            pprint.pprint(filtered_messages)
            return filtered_messages

def parse_message_content(message):
    """
    Parse a message's content from either plain text or JSON string format.
    
    Args:
        message (dict): Message object with 'content' field that might be JSON string
        
    Returns:
        str: The actual message content
    """
    try:
        import json
        if isinstance(message.get('content'), str):
            try:
                # Try to parse as JSON string
                content_data = json.loads(message['content'])
                if isinstance(content_data, dict):
                    # Extract message from JSON structure
                    return content_data.get('message', content_data.get('response', message['content']))
            except json.JSONDecodeError:
                # If not JSON, return as is
                return message['content']
    except Exception:
        # If any error occurs, return original content
        return message.get('content', '')

def get_message_context(messages, exclude_system=True, last_n=None):
    """
    Get message content from a list of messages, handling JSON string format.
    
    Args:
        messages (list): List of message objects
        exclude_system (bool): Whether to exclude system messages
        last_n (int, optional): Only get the last N messages
        
    Returns:
        list: List of messages with parsed content
    """
    filtered_messages = [m for m in messages if not exclude_system or m['role'] != 'system']
    
    if last_n is not None:
        filtered_messages = filtered_messages[-last_n:]
    
    return [{
        'role': msg['role'],
        'content': parse_message_content(msg)
    } for msg in filtered_messages]

async def get_response_from_model_sync(api, model_id: str, messages):
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, api.get_chat_completion_with_messages, model_id, messages)
        print("Result:", result)  
        return result.choices[0].message.content
    except Exception as e:
        print("Async exception:", str(e))
        raise

def filter_conversation_by_tokens(conversation, token_limit=200000):
    """
    Filter a conversation array to keep it within a token limit while preserving system messages.
    
    Args:
        conversation (list): List of message objects with 'role' and 'content' fields
        token_limit (int): Maximum number of tokens allowed (default: 200,000)
        
    Returns:
        list: Filtered conversation array within token limit
    """
    # Get the encoding for GPT-4o
    enc = tiktoken.get_encoding("o200k_base")
    
    # Separate system messages from other messages
    system_messages = [msg for msg in conversation if msg['role'] == 'system']
    other_messages = [msg for msg in conversation if msg['role'] != 'system']
    
    def count_tokens(messages):
        total = 0
        for msg in messages:
            # Count tokens in the content
            content_tokens = len(enc.encode(str(msg.get('content', ''))))
            # Add tokens for message format (role, content markers, etc)
            format_tokens = 4  # Each message follows format: <im_start>{role}\n{content}<im_end>\n
            total += content_tokens + format_tokens
        return total
    
    # Start with all system messages
    filtered_conversation = system_messages.copy()
    remaining_tokens = token_limit - count_tokens(system_messages)
    
    # Add non-system messages from the end until we hit the token limit
    for msg in reversed(other_messages):
        msg_tokens = count_tokens([msg])
        if msg_tokens <= remaining_tokens:
            filtered_conversation.append(msg)
            remaining_tokens -= msg_tokens
        else:
            break
    
    # Sort messages back into original order
    filtered_conversation.sort(key=lambda x: conversation.index(x))
    
    return filtered_conversation
