from typing import Dict
import aiohttp
import random
import urllib.parse
from bot.commands.base_command import BaseCommand
from bot.utils import get_response_from_model_sync

class HelpCommand(BaseCommand):
    def __init__(self):
        super().__init__("help", "List all available commands and their descriptions")

    async def execute(self, channel_id: str, **kwargs) -> str:
        help_text = "Available commands:\n\n"
        # Use the registry directly through self
        for cmd in self.registry.get_all_commands().values():
            help_text += f"${cmd.name}: {cmd.description}\n"
        return f"```\n{help_text}```"

class ClearContextCommand(BaseCommand):
    def __init__(self):
        super().__init__("clearcontext", "Clear the message history for the current channel")

    async def execute(self, channel_id: str, **kwargs) -> str:
        # This command is no longer needed since we're not storing messages locally
        return "*Message history is not stored locally anymore*"

class VibeCheckCommand(BaseCommand):
    def __init__(self):
        super().__init__("vibecheck", "Analyze the current chat vibe with AI")

    async def execute(self, channel_id: str, **kwargs) -> str:
        from bot.utils import get_latest_messages
        try:
            # Get the latest messages from the channel
            message_history = await get_latest_messages(channel_id, limit=10)
            if not message_history:
                return "*Channel's dead AF, no vibe detected*"
            
            # Convert API messages to the format expected by the model
            recent_messages = []
            for msg in message_history:
                msg_user = msg.get('user', {})
                recent_messages.append({
                    "role": "user",
                    "name": msg_user.get('name', 'unknown'),
                    "content": msg.get('content', '')
                })
        except Exception as e:
            return f"*Failed to fetch message history: {str(e)}*"
        
        system_prompt = {
            "role": "system",
            "content": """You are Toaster, analyzing the vibe of a chat. Be brutally honest, sarcastic, and use casual language.
            Based on the recent messages, describe the chat's energy level and overall vibe in 1-2 sentences.
            Use descriptive language that captures both the activity level and the emotional tone.
            Be creative and don't hold back - if it's dead, say it's dead. If it's lit, hype it up."""
        }
        
        context = [system_prompt] + recent_messages
        api = kwargs.get('api')
        model_id = kwargs.get('model_id', '')
        response = await get_response_from_model_sync(api, model_id, context)
        return f"*{response}*"

class ModelListCommand(BaseCommand):
    def __init__(self):
        super().__init__("modellist", "Show all available AI models")

    async def execute(self, channel_id: str, **kwargs) -> str:
        api = kwargs.get('api')
        model_id = kwargs.get('model_id', '')
        models = api.get_models()
        if not models:
            return "*No models available*"
        
        model_list = "Available models:\n\n"
        for model in models:
            model_list += f"- {model.id}"
            if model.id == model_id:
                model_list += " (current)"
            model_list += "\n"
        return f"```\n{model_list}```"

class ModelSwitchCommand(BaseCommand):
    def __init__(self):
        super().__init__("modelswitch", "Switch to a different AI model (usage: $modelswitch type(-d/-c/-a) model_id)")

    async def execute(self, channel_id: str, **kwargs) -> str:
        api = kwargs.get('api')
        command = kwargs.get('command', '')
        try:
        # Extract model ID and type from command
            parts = command[len("$modelswitch"):].split()
            if len(parts) < 2:
                return "*Usage: $modelswitch type(-d/-c/-a) model_id(s)* (For -a use: model_id1,model_id2)"
            model_type = parts[0]
            new_model_id = parts[1]
        except IndexError:
            return "*Usage: $modelswitch type(-d/-c/-a) model_id(s)* (For -a use: model_id1,model_id2)"
        
        if not model_type:
            return "*Provide a model type (e.g., $modelswitch type(-d/-c/-a) sentiment)*"

        if not new_model_id:
            return "*Provide a model ID to switch to. Use $modellist to see available models.*"
        
        available_models = [model.id for model in api.get_models()]
        
        # Get the parent Commands instance that's handling this command
        parent_instance = self.registry.parent

        # Update model ID
        if model_type == "-d":
            if new_model_id not in available_models:
                return f"*Model '{new_model_id}' not found. Use $modellist to see available models.*"
            parent_instance.descision_model_id = new_model_id
        elif model_type == "-c":
            if new_model_id not in available_models:
                return f"*Model '{new_model_id}' not found. Use $modellist to see available models.*"
            parent_instance.model_id = new_model_id
        elif model_type == "-a":
            try:
                decision_id, chat_id = new_model_id.split(',')
                if decision_id not in available_models:
                    return f"*Decision model '{decision_id}' not found. Use $modellist to see available models.*"
                if chat_id not in available_models:
                    return f"*Chat model '{chat_id}' not found. Use $modellist to see available models.*"
                parent_instance.descision_model_id = decision_id
                parent_instance.model_id = chat_id
                return f"*Switched decision model to: {decision_id}\nSwitched chat model to: {chat_id}*"
            except ValueError:
                return "*For -a flag, provide two model IDs separated by comma (e.g., model1,model2)*"
        else:
            return "*Invalid model type. Use -d for decision model, -c for conversation, or -a for all.*"
        
        return f"*Switched to model: {new_model_id}*"

