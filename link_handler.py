import re
import discord

# Regex pattern to match x.com and twitter.com links
X_PATTERN = re.compile(r'https?://(www\.)?(x|twitter)\.com/\S+')

async def handle_links(message):
    """
    Detect x.com or twitter.com links in messages and post fxtwitter.com versions
    without deleting the original message so people can still reply to the user.
    """
    # Don't process messages from bots (including self)
    if message.author.bot:
        return
    
    # Check if message contains x.com or twitter.com links
    content = message.content
    matches = X_PATTERN.findall(content)
    
    if not matches:
        return
    
    try:
        # Extract the original full URLs from the message content
        links = []
        for match in X_PATTERN.finditer(content):
            full_url = match.group(0)  # This gets the entire matched URL
            links.append(full_url)
        
        # If no links were found, return
        if not links:
            return
        
        # Create new links with fxtwitter.com
        new_links = []
        for link in links:
            # Replace x.com or twitter.com with fxtwitter.com
            new_link = re.sub(r'(www\.)?(x|twitter)\.com', 'fxtwitter.com', link)
            new_links.append(new_link)
        
        # Create a message mentioning who sent the original links
        new_message = f"**{message.author.display_name}** shared:\n"
        for new_link in new_links:
            new_message += f"{new_link}\n"
        
        # Send the new message without deleting the original
        await message.channel.send(new_message)
        
        print(f"Posted {len(new_links)} fxtwitter links for {message.author.display_name}'s message")
        
    except Exception as e:
        print(f"Error in link_handler: {str(e)}") 