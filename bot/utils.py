import aiohttp
import socketio
import asyncio
from env import WEBUI_URL, TOKEN, OPENWEBUI_API_KEY


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

async def get_latest_messages(channel_id: str, limit: int = 20):
    """
    Fetch the latest messages from a channel.
    
    Args:
        channel_id (str): The ID of the channel to fetch messages from
        limit (int, optional): Maximum number of messages to fetch. Defaults to 20.
        
    Returns:
        dict: The response containing the messages
    """
    url = f"{WEBUI_URL}/api/v1/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    params = {"limit": limit}

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
            return await response.json()

async def get_response_from_model_sync(api, model_id: str, messages):
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, api.get_chat_completion_with_messages, model_id, messages)
        print("Result:", result)
        return result.choices[0].message.content
    except Exception as e:
        print("Async exception:", str(e))
        raise
