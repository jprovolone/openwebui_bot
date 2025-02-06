# Bot
Clone repo
```git clone this repo```
Install requirements
```pip install -r requirements.txt```
*Note that this does require another unreleased python package link here*
Setup env
```cp .envexample .env```
Run
```python3 -m bot.main```

## Creating a command
In the commands directory, create a file and import base_command.py
```from bot.commands.base_command import BaseCommand```
Create a new class for your command and inherit the BaseCommand class
```
class HelpCommand(BaseCommand):
    def __init__(self):
        super().__init__("help", "List all available commands and their descriptions")

    async def execute(self, channel_id: str, command: str = "", messages: Dict = None, api = None, model_id: str = "") -> str:
        help_text = "Available commands:\n\n"
        # Get commands from the registry through the parent Commands instance
        from bot import commands
        registry = commands.Commands(messages, api, "", model_id).registry
        for cmd in registry.get_all_commands().values():
            help_text += f"${cmd.name}: {cmd.description}\n"
        return f"```\n{help_text}```"
```
---
# open-webui/bot

This repository provides an experimental boilerplate for building bots compatible with the **Open WebUI** "Channels" feature (introduced in version 0.5.0). It serves as a proof of concept to demonstrate bot-building capabilities while highlighting the potential of asynchronous communication enabled by Channels. 

## ⚡ Key Highlights
- **Highly Experimental**: This is an early-stage project showcasing basic bot-building functionality. Expect major API changes in the future.
- **Extensible Framework**: Designed as a foundation for further development, with plans to enhance APIs, developer tooling, and usability.
- **Asynchronous Communication**: Leverages Open WebUI Channels for event-driven workflows.

## 🚧 Disclaimer
This project is an early-stage proof of concept. **APIs will break** and existing functionality may change as Open WebUI evolves to include native bot support. This repository is not production-ready and primarily serves experimental and exploratory purposes.

## 🎯 Future Vision
We aim to introduce improved APIs, enhanced developer tooling, and seamless native support for bots directly within Open WebUI. The ultimate goal is to make building bots easier, faster, and more intuitive.

---
Contributions, feedback, and experimentation are encouraged. Join us in shaping the future of bot-building on Open WebUI!