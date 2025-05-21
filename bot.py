import discord
import os
import re
from dotenv import load_dotenv
from discord import app_commands
from ai_handler import get_ai_response
from link_handler import handle_links

# Load environment variables
load_dotenv()

# Get Discord token from environment variables
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Set up intents
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

# Create bot instance with command support
class LunaBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        # Settings to track enabled/disabled state
        self.is_globally_enabled = True
        self.disabled_channels = set()
        # Channels that should be enabled even if global is off
        self.always_enabled_channels = set()
        
    async def setup_hook(self):
        # This is called when the bot is ready
        await self.tree.sync()

# Initialize the bot
client = LunaBot()

@client.event
async def on_ready():
    print(f'Luna has connected to Discord!')
    # Set the bot's activity
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="@Luna"))
    
# Natural conversational commands for Luna
@client.tree.command(name="luna", description="Talk to Luna directly with commands")
@app_commands.choices(command=[
    app_commands.Choice(name="listen here", value="listen_here"),
    app_commands.Choice(name="be quiet here", value="quiet_here"),
    app_commands.Choice(name="listen everywhere", value="listen_everywhere"),
    app_commands.Choice(name="be quiet everywhere", value="quiet_everywhere"),
    app_commands.Choice(name="how are you feeling", value="status")
])
async def luna_command(interaction: discord.Interaction, command: app_commands.Choice[str]):
    channel_id = interaction.channel_id
    
    if command.value == "listen_here":
        # Remove this channel from disabled list AND add to always_enabled list
        if channel_id in client.disabled_channels:
            client.disabled_channels.remove(channel_id)
        # Add to explicitly enabled channels that override global settings
        client.always_enabled_channels.add(channel_id)
        await interaction.response.send_message("Sure, I'll start listening in this channel again! 👋", ephemeral=True)
        
    elif command.value == "quiet_here":
        # Add this channel to disabled list AND remove from always_enabled
        client.disabled_channels.add(channel_id)
        if channel_id in client.always_enabled_channels:
            client.always_enabled_channels.remove(channel_id)
        await interaction.response.send_message("Got it, I'll be quiet in this channel for now. 🤐", ephemeral=True)
        
    elif command.value == "listen_everywhere":
        client.is_globally_enabled = True
        client.disabled_channels.clear()  # Clear all channel restrictions
        client.always_enabled_channels.clear()  # Clear always enabled channels since global is on
        await interaction.response.send_message("I'll start listening in all channels now! 👋", ephemeral=True)
        
    elif command.value == "quiet_everywhere":
        client.is_globally_enabled = False
        # Keep always_enabled_channels intact so those override the global setting
        await interaction.response.send_message("I'll be quiet everywhere except where you've specifically asked me to listen. 🤐", ephemeral=True)
        
    elif command.value == "status":
        global_status = "listening" if client.is_globally_enabled else "staying quiet"
        
        # Channel is active if:
        # 1. It's in always_enabled_channels list (overrides everything) OR
        # 2. Global is enabled AND it's not in disabled_channels
        is_enabled_here = (channel_id in client.always_enabled_channels) or \
                       (client.is_globally_enabled and channel_id not in client.disabled_channels)
        
        channel_status = "listening" if is_enabled_here else "staying quiet"
        
        await interaction.response.send_message(
            f"Hey there! Currently I'm **{global_status}** globally, but **{channel_status}** in this channel.\n\n" 
            f"**{'I can hear you in this channel!' if is_enabled_here else 'I cannot hear you in this channel right now.'}**",
            ephemeral=True
        )

async def fetch_message_history(channel, current_user_id, limit=25):
    """
    Fetch recent messages from a channel and format them for context analysis.
    Returns a list of message dictionaries with content and metadata.
    
    Messages are returned in chronological order (oldest first), which is
    better for establishing conversational context.
    
    Default limit is 25 messages for performance.
    Prioritizes relevant conversation threads involving Luna and the current user.
    """
    try:
        # First collect messages in reverse order (newest first)
        raw_messages = []
        
        # First pass: get recent messages to analyze
        async for msg in channel.history(limit=limit):
            raw_messages.append(msg)
            
        # Prioritize messages that are part of conversations with the bot or from current user
        relevant_messages = []
        
        for msg in raw_messages:
            # Always include bot messages
            if msg.author.id == client.user.id:
                relevant_messages.append(msg)
            # Always include current user's messages
            elif msg.author.id == current_user_id:
                relevant_messages.append(msg)
            # Include messages that mention the bot
            elif client.user.mentioned_in(msg):
                relevant_messages.append(msg)
            # Include replies to the bot
            elif msg.reference and msg.reference.resolved and msg.reference.resolved.author.id == client.user.id:
                relevant_messages.append(msg)
        
        # If we have enough relevant messages, use only those; otherwise use all collected messages
        if len(relevant_messages) >= 10:
            raw_messages = relevant_messages
        
        # Convert to chronological order (oldest first) for better context analysis
        raw_messages.reverse()
        
        # Process messages to extract content and useful metadata
        message_history = []
        for msg in raw_messages:
            # Skip empty messages
            if not msg.content.strip():
                continue
                
            # Get reply reference if this message is a reply
            reference_info = ""
            if msg.reference and hasattr(msg.reference, 'resolved') and msg.reference.resolved:
                ref_msg = msg.reference.resolved
                # Only include a few characters of the referenced message
                ref_content = ref_msg.content[:50] + "..." if len(ref_msg.content) > 50 else ref_msg.content
                reference_info = f" [replying to: {ref_msg.author.name}: {ref_content}]"
                
            # Get mentions if any
            mentions = []
            if msg.mentions:
                mentions = [user.name for user in msg.mentions]
                
            # Mark if this is the current requester with an indicator
            user_indicator = "[CURRENT USER]" if msg.author.id == current_user_id else ""
            
            # Modify content to clearly prefix with username and mark current user
            formatted_content = f"[{msg.author.name}{user_indicator}]: {msg.content}{reference_info}"
            
            # Create a rich dict representation of each message
            message_history.append({
                'content': formatted_content,
                'author_id': msg.author.id,
                'author_name': msg.author.name,
                'timestamp': msg.created_at.isoformat(),
                'message_id': msg.id,
                'is_bot': msg.author.bot,
                'is_current_requester': msg.author.id == current_user_id, # Tag if this is from the current requester
                'mentions': mentions,
                'is_reply': bool(msg.reference and hasattr(msg.reference, 'resolved') and msg.reference.resolved)
            })
            
        return message_history
    except Exception as e:
        print(f"Error fetching message history: {e}")
        return []

