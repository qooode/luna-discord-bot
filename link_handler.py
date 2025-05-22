import re
import discord

# Regex pattern to match x.com, twitter.com, reddit.com, and tiktok.com links
LINK_PATTERNS = [
    re.compile(r'https?://(www\.)?(x|twitter)\.com/\S+'),
    re.compile(r'https?://(www\.)?reddit\.com/\S+'),
    re.compile(r'https?://(www\.|vm\.)?tiktok\.com/\S+')
]

REPLACEMENTS = {
    "x.com": "fxtwitter.com",
    "twitter.com": "fxtwitter.com",
    "reddit.com": "rxddit.com",
    "tiktok.com": "tnktok.com",
    "vm.tiktok.com": "tnktok.com" # Handle short TikTok links
}

async def handle_links(message):
    """
    Detect x.com, twitter.com, reddit.com, or tiktok.com links in messages 
    and post enhanced versions (e.g., fxtwitter, rxddit, tnktok).
    Keeps the original message but suppresses its embeds so people can still reply to the user.
    """
    # Don't process messages from bots (including self)
    if message.author.bot:
        return
    
    content = message.content
    found_links_to_process = False
    
    # Check if any of the patterns match
    for pattern in LINK_PATTERNS:
        if pattern.search(content):
            found_links_to_process = True
            break
            
    if not found_links_to_process:
        return
    
    try:
        # Extract all matching links from the message content
        all_extracted_links = []
        for pattern in LINK_PATTERNS:
            for match in pattern.finditer(content):
                all_extracted_links.append(match.group(0))
        
        if not all_extracted_links:
            return

        new_links_messages = []
        
        for original_link in all_extracted_links:
            new_link = original_link
            for domain, replacement_domain in REPLACEMENTS.items():
                if domain in new_link:
                    # Preserve the www. if it exists, unless it's vm.tiktok.com
                    if "www." in new_link and domain != "vm.tiktok.com":
                         new_link = new_link.replace("www." + domain, replacement_domain)
                    else:
                         new_link = new_link.replace(domain, replacement_domain)
                    break # Stop after first replacement for this link
            new_links_messages.append(new_link)

        if not new_links_messages:
            return

        # Create a message mentioning who sent the original links
        response_message_content = f"**{message.author.display_name}** shared:\n"
        response_message_content += "\n".join(new_links_messages)
        
        # Suppress embeds in the original message
        await message.edit(suppress=True)
        
        # Send the new message with the enhanced links
        await message.channel.send(response_message_content)
        
        print(f"Posted {len(new_links_messages)} enhanced links for {message.author.display_name}'s message and suppressed original embeds")
        
    except discord.errors.NotFound:
        # This can happen if the original message is deleted before we can edit it (e.g., by another bot or the user)
        print(f"Could not edit message {message.id} to suppress embeds, it might have been deleted.")
        # Still try to send the enhanced links
        if new_links_messages:
            response_message_content = f"**{message.author.display_name}** shared (original message was deleted before embeds could be suppressed):\n"
            response_message_content += "\n".join(new_links_messages)
            await message.channel.send(response_message_content)
            print(f"Posted {len(new_links_messages)} enhanced links for {message.author.display_name}'s message (original deleted).")

    except Exception as e:
        print(f"Error in link_handler: {str(e)} for message ID {message.id}") 