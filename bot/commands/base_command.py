from abc import ABC, abstractmethod
from typing import Dict, Optional

class BaseCommand(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.registry = None  # Will be set when command is registered

    @abstractmethod
    async def execute(self, channel_id: str, **kwargs) -> str:
        """
        Execute the command with the given parameters.
        
        Args:
            channel_id: str - The ID of the channel where the command was executed
            **kwargs: Additional arguments that may include:
                - command: str - The command text (default: "")
                - messages: Dict - Message history (default: None)
                - api - The API client (default: None)
                - model_id: str - The model identifier (default: "")
                - Any additional parameters specific to the command
        
        Returns:
            str: The command's response
        """
        pass

class CommandRegistry:
    def __init__(self, parent=None):
        self.commands: Dict[str, BaseCommand] = {}
        self.parent = parent

    def register(self, command: BaseCommand):
        command.registry = self  # Give command access to registry
        self.commands[command.name] = command

    def get_command(self, name: str) -> Optional[BaseCommand]:
        return self.commands.get(name)

    def get_all_commands(self) -> Dict[str, BaseCommand]:
        return self.commands

    def set_parent(self, parent):
        self.parent = parent