@client.event
async def on_message(message):
    # Don't respond to our own messages
    if message.author == client.user:
        return
    
    # First, check for x.com or twitter.com links
    await handle_links(message)
        
    # Check if Luna is enabled for this channel
    channel_id = message.channel.id
    
    # Logic for determining if Luna should respond:
    # 1. If channel is in always_enabled_channels, Luna WILL respond regardless of global setting
    # 2. If channel is in disabled_channels, Luna will NOT respond regardless of global setting
    # 3. Otherwise, use the global setting
    
    # Channel explicitly enabled (overrides everything)
    if channel_id in client.always_enabled_channels:
        pass  # Luna will respond
    # Channel explicitly disabled (overrides global enabled)
    elif channel_id in client.disabled_channels:
        print(f"Luna ignoring message in channel {channel_id} (explicitly disabled in this channel)")
        return
    # Global setting applies
    elif not client.is_globally_enabled:
        print(f"Luna ignoring message in channel {channel_id} (globally disabled and not in always_enabled)")
        return
    
    # Only respond to direct mentions or replies
    bot_mentioned = client.user.mentioned_in(message)
    is_reply_to_luna = message.reference and message.reference.resolved and message.reference.resolved.author == client.user
    
    if not (bot_mentioned or is_reply_to_luna):
        return
    
    # Remove the mention from the content if it exists
    content = re.sub(f'<@!?{client.user.id}>', '', message.content).strip()
    
    # If the message is empty after removing the mention, don't respond
    if not content:
        return
    
    async with message.channel.typing():
        try:
            # Smart context fetching - start with a small batch of well-prioritized messages
            previous_messages = await fetch_message_history(message.channel, message.author.id)
            message_count = len(previous_messages)
            
            # Only use messages that are actually relevant to this conversation
            # Filter out system messages and keep the conversation focused
            filtered_messages = []
            for msg in previous_messages:
                # Skip messages that are just bot commands or system notifications
                if msg['content'].startswith('!') or msg['content'].startswith('/'): 
                    continue
                # Add all messages from current user or Luna
                if msg['is_bot'] or msg['is_current_requester']:
                    filtered_messages.append(msg)
                # Add any message directly part of this conversation thread
                elif any(client.user.name in msg['content'] for mentions in msg.get('mentions', [])) or msg.get('is_reply', False):
                    filtered_messages.append(msg)
            
            # If we have a good number of relevant messages, use those; otherwise fall back to all messages
            if len(filtered_messages) >= 5:
                print(f"Filtered to {len(filtered_messages)} highly relevant messages from {message_count} total")
                previous_messages = filtered_messages
            else:
                print(f"Using all {message_count} messages for context analysis - limited relevant context found")
            
            # Get AI response - Luna will analyze context and decide if online data is needed
            response = get_ai_response(content, previous_messages=previous_messages)
            
            await send_long_message(message.channel, response, message)
        except Exception as e:
            await message.reply(f"❌ Error: {str(e)}")

async def send_long_message(message_channel, text, reference_message):
    MAX_LENGTH = 2000
    if len(text) <= MAX_LENGTH:
        await reference_message.reply(text)
        return

    chunks = []
    current_chunk = ""
    for paragraph in text.split('\n\n'): # Try to split by paragraphs first
        if len(current_chunk) + len(paragraph) + 2 > MAX_LENGTH:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = paragraph
            # If a single paragraph is too long, it will be force-split later
            while len(current_chunk) > MAX_LENGTH:
                # This would be rare with Luna's new persona (very brief responses), but let's handle it anyway
                split_point = current_chunk.rfind(' ', 0, MAX_LENGTH - 3) # find last space before limit, leave room for ...
                if split_point == -1: # no space found, hard split
                    split_point = MAX_LENGTH - 3
                chunks.append(current_chunk[:split_point] + "...")
                current_chunk = "..." + current_chunk[split_point:]
        else:
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph
    
    if current_chunk: # Add the last chunk
        chunks.append(current_chunk)

    if not chunks: # Should not happen if text was > MAX_LENGTH, but as a safe guard
        await reference_message.reply(text) # try sending as is
        return

    first = True
    for chunk in chunks:
        if first:
            await reference_message.reply(chunk)
            first = False
        else:
            await message_channel.send(chunk)

# Run the client
client.run(DISCORD_TOKEN)