class GifCommand(BaseCommand):
    def __init__(self):
        super().__init__("gif", "Generate a reaction GIF based on recent chat context")

    async def execute(self, channel_id: str, **kwargs) -> str:
        from bot.utils import get_latest_messages
        api = kwargs.get('api')
        model_id = kwargs.get('model_id', '')
        
        try:
            # Get the latest messages from the channel
            message_history = await get_latest_messages(channel_id, limit=5)
            if not message_history:
                return "*No chat context found to generate a GIF from*"
            
            # Convert API messages to the format expected by the model
            recent_messages = []
            for msg in message_history:
                msg_user = msg.get('user', {})
                recent_messages.append({
                    "role": "user",
                    "name": msg_user.get('name', 'unknown'),
                    "content": msg.get('content', '')
                })
        except Exception as e:
            return f"*Failed to fetch message history: {str(e)}*"
        
        # Use AI to generate a good search query based on the chat context
        system_prompt = {
            "role": "system",
            "content": """RESPOND WITH ONLY THE SEARCH TERM, NO OTHER TEXT.
            You are finding a reaction GIF for the chat. Based on the messages, give a 2-4 word search term for a reaction GIF.
            Focus on popular memes, reactions, or emotions. Examples: "deal with it", "mind blown", "facepalm", "thug life", etc.
            DO NOT include phrases like "Search query:" or any other text. ONLY the search term."""
        }
        
        context = [system_prompt] + recent_messages
        search_query = await get_response_from_model_sync(api, model_id, context)
        
        # Clean up and encode the search query
        search_query = search_query.strip().lower()
        encoded_query = urllib.parse.quote(search_query)
        
        try:
            # Use Tenor's public API endpoint
            async with aiohttp.ClientSession() as session:
                url = f"https://g.tenor.com/v1/search?q={encoded_query}&limit=20&media_filter=minimal&contentfilter=off&key=LIVDSRZULELA"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('results'):
                            # Pick a random GIF from the results
                            gif = random.choice(data['results'])
                            gif_url = gif.get('media')[0].get('gif', {}).get('url')
                            if gif_url:
                                return f"![{search_query}]({gif_url})"
            return "*Couldn't find a dank enough GIF, my bad*"
        except Exception as e:
            return "*GIF search failed, but I'll keep it real - something's wrong with the GIF service*"

class RoastCommand(BaseCommand):
    def __init__(self):
        super().__init__("roast", "Generate an AI-powered playful roast")

    async def execute(self, channel_id: str, **kwargs) -> str:
        api = kwargs.get('api')
        model_id = kwargs.get('model_id', '')
        system_prompt = {
            "role": "system",
            "content": """You are Toaster, generating a creative roast. Keep it:
            - Playful and clever, not mean-spirited
            - Original and specific
            - One sentence only
            - Funny but not overly offensive
            - Using casual, modern language"""
        }
        
        response = await get_response_from_model_sync(api, model_id, [system_prompt])
        return f"*{response}*"

class Magic8BallCommand(BaseCommand):
    def __init__(self):
        super().__init__("8ball", "Ask the AI magic 8-ball a question (usage: $8ball your question)")

    async def execute(self, channel_id: str, **kwargs) -> str:
        api = kwargs.get('api')
        model_id = kwargs.get('model_id', '')
        command = kwargs.get('command', '')
        # Extract question from command
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
        response = await get_response_from_model_sync(api, model_id, context)
        return f"*{response}*"
