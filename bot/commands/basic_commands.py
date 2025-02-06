from typing import Dict
import asyncio
import aiohttp
import random
import logging
import urllib.parse
import tiktoken
from .command import Command, CommandRegistry
from bot.utils import get_response_from_model_sync

@CommandRegistry.register("help", "List all available commands and their descriptions")
class HelpCommand(Command):
    async def execute(self, channel_id: str, command: str = None) -> str:
        help_text = "Available commands:\n\n"
        for cmd, desc in CommandRegistry.get_command_descriptions().items():
            help_text += f"${cmd}: {desc}\n"
        return f"```\n{help_text}```"

@CommandRegistry.register("clearcontext", "Clear the message history for the current channel")
class ClearContextCommand(Command):
    async def execute(self, channel_id: str, command: str = None) -> str:
        if channel_id in self.messages:
            self.messages[channel_id] = []
            return "*Message context cleared*"
        return "*No message context found for this channel*"

@CommandRegistry.register("modellist", "Show all available AI models")
class ModelListCommand(Command):
    async def execute(self, channel_id: str, command: str = None) -> str:
        try:
            loop = asyncio.get_running_loop()
            models = await loop.run_in_executor(None, self.api.get_models)
            if not models:
                return "*No models available*"
            
            model_list = "Available models:\n\n"
            for model in models:
                model_list += f"- {model.id}"
                if model.id == self.model_id:
                    model_list += " (current)"
                model_list += "\n"
            return f"```\n{model_list}```"
        except Exception as e:
            return f"*Failed to get models: {str(e)}*"

@CommandRegistry.register("modelswitch", "Switch to a different AI model (usage: $modelswitch model_type_switch(-d/-c/-a) model_id)")
class ModelSwitchCommand(Command):
    async def execute(self, channel_id: str, command: str) -> str:
        try:
            print(command)
            # Extract model type and model ID from command
            model_type = command[len("$modelswitch"):].split(' ')[1]
            model_id = command[len("$modelswitch"):].split(' ')[-1]

            if not model_type:
                return "*Provide a model type to switch -d (decision model) -c (conversation model).*"

            if not model_id:
                return "*Provide a model ID to switch to. Use $modellist to see available models.*"
            
            # Check if model exists
            loop = asyncio.get_running_loop()
            models = await loop.run_in_executor(None, self.api.get_models)
            available_models = [model.id for model in models]
            if model_id not in available_models:
                return f"*Model '{model_id}' not found. Use $modellist to see available models.*"
            
            # Update model ID
            if model_type == "-c":
                self.model_id = model_id
                return f"*Switched to model: {model_id}*"
            elif model_type == "-d":
                self.decision_model_id = model_id
                return f"*Switched decision model to: {model_id}*"
            elif model_type == "-a":
                self.model_id = model_id
                self.decision_model_id = model_id
                return f"*Switched decision and conversation models to: {model_id}*"
            else:
                return "*Invalid model type. Use -d (decision model), -c (conversation model), or -a (both).*"
        except Exception as e:
            return f"*Failed to switch model: {str(e)}*"

@CommandRegistry.register("vibecheck", "Analyze the current chat vibe with AI")
class VibeCheckCommand(Command):
    async def execute(self, channel_id: str, command: str = None) -> str:
        if channel_id not in self.messages or len(self.messages[channel_id]) <= 1:
            return "*Channel's dead AF, no vibe detected*"
        
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
        
        recent_messages = [m for m in self.messages[channel_id] if m["role"] != "system"][-5:]
        
        system_prompt = {
            "role": "system",
            "content": """RESPOND WITH ONLY THE SEARCH TERM, NO OTHER TEXT.
            You are finding a reaction GIF for the chat. Based on the messages, give a 2-4 word search term for a reaction GIF.
            Focus on popular memes, reactions, or emotions. Examples: "deal with it", "mind blown", "facepalm", "thug life", etc.
            DO NOT include phrases like "Search query:" or any other text. ONLY the search term."""
        }
        
        context = [system_prompt] + recent_messages
        search_query = await get_response_from_model_sync(self.api, self.model_id, context)
        
        search_query = search_query.strip().lower()
        encoded_query = urllib.parse.quote(search_query)
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://g.tenor.com/v1/search?q={encoded_query}&limit=20&media_filter=minimal&contentfilter=off&key=LIVDSRZULELA"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('results'):
                            gif = random.choice(data['results'])
                            gif_url = gif.get('media')[0].get('gif', {}).get('url')
                            if gif_url:
                                return f"![{search_query}]({gif_url})"
            return "*Couldn't find a dank enough GIF, my bad*"
        except Exception as e:
            return "*GIF search failed, but I'll keep it real - something's wrong with the GIF service*"

@CommandRegistry.register("tokencheck", "Calculate the number of tokens in the current chat context")
class TokenCheckCommand(Command):
    async def execute(self, channel_id: str, command: str = None) -> str:
        if channel_id not in self.messages or not self.messages[channel_id]:
            return "*No message context found for this channel*"
        
        try:
            # Get the encoding for an exmaple model
            enc = tiktoken.encoding_for_model("gpt-4o")
            
            # Initialize counters
            total_tokens = 0
            role_tokens = {"system": 0, "user": 0, "assistant": 0}
            
            # Count tokens for each message
            for message in self.messages[channel_id]:
                # Count tokens in the content
                content_tokens = len(enc.encode(message["content"]))
                # Add tokens for message format (role, content markers, etc)
                format_tokens = 4  # Each message follows format: <im_start>{role}\n{content}<im_end>\n
                message_tokens = content_tokens + format_tokens
                
                # Update counters
                total_tokens += message_tokens
                role_tokens[message["role"]] += message_tokens
            
            # Format the response
            response = f"Total tokens: {total_tokens}\n\n"
            response += "Breakdown:\n"
            for role, count in role_tokens.items():
                if count > 0:  # Only show roles that have messages
                    response += f"- {role}: {count} tokens\n"
            
            return f"```\n{response}```"
            
        except Exception as e:
            return f"*Failed to calculate tokens: {str(e)}*"
