import os
import importlib
from pathlib import Path
from .command_registry import Command, CommandRegistry

# Automatically import all command modules in this directory
commands_dir = Path(__file__).parent
for file in commands_dir.glob("*_commands.py"):
    module_name = f"bot.commands.{file.stem}"
    importlib.import_module(module_name)

# Export the registry classes
__all__ = ['Command', 'CommandRegistry']
