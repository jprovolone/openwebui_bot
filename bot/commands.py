from typing import Dict, Optional
import aiohttp
import random
import logging
import urllib.parse
from utils import get_response_from_model_sync

class Commands:
    # Command descriptions for help command
    COMMAND_DESCRIPTIONS = {
        'help': 'List all available commands and their descriptions',
        'clearcontext': 'Clear the message history for the current channel',
        'vibecheck': 'Analyze the current chat vibe with AI',
        'roast': 'Generate an AI-powered playful roast',
        '8ball': 'Ask the AI magic 8-ball a question (usage: $8ball your question)',
        'gif': 'Generate a reaction GIF based on recent chat context',
        'modellist': 'Show all available AI models',
        'modelswitch': 'Switch to a different AI model (usage: $modelswitch model_id)'
    }

    def __init__(self, messages: Dict, api, descision_model_id: str, model_id: str):
        self.messages = messages
        self.api = api
        self.descision_model_id = descision_model_id
        self.model_id = model_id
        self.logger = logging.getLogger(__name__)

    async def clearcontext(self, channel_id: str) -> str:
        """
        Clear the message context for a specific channel
        """
        if channel_id in self.messages:
            self.messages[channel_id] = []
            return "*Message context cleared*"
        return "*No message context found for this channel*"

    async def handle_command(self, command: str, channel_id: str) -> Optional[str]:
        """
        Handle incoming commands and route to appropriate method
        """
        # Get the base command and any additional text
        full_command = command[1:].strip()  # Remove $ and trim
        parts = full_command.split(maxsplit=1)
        base_command = parts[0].lower()
        
        # Map commands to methods
        command_map = {
            'help': self.help,
            'clearcontext': self.clearcontext,
            'vibecheck': self.vibe_check,
            'roast': self.roast,
            '8ball': self.magic_8ball,
            'gif': self.gif,
            'modellist': self.modellist,
            'modelswitch': self.modelswitch
        }
        
        # Get the command handler if it exists
        handler = command_map.get(base_command)
        
        if handler:
            if base_command in ['8ball', 'modelswitch']:
                return await handler(channel_id, command)
            return await handler(channel_id)
        
        return "*Not a valid command*"

    async def vibe_check(self, channel_id: str) -> str:
        """Check the current channel vibe using AI analysis"""
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

    async def help(self, channel_id: str) -> str:
        """List all available commands and their descriptions"""
        help_text = "Available commands:\n\n"
        for cmd, desc in self.COMMAND_DESCRIPTIONS.items():
            help_text += f"${cmd}: {desc}\n"
        return f"```\n{help_text}```"

    async def modellist(self, channel_id: str) -> str:
        """Show available AI models"""
        models = self.api.get_models()
        if not models:
            return "*No models available*"
        
        model_list = "Available models:\n\n"
        for model in models:
            model_list += f"- {model.id}"
            if model.id == self.model_id:
                model_list += " (current)"
            model_list += "\n"
        return f"```\n{model_list}```"

    async def modelswitch(self, channel_id: str, command: str) -> str:
        """Switch to a different AI model"""
        # Extract model ID from command
        model_id = command[len("$modelswitch"):].strip()
        
        if not model_id:
            return "*Provide a model ID to switch to. Use $modellist to see available models.*"
        
        # Check if model exists
        available_models = [model.id for model in self.api.get_models()]
        if model_id not in available_models:
            return f"*Model '{model_id}' not found. Use $modellist to see available models.*"
        
        # Update model ID
        self.model_id = model_id
        return f"*Switched to model: {model_id}*"

    async def gif(self, channel_id: str) -> str:
        """Find a relevant GIF based on chat context using GIPHY"""
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
        self.logger.info(f"Original search query: {search_query}")
        encoded_query = urllib.parse.quote(search_query)
        self.logger.info(f"Encoded search query: {encoded_query}")
        
        try:
            # Use Tenor's public API endpoint
            async with aiohttp.ClientSession() as session:
                url = f"https://g.tenor.com/v1/search?q={encoded_query}&limit=20&media_filter=minimal&contentfilter=off&key=LIVDSRZULELA"
                self.logger.info(f"Tenor URL: {url}")
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('results'):
                            # Pick a random GIF from the results
                            gif = random.choice(data['results'])
                            gif_url = gif.get('media')[0].get('gif', {}).get('url')
                            if gif_url:
                                self.logger.info(f"Found GIF: {gif_url}")
                                return f"![{search_query}]({gif_url})"
                    self.logger.error(f"Tenor response status: {response.status}")
                    response_text = await response.text()
                    self.logger.error(f"Tenor response: {response_text}")
            return "*Couldn't find a dank enough GIF, my bad*"
        except Exception as e:
            self.logger.error(f"GIF search failed: {str(e)}")
            return "*GIF search failed, but I'll keep it real - something's wrong with the GIF service*"

    async def roast(self, channel_id: str) -> str:
        """Generate an AI roast"""
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

    async def magic_8ball(self, channel_id: str, command: str) -> str:
        """AI-powered magic 8-ball"""
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
