# Luna - AI Discord Assistant

Luna is an independent AI assistant for Discord that responds naturally to mentions and replies. It uses OpenRouter to access both real-time data (via Perplexity) and core AI (via Gemini).

## Features

- **Natural Conversation**: Just mention @Luna or reply to her messages
- **Smart Model Selection**: Automatically switches between models based on your question
- **Real-time Information**: Uses Perplexity for current events, weather, news, etc.
- **General Knowledge**: Uses Gemini for questions that don't require real-time data

## Setup

1. Update the `.env` file with your Discord token and OpenRouter API key
2. Install dependencies: `pip install -r requirements.txt`
3. Run the bot: `python bot.py`

## Environment Variables

- `DISCORD_TOKEN`: Your Discord bot token
- `OPENROUTER_API_KEY`: Your OpenRouter API key

## How to Get API Keys

1. Discord Bot Token:
   - Go to the [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application
   - Go to the "Bot" tab and click "Add Bot"
   - Copy the token and add it to your `.env` file
   - Enable "MESSAGE CONTENT INTENT" under Privileged Gateway Intents
   
2. OpenRouter API Key:
   - Sign up on [OpenRouter](https://openrouter.ai)
   - Get your API key from your account dashboard
   - Add it to your `.env` file

## Adding the Bot to Your Server

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your application
3. Go to the "OAuth2" tab
4. In URL Generator, select the "bot" scope
5. Select permissions: "Send Messages", "Read Message History", etc.
6. Copy the generated URL and open it in your browser
7. Select your Discord server and authorize the bot
