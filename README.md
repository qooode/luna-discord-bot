# Luna - AI Discord Assistant

Luna is an intelligent Discord bot that combines AI conversation capabilities with advanced temporary channel management and chat summarization features.

## 🤖 Core Features

### AI Conversation
- **Natural Conversation**: Just mention @Luna or reply to her messages
- **Smart Model Selection**: Automatically switches between models based on your question
- **Real-time Information**: Uses Perplexity for current events, weather, news, etc.
- **General Knowledge**: Uses Gemini for questions that don't require real-time data
- **Context Awareness**: Remembers recent conversation history for better responses
- **Link Processing**: Automatically handles Twitter/X links

### Channel Management  
- **Enable/Disable Controls**: Use `/luna` commands to control where Luna responds
- **Per-channel Settings**: Enable Luna in specific channels while keeping others quiet
- **Global Controls**: Turn Luna on/off everywhere with simple commands

## ⏰ Temporary Channels

### Channel Creation
- **Flexible Durations**: 5min, 10min, 15min, 30min, 45min, 1h, 1h30m, 2h, 3h, 4h, 6h, 8h, 12h, 24h
- **Public & Private**: Create channels anyone can join or invite-only private spaces
- **Smart Naming**: Channels named as `⏰・topic-duration` with live countdown timers
- **Auto-cleanup**: Channels automatically delete when expired or inactive

### Channel Management
- **Live Countdown**: Channel names update to show remaining time (every 5 minutes)
- **Smart Notifications**: Get warnings before channels expire or become inactive
- **Extension Options**: React with 🕐 (+5min), 🕙 (+10min), or 🕞 (+30min) to extend
- **Private Channel Controls**: Invite users with `/invite` or kick with `/kick`
- **Manual Closure**: Close channels anytime with `/tempclose`

### Anti-Spam & Limits
- **User Limits**: Maximum 2 temp channels per user
- **Cooldown**: 5-minute cooldown between channel creations  
- **Smart Inactivity**: Channels deleted after appropriate inactivity periods
- **Permission Inheritance**: Channels inherit category permissions for bot control

### Admin Controls
- **Global Toggle**: Admins can enable/disable temp channels with `/tempon` and `/tempoff`
- **Override Permissions**: Admins can close any temp channel, even if they didn't create it

## 📝 Chat Summarization

- **Smart Summarization**: `/summarize` creates bullet-point summaries of recent messages
- **Customizable Count**: Summarize 10-500 messages (default: 100)
- **Intelligent Filtering**: Skips commands, bot messages, and very short responses
- **Message Links**: Click to jump to specific messages in the summary
- **Pagination**: Long summaries are paginated for easy reading

## 🎛️ Commands

### Public Commands
- `/help` - Show all available commands and features
- `/luna <option>` - Control Luna's behavior (listen/quiet in channels)
- `/summarize [count]` - Summarize recent chat messages
- `/temp <topic> <type> <duration>` - Create temporary channels
- `/invite <user>` - Invite someone to your private temp channel
- `/kick <user>` - Remove someone from your private temp channel  
- `/tempclose` - Close your temp channel
- `/templist` - List your active temp channels

### Admin Commands
- `/tempon` - Enable temporary channels feature
- `/tempoff` - Disable temporary channels feature

## 🚀 Setup

### Prerequisites
- Python 3.8+
- Discord Bot Token
- OpenRouter API Key

### Installation
1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Update the `.env` file with your tokens
4. Run the bot: `python bot.py`

### Environment Variables
```env
DISCORD_TOKEN=your_discord_bot_token
OPENROUTER_API_KEY=your_openrouter_api_key
```

## 🔑 Getting API Keys

### Discord Bot Token
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to the "Bot" tab and click "Add Bot"
4. Copy the token and add it to your `.env` file
5. Enable "MESSAGE CONTENT INTENT" under Privileged Gateway Intents

### OpenRouter API Key
1. Sign up on [OpenRouter](https://openrouter.ai)
2. Get your API key from your account dashboard
3. Add it to your `.env` file

## 🔐 Required Bot Permissions

### Basic Permissions
- **Send Messages** - For AI responses and notifications
- **Read Message History** - For context and summarization
- **Use Slash Commands** - For all bot commands
- **Add Reactions** - For extension features

### Temp Channel Permissions
- **Manage Channels** - Create, delete, and modify temp channels
- **Manage Roles** - Set user permissions for private channels
- **View Channels** - Access channels for management

## 📋 Adding Bot to Server

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your application
3. Go to the "OAuth2" > "URL Generator" tab
4. Select scopes: `bot` and `applications.commands`
5. Select permissions: `Manage Channels`, `Manage Roles`, `Send Messages`, `Read Message History`, `Use Slash Commands`, `Add Reactions`
6. Copy the generated URL and open it in your browser
7. Select your Discord server and authorize the bot

## 💡 Usage Examples

### AI Conversation
```
@Luna what's the weather like in Tokyo?
@Luna explain quantum computing
```

### Temporary Channels
```
/temp debug session public 1h
/temp planning meeting private 30min
/temp game night public 3h
```

### Chat Management
```
/luna listen here
/luna be quiet everywhere  
/summarize count:200
```

## 🛠️ Advanced Configuration

### Category Permissions
- Create a "Temp Channels" category
- Set permissions on the category to control bot access
- Temp channels automatically inherit category permissions
- Useful for excluding moderation bots from temp channels

### Customization
- Modify duration options in `bot.py`
- Adjust cooldown periods in `temp_channels.py`
- Change timer update frequency (currently every 5 minutes)

## 📝 License

This project is open source. Feel free to modify and distribute as needed.