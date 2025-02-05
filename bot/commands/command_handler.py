from typing import Dict, Optional
from .command import Command, CommandRegistry

class CommandHandler:
    def __init__(self, messages: Dict, api, decision_model_id: str, model_id: str):
        self.messages = messages
        self.api = api
        self.decision_model_id = decision_model_id
        self.model_id = model_id
        
        # Initialize all registered commands
        self.commands = {}
        for name, command_class in CommandRegistry.get_commands().items():
            self.commands[name] = command_class(messages, api, decision_model_id, model_id)
    
    async def handle_command(self, command: str, channel_id: str) -> Optional[str]:
        """
        Handle incoming commands and route to appropriate command class
        """
        # Get the base command and any additional text
        full_command = command[1:].strip()  # Remove $ and trim
        parts = full_command.split(maxsplit=1)
        base_command = parts[0].lower()
        
        # Get the command handler if it exists
        command_obj = self.commands.get(base_command)
        
        if command_obj:
            return await command_obj.execute(channel_id, command)
        
        return "*Not a valid command*"
