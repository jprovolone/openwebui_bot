from commands.base_command import BaseCommand, CommandRegistry
import logging
import os
import importlib
import inspect
from pathlib import Path
from typing import Dict, Type, List

class Commands:
    def __init__(self, api, descision_model_id: str, model_id: str):
        self.api = api
        self.descision_model_id = descision_model_id
        self.model_id = model_id
        self.logger = logging.getLogger(__name__)
        self.registry = CommandRegistry(self)
        self._register_commands()

    def _discover_command_classes(self) -> List[Type[BaseCommand]]:
        """Dynamically discover all command classes from *command.py files."""
        command_classes = []
        commands_dir = Path(__file__).parent
        
        # Get all Python files ending with command.py
        for file in commands_dir.glob("*commands.py"):
            if file.name == "base_command.py":
                continue
                
            # Convert file path to module path
            module_name = f"bot.commands.{file.stem}"
            try:
                # Import the module
                module = importlib.import_module(module_name)
                
                # Find all classes in the module that inherit from BaseCommand
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, BaseCommand) and 
                        obj != BaseCommand and 
                        obj.__module__ == module.__name__):
                        command_classes.append(obj)
                        
            except Exception as e:
                self.logger.error(f"Error loading command module {file.name}: {str(e)}")
                
        return command_classes

    def _register_commands(self):
        """Register all discovered command classes."""
        command_classes = self._discover_command_classes()
        for command_class in command_classes:
            try:
                self.registry.register(command_class())
            except Exception as e:
                self.logger.error(f"Error registering command {command_class.__name__}: {str(e)}")

    async def handle_command(self, command: str, channel_id: str) -> str:
        """Handle incoming commands and route to appropriate method"""
        full_command = command[1:].strip()  # Remove $ and trim
        parts = full_command.split(maxsplit=1)
        base_command = parts[0].lower()
        
        command_handler = self.registry.get_command(base_command)
        if command_handler:
            return await command_handler.execute(
                channel_id=channel_id,
                command=command,
                messages=None,
                api=self.api,
                model_id=self.model_id
            )
        
        return "*Not a valid command*"
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
