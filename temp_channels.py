import discord
import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class TempChannelManager:
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "temp_channels.json"
        self.temp_channels: Dict[int, dict] = {}
        self.user_cooldowns: Dict[int, datetime] = {}
        self.cleanup_task = None
        self.warned_channels: set = set()  # Track channels that got 5-min warning
        self.load_data()
    
    def load_data(self):
        """Load temp channel data from file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    # Convert string timestamps back to datetime objects
                    for channel_id, channel_data in data.items():
                        channel_data['created_at'] = datetime.fromisoformat(channel_data['created_at'])
                        channel_data['expires_at'] = datetime.fromisoformat(channel_data['expires_at'])
                        if channel_data.get('last_activity'):
                            channel_data['last_activity'] = datetime.fromisoformat(channel_data['last_activity'])
                        self.temp_channels[int(channel_id)] = channel_data
        except Exception as e:
            print(f"Error loading temp channel data: {e}")
    
    def save_data(self):
        """Save temp channel data to file"""
        try:
            # Convert datetime objects to ISO format strings
            data = {}
            for channel_id, channel_data in self.temp_channels.items():
                data[str(channel_id)] = {
                    **channel_data,
                    'created_at': channel_data['created_at'].isoformat(),
                    'expires_at': channel_data['expires_at'].isoformat(),
                    'last_activity': channel_data.get('last_activity', datetime.now()).isoformat()
                }
            
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving temp channel data: {e}")
    
    def start_cleanup_task(self):
        """Start the background cleanup task"""
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self.cleanup_loop())
    
    async def cleanup_loop(self):
        """Background task to clean up expired channels"""
        while True:
            try:
                await self.cleanup_expired_channels()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                print(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)
    
    async def cleanup_expired_channels(self):
        """Remove expired or inactive channels"""
        now = datetime.now()
        channels_to_remove = []
        
        for channel_id, data in self.temp_channels.items():
            channel = self.bot.get_channel(channel_id)
            
            # Channel doesn't exist anymore
            if not channel:
                channels_to_remove.append(channel_id)
                continue
            
            # Check for 5-minute expiration warning
            time_until_expiry = data['expires_at'] - now
            if time_until_expiry <= timedelta(minutes=5) and channel_id not in self.warned_channels:
                await self.send_expiration_warning(channel, time_until_expiry)
                self.warned_channels.add(channel_id)
            
            # Check if channel expired by time
            if now >= data['expires_at']:
                await self.delete_temp_channel(channel_id, "⏰ Time's up!")
                channels_to_remove.append(channel_id)
                continue
            
            # Check if channel is inactive (no activity for 10 minutes)
            last_activity = data.get('last_activity', data['created_at'])
            time_since_activity = now - last_activity
            
            # Send inactivity warning at 5 minutes of inactivity
            if time_since_activity >= timedelta(minutes=5) and time_since_activity < timedelta(minutes=10):
                if not data.get('inactivity_warned', False):
                    await self.send_inactivity_warning(channel)
                    self.temp_channels[channel_id]['inactivity_warned'] = True
            
            # Delete after 10 minutes of inactivity
            if time_since_activity >= timedelta(minutes=10):
                # Check if channel is empty
                if len(channel.members) == 0:
                    await self.delete_temp_channel(channel_id, "💤 Channel deleted due to inactivity")
                    channels_to_remove.append(channel_id)
                    continue
        
        # Remove deleted channels from tracking
        for channel_id in channels_to_remove:
            if channel_id in self.temp_channels:
                del self.temp_channels[channel_id]
            if channel_id in self.warned_channels:
                self.warned_channels.remove(channel_id)
        
        if channels_to_remove:
            self.save_data()
    
    async def delete_temp_channel(self, channel_id: int, reason: str):
        """Delete a temp channel with a reason"""
        try:
            channel = self.bot.get_channel(channel_id)
            if channel:
                # Send farewell message
                try:
                    await channel.send(f"{reason}")
                    await asyncio.sleep(2)  # Let users see the message
                except:
                    pass
                
                try:
                    await channel.delete(reason=reason)
                    print(f"Deleted temp channel: {channel.name} - {reason}")
                except discord.Forbidden:
                    print(f"Error deleting temp channel {channel_id}: Missing permissions. Bot needs 'Manage Channels' permission.")
                except Exception as e:
                    print(f"Error deleting temp channel {channel_id}: {e}")
        except Exception as e:
            print(f"Error deleting temp channel {channel_id}: {e}")
    
    async def send_expiration_warning(self, channel: discord.TextChannel, time_left: timedelta):
        """Send warning when channel is about to expire"""
        try:
            minutes_left = int(time_left.total_seconds() / 60)
            if minutes_left <= 0:
                return
            
            embed = discord.Embed(
                title="⚠️ Channel Expiring Soon",
                description=f"This channel will be deleted in **{minutes_left} minute{'s' if minutes_left != 1 else ''}**!",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="Want to extend?", 
                value="React with ⏰ to add 30 more minutes", 
                inline=False
            )
            
            message = await channel.send(embed=embed)
            await message.add_reaction("⏰")
            
            # Store message ID for reaction handling
            if channel.id in self.temp_channels:
                self.temp_channels[channel.id]['warning_message_id'] = message.id
                
        except Exception as e:
            print(f"Error sending expiration warning: {e}")
    
    async def send_inactivity_warning(self, channel: discord.TextChannel):
        """Send warning when channel is inactive"""
        try:
            embed = discord.Embed(
                title="💤 Channel Inactive",
                description="This channel will be deleted in **5 minutes** due to inactivity.",
                color=discord.Color.red()
            )
            embed.add_field(
                name="Keep it alive", 
                value="Send a message to reset the timer", 
                inline=False
            )
            
            await channel.send(embed=embed)
            
        except Exception as e:
            print(f"Error sending inactivity warning: {e}")
    
    async def extend_channel(self, channel_id: int, user_id: int) -> str:
        """Extend a channel by 30 minutes"""
        if channel_id not in self.temp_channels:
            return "❌ This is not a temp channel!"
        
        channel_data = self.temp_channels[channel_id]
        
        # Check if user is the creator
        if channel_data['creator_id'] != user_id:
            return "❌ Only the channel creator can extend the channel!"
        
        # Extend by 30 minutes
        self.temp_channels[channel_id]['expires_at'] += timedelta(minutes=30)
        
        # Reset warning status
        if channel_id in self.warned_channels:
            self.warned_channels.remove(channel_id)
        
        # Update channel topic
        channel = self.bot.get_channel(channel_id)
        if channel:
            new_expires_at = self.temp_channels[channel_id]['expires_at']
            time_left = new_expires_at - datetime.now()
            hours, remainder = divmod(int(time_left.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
            
            try:
                await channel.edit(topic=f"⏰ {time_str} remaining | Created by {channel_data['creator_name']}")
            except:
                pass
        
        self.save_data()
        return "✅ Channel extended by 30 minutes!"
    
    def parse_duration(self, duration_str: str) -> Optional[timedelta]:
        """Parse duration string to timedelta"""
        duration_map = {
            '15min': timedelta(minutes=15),
            '30min': timedelta(minutes=30),
            '1h': timedelta(hours=1),
            '2h': timedelta(hours=2),
            '6h': timedelta(hours=6),
            '12h': timedelta(hours=12),
            '24h': timedelta(hours=24)
        }
        return duration_map.get(duration_str.lower())
    
    def get_user_channels(self, user_id: int) -> List[int]:
        """Get list of channels owned by user"""
        return [ch_id for ch_id, data in self.temp_channels.items() 
                if data['creator_id'] == user_id]
    
    def is_user_on_cooldown(self, user_id: int) -> bool:
        """Check if user is on cooldown"""
        if user_id in self.user_cooldowns:
            return datetime.now() < self.user_cooldowns[user_id]
        return False
    
    def set_user_cooldown(self, user_id: int):
        """Set cooldown for user"""
        self.user_cooldowns[user_id] = datetime.now() + timedelta(minutes=5)
    
    async def create_temp_channel(self, guild: discord.Guild, creator: discord.Member, 
                                topic: str, channel_type: str, duration: str) -> Optional[discord.TextChannel]:
        """Create a new temporary channel"""
        try:
            # Check user limits
            if len(self.get_user_channels(creator.id)) >= 2:
                return None, "❌ You already have 2 temp channels! Close one first."
            
            # Check cooldown
            if self.is_user_on_cooldown(creator.id):
                return None, "⏰ You're on cooldown! Wait 5 minutes between channel creations."
            
            # Parse duration
            duration_delta = self.parse_duration(duration)
            if not duration_delta:
                return None, "❌ Invalid duration! Use: 15min, 30min, 1h, 2h, 6h, 12h, 24h"
            
            # Find or create temp channels category
            category = discord.utils.get(guild.categories, name="Temp Channels")
            if not category:
                category = await guild.create_category("Temp Channels")
            
            # Create channel name
            channel_name = f"temp-{topic.replace(' ', '-')}-{creator.display_name}".lower()
            
            # Set up permissions
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=channel_type == 'public'),
                creator: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True),
                self.bot.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True, manage_channels=True)
            }
            
            # Create the channel
            expires_at = datetime.now() + duration_delta
            topic_text = f"⏰ Expires in {duration} | Created by {creator.display_name}"
            
            channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=topic_text
            )
            
            # Track the channel
            self.temp_channels[channel.id] = {
                'creator_id': creator.id,
                'creator_name': creator.display_name,
                'topic': topic,
                'type': channel_type,
                'duration': duration,
                'created_at': datetime.now(),
                'expires_at': expires_at,
                'last_activity': datetime.now()
            }
            
            # Set cooldown
            self.set_user_cooldown(creator.id)
            
            # Save data
            self.save_data()
            
            # Send welcome message
            await channel.send(f"**{topic}** - Created by {creator.mention}\n"
                             f"⏰ This channel will be deleted in **{duration}** or after **10 minutes** of inactivity.\n"
                             f"{'🔒 This is a private channel. Use `/invite @user` to add people.' if channel_type == 'private' else '🌍 This is a public channel - anyone can join!'}")
            
            return channel, None
            
        except Exception as e:
            print(f"Error creating temp channel: {e}")
            return None, f"❌ Error creating channel: {str(e)}"
    
    async def invite_user_to_channel(self, channel_id: int, inviter_id: int, target_user: discord.Member) -> str:
        """Invite a user to a private temp channel"""
        if channel_id not in self.temp_channels:
            return "❌ This is not a temp channel!"
        
        channel_data = self.temp_channels[channel_id]
        
        # Check if user is the creator
        if channel_data['creator_id'] != inviter_id:
            return "❌ Only the channel creator can invite users!"
        
        # Check if channel is private
        if channel_data['type'] != 'private':
            return "❌ This is a public channel - anyone can join!"
        
        # Get the channel
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return "❌ Channel not found!"
        
        # Add permission for the user
        try:
            await channel.set_permissions(target_user, read_messages=True, send_messages=True)
        except discord.Forbidden:
            return f"❌ I don't have permission to invite users to this channel. Make sure I have 'Manage Channels' permission!"
        except Exception as e:
            return f"❌ Error inviting user: {str(e)}"
        
        # Update activity
        self.temp_channels[channel_id]['last_activity'] = datetime.now()
        self.save_data()
        
        return f"✅ {target_user.mention} has been invited to the channel!"
    
    async def kick_user_from_channel(self, channel_id: int, kicker_id: int, target_user: discord.Member) -> str:
        """Kick a user from a private temp channel"""
        if channel_id not in self.temp_channels:
            return "❌ This is not a temp channel!"
        
        channel_data = self.temp_channels[channel_id]
        
        # Check if user is the creator
        if channel_data['creator_id'] != kicker_id:
            return "❌ Only the channel creator can kick users!"
        
        # Check if channel is private
        if channel_data['type'] != 'private':
            return "❌ You can only kick users from private channels!"
        
        # Can't kick yourself
        if target_user.id == kicker_id:
            return "❌ You can't kick yourself! Use `/tempclose` to close the channel instead."
        
        # Get the channel
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return "❌ Channel not found!"
        
        # Remove permissions for the user
        try:
            await channel.set_permissions(target_user, overwrite=None)  # Remove specific permissions
        except discord.Forbidden:
            return f"❌ I don't have permission to kick users from this channel. Make sure I have 'Manage Channels' permission!"
        except Exception as e:
            return f"❌ Error kicking user: {str(e)}"
        
        # Update activity
        self.temp_channels[channel_id]['last_activity'] = datetime.now()
        self.save_data()
        
        return f"✅ {target_user.mention} has been kicked from the channel!"
    
    async def update_channel_activity(self, channel_id: int):
        """Update last activity for a channel"""
        if channel_id in self.temp_channels:
            self.temp_channels[channel_id]['last_activity'] = datetime.now()
            # Reset inactivity warning flag
            if 'inactivity_warned' in self.temp_channels[channel_id]:
                del self.temp_channels[channel_id]['inactivity_warned']
            # Don't save on every message - let the cleanup task handle it
    
    async def close_channel(self, channel_id: int, user_id: int):
        """Close a temp channel manually"""
        if channel_id not in self.temp_channels:
            return False, "❌ This is not a temp channel!"
        
        channel_data = self.temp_channels[channel_id]
        
        # Check if user is the creator
        if channel_data['creator_id'] != user_id:
            return False, "❌ Only the channel creator can close the channel!"
        
        # Delete the channel
        await self.delete_temp_channel(channel_id, "Channel closed by creator")
        
        # Clean up tracking data
        if channel_id in self.temp_channels:
            del self.temp_channels[channel_id]
        if channel_id in self.warned_channels:
            self.warned_channels.remove(channel_id)
        
        self.save_data()
        return True, "✅ Channel will be closed!"
    
    def get_user_channel_list(self, user_id: int) -> str:
        """Get formatted list of user's channels"""
        user_channels = self.get_user_channels(user_id)
        if not user_channels:
            return "You don't have any temp channels."
        
        channel_list = []
        for channel_id in user_channels:
            data = self.temp_channels[channel_id]
            channel = self.bot.get_channel(channel_id)
            if channel:
                time_left = data['expires_at'] - datetime.now()
                hours, remainder = divmod(int(time_left.total_seconds()), 3600)
                minutes, _ = divmod(remainder, 60)
                time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
                
                channel_list.append(f"**{data['topic']}** - {time_str} left ({data['type']})")
        
        return "\n".join(channel_list) if channel_list else "You don't have any temp channels."