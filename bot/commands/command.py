from typing import Dict, Optional, List, Type, Callable
from functools import wraps
import inspect

class Command:
    """Base interface for all commands"""
    name: str
    description: str
    
    def __init__(self, messages: Dict, api, decision_model_id: str, model_id: str):
        self.messages = messages
        self.api = api
        self.decision_model_id = decision_model_id
        self.model_id = model_id
    
    async def execute(self, channel_id: str, command: str = None) -> str:
        """Execute the command"""
        raise NotImplementedError

class CommandRegistry:
    """Registry for all commands"""
    _commands: Dict[str, Type[Command]] = {}
    
    @classmethod
    def register(cls, name: str, description: str) -> Callable:
        """Decorator to register a command"""
        def decorator(command_cls: Type[Command]) -> Type[Command]:
            command_cls.name = name
            command_cls.description = description
            cls._commands[name] = command_cls
            return command_cls
        return decorator
    
    @classmethod
    def get_commands(cls) -> Dict[str, Type[Command]]:
        """Get all registered commands"""
        return cls._commands
    
    @classmethod
    def get_command(cls, name: str) -> Optional[Type[Command]]:
        """Get a specific command by name"""
        return cls._commands.get(name)

    @classmethod
    def get_command_descriptions(cls) -> Dict[str, str]:
        """Get descriptions for all commands"""
        return {name: cmd.description for name, cmd in cls._commands.items()}
