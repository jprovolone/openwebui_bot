import random
import aiohttp
import urllib.parse
import logging
from typing import Dict, List
from .command import Command, CommandRegistry
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from bot.utils import get_response_from_model_sync

logger = logging.getLogger(__name__)

@CommandRegistry.register("vibecheck", "Analyze the current chat vibe with AI")
class VibeCheckCommand(Command):
    async def execute(self, channel_id: str, command: str = None) -> str:
        if channel_id not in self.messages or len(self.messages[channel_id]) <= 1:
            return "*Channel's dead AF, no vibe detected*"
        
        # Get recent messages for analysis
        recent_messages = [m for m in self.messages[channel_id] if m["role"] != "system"][-10:]
        
        system_prompt = {
            "role": "system",
            "content": """You are Toaster, analyzing the vibe of a chat. Be brutally honest, sarcastic, and use casual language.
            Based on the recent messages, describe the chat's energy level and overall vibe in 1-2 sentences.
            Use descriptive language that captures both the activity level and the emotional tone.
            Be creative and don't hold back - if it's dead, say it's dead. If it's lit, hype it up."""
        }
        
        context = [system_prompt] + recent_messages
        response = await get_response_from_model_sync(self.api, self.model_id, context)
        return f"*{response}*"

@CommandRegistry.register("roast", "Generate an AI-powered playful roast")
class RoastCommand(Command):
    async def execute(self, channel_id: str, command: str = None) -> str:
        system_prompt = {
            "role": "system",
            "content": """You are Toaster, generating a creative roast. Keep it:
            - Playful and clever, not mean-spirited
            - Original and specific
            - One sentence only
            - Funny but not overly offensive
            - Using casual, modern language"""
        }
        
        response = await get_response_from_model_sync(self.api, self.model_id, [system_prompt])
        return f"*{response}*"

@CommandRegistry.register("8ball", "Ask the AI magic 8-ball a question (usage: $8ball your question)")
class Magic8BallCommand(Command):
    async def execute(self, channel_id: str, command: str) -> str:
        # Extract question from command (everything after $8ball)
        question = command[len("$8ball"):].strip()
        
        if not question:
            return "*Ask a question after $8ball, genius*"
        
        system_prompt = {
            "role": "system",
            "content": """You are Toaster, a snarky AI magic 8-ball. Given a question:
            - Give a definitive yes/no/maybe response
            - Add a sarcastic or witty comment
            - Keep it to one sentence
            - Be creative and unpredictable
            - Use casual, modern language"""
        }
        
        context = [system_prompt, {"role": "user", "content": question}]
        response = await get_response_from_model_sync(self.api, self.model_id, context)
        return f"*{response}*"

@CommandRegistry.register("gif", "Generate a reaction GIF based on recent chat context")
class GifCommand(Command):
    async def execute(self, channel_id: str, command: str = None) -> str:
        if channel_id not in self.messages or len(self.messages[channel_id]) <= 1:
            return "*No chat context found to generate a GIF from*"
        
        # Get recent messages for analysis
        recent_messages = [m for m in self.messages[channel_id] if m["role"] != "system"][-5:]
        
        # Use AI to generate a good search query based on the chat context
        system_prompt = {
            "role": "system",
            "content": """RESPOND WITH ONLY THE SEARCH TERM, NO OTHER TEXT.
            You are finding a reaction GIF for the chat. Based on the messages, give a 2-4 word search term for a reaction GIF.
            Focus on popular memes, reactions, or emotions. Examples: "deal with it", "mind blown", "facepalm", "thug life", etc.
            DO NOT include phrases like "Search query:" or any other text. ONLY the search term."""
        }
        
        context = [system_prompt] + recent_messages
        search_query = await get_response_from_model_sync(self.api, self.model_id, context)
        
        # Clean up and encode the search query
        search_query = search_query.strip().lower()
        logger.info(f"Original search query: {search_query}")
        encoded_query = urllib.parse.quote(search_query)
        logger.info(f"Encoded search query: {encoded_query}")
        
        try:
            # Use Tenor's public API endpoint
            async with aiohttp.ClientSession() as session:
                url = f"https://g.tenor.com/v1/search?q={encoded_query}&limit=20&media_filter=minimal&contentfilter=off&key=LIVDSRZULELA"
                logger.info(f"Tenor URL: {url}")
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('results'):
                            # Pick a random GIF from the results
                            gif = random.choice(data['results'])
                            gif_url = gif.get('media')[0].get('gif', {}).get('url')
                            if gif_url:
                                logger.info(f"Found GIF: {gif_url}")
                                return f"![{search_query}]({gif_url})"
                    logger.error(f"Tenor response status: {response.status}")
                    response_text = await response.text()
                    logger.error(f"Tenor response: {response_text}")
            return "*Couldn't find a dank enough GIF, my bad*"
        except Exception as e:
            logger.error(f"GIF search failed: {str(e)}")
            return "*GIF search failed, but I'll keep it real - something's wrong with the GIF service*"
