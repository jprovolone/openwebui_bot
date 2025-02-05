from typing import Dict, Optional
import logging
from .command import Command, CommandRegistry
from .basic_commands import *  # This registers the basic commands
from .fun_commands import *    # This registers the fun commands

class Commands:
    """Main command handler that uses the command registry"""
    
    def __init__(self, messages: Dict, api, decision_model_id: str, model_id: str):
        self.messages = messages
        self.api = api
        self.decision_model_id = decision_model_id
        self.model_id = model_id
        self.logger = logging.getLogger(__name__)
        
        # Initialize all registered commands
        self.command_instances = {}
        for name, command_cls in CommandRegistry.get_commands().items():
            self.command_instances[name] = command_cls(messages, api, decision_model_id, model_id)

    async def handle_command(self, command: str, channel_id: str) -> Optional[str]:
        """Handle incoming commands using the command registry"""
        # Get the base command and any additional text
        full_command = command[1:].strip()  # Remove $ and trim
        parts = full_command.split(maxsplit=1)
        base_command = parts[0].lower()
        
        # Get the command instance if it exists
        command_instance = self.command_instances.get(base_command)
        
        if command_instance:
            try:
                return await command_instance.execute(channel_id, command)
            except Exception as e:
                self.logger.error(f"Error executing command {base_command}: {str(e)}")
                return f"*Command failed: {str(e)}*"
        
        return "*Not a valid command*"
