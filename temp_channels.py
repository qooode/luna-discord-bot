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
        self.enabled = True  # Global enable/disable switch
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
                # Update timers less frequently to avoid rate limits
                if hasattr(self, '_timer_counter'):
                    self._timer_counter += 1
                else:
                    self._timer_counter = 1
                
                # Update channel names every 5 minutes, but cleanup every minute
                if self._timer_counter % 5 == 0:
                    await self.update_channel_timers()
                
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
            
            # Calculate smart inactivity limits based on channel duration
            expires_at = data['expires_at']
            created_at = data['created_at']
            total_duration_minutes = int((expires_at - created_at).total_seconds() / 60)
            
            # Inactivity limit: half the total duration or 10 minutes, whichever is smaller
            inactivity_limit = min(10, total_duration_minutes // 2)
            if inactivity_limit < 2:  # Minimum 2 minutes for very short channels
                inactivity_limit = min(2, total_duration_minutes)
            
            # Check if channel is inactive
            last_activity = data.get('last_activity', data['created_at'])
            time_since_activity = now - last_activity
            
            # Send inactivity warning at half the inactivity limit
            warning_time = max(1, inactivity_limit // 2)  # At least 1 minute warning
            if time_since_activity >= timedelta(minutes=warning_time) and time_since_activity < timedelta(minutes=inactivity_limit):
                if not data.get('inactivity_warned', False):
                    await self.send_inactivity_warning(channel, inactivity_limit - int(time_since_activity.total_seconds() / 60))
                    self.temp_channels[channel_id]['inactivity_warned'] = True
            
            # Delete after inactivity limit
            if time_since_activity >= timedelta(minutes=inactivity_limit):
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
    
    async def update_channel_timers(self):
        """Update channel names with countdown timers"""
        now = datetime.now()
        
        for channel_id, data in self.temp_channels.items():
            try:
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    continue
                
                # Calculate time remaining
                time_left = data['expires_at'] - now
                if time_left.total_seconds() <= 0:
                    continue  # Will be cleaned up by cleanup task
                
                # Get the base topic (without timer)
                clean_topic = data['topic'].replace(' ', '-').lower()
                
                # Calculate smart timer display
                total_minutes = int(time_left.total_seconds() / 60)
                hours = total_minutes // 60
                minutes = total_minutes % 60
                
                # Smart timer logic
                if total_minutes >= 120:  # 2+ hours: show only hours
                    if hours >= 24:
                        timer_display = f"{hours//24}d"
                    else:
                        timer_display = f"{hours}h"
                elif total_minutes >= 60:  # 1-2 hours: show hours and minutes if minutes > 0
                    if minutes > 0:
                        timer_display = f"{hours}h{minutes}m"
                    else:
                        timer_display = f"{hours}h"
                else:  # Under 1 hour: show minutes
                    timer_display = f"{total_minutes}m"
                
                # Create new channel name (no extended suffix)
                new_name = f"⏰・{clean_topic}-{timer_display}"
                
                # Only update if name changed and avoid rate limits
                if channel.name != new_name:
                    try:
                        await channel.edit(name=new_name)
                        print(f"Updated channel timer: {new_name}")
                        # Add small delay to avoid rate limits
                        await asyncio.sleep(1)
                    except discord.HTTPException as e:
                        # Rate limited or permission issues
                        print(f"Failed to update channel name: {e}")
                        pass
                        
            except Exception as e:
                print(f"Error updating timer for channel {channel_id}: {e}")
    
    async def update_single_channel_timer(self, channel_id: int):
        """Update timer for a single channel (used after extension)"""
        if channel_id not in self.temp_channels:
            return
            
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                return
            
            data = self.temp_channels[channel_id]
            now = datetime.now()
            
            # Calculate time remaining
            time_left = data['expires_at'] - now
            if time_left.total_seconds() <= 0:
                return
            
            # Get the base topic (without timer)
            clean_topic = data['topic'].replace(' ', '-').lower()
            
            # Calculate smart timer display
            total_minutes = int(time_left.total_seconds() / 60)
            hours = total_minutes // 60
            minutes = total_minutes % 60
            
            # Smart timer logic
            if total_minutes >= 120:  # 2+ hours: show only hours
                if hours >= 24:
                    timer_display = f"{hours//24}d"
                else:
                    timer_display = f"{hours}h"
            elif total_minutes >= 60:  # 1-2 hours: show hours and minutes if minutes > 0
                if minutes > 0:
                    timer_display = f"{hours}h{minutes}m"
                else:
                    timer_display = f"{hours}h"
            else:  # Under 1 hour: show minutes
                timer_display = f"{total_minutes}m"
            
            # Create new channel name (no extended suffix)
            new_name = f"⏰・{clean_topic}-{timer_display}"
            
            # Update channel name
            if channel.name != new_name:
                try:
                    await channel.edit(name=new_name)
                    print(f"Updated extended channel timer: {new_name}")
                except discord.HTTPException as e:
                    print(f"Failed to update extended channel name: {e}")
                    
        except Exception as e:
            print(f"Error updating single channel timer: {e}")
    
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
                value="🕐 +5min | 🕙 +10min | 🕞 +30min", 
                inline=False
            )
            
            message = await channel.send(embed=embed)
            await message.add_reaction("🕐")
            await message.add_reaction("🕙")
            await message.add_reaction("🕞")
            
            # Store message ID for reaction handling
            if channel.id in self.temp_channels:
                self.temp_channels[channel.id]['warning_message_id'] = message.id
                
        except Exception as e:
            print(f"Error sending expiration warning: {e}")
    
    async def send_inactivity_warning(self, channel: discord.TextChannel, minutes_left: int):
        """Send warning when channel is inactive"""
        try:
            embed = discord.Embed(
                title="💤 Channel Inactive",
                description=f"This channel will be deleted in **{minutes_left} minute{'s' if minutes_left != 1 else ''}** due to inactivity.",
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
    
    async def extend_channel(self, channel_id: int, user_id: int, extension_minutes: int) -> str:
        """Extend a channel by specified minutes"""
        if channel_id not in self.temp_channels:
            return "❌ This is not a temp channel!"
        
        channel_data = self.temp_channels[channel_id]
        
        # Check if user is the creator
        if channel_data['creator_id'] != user_id:
            return "❌ Only the channel creator can extend the channel!"
        
        # Extend by specified minutes
        self.temp_channels[channel_id]['expires_at'] += timedelta(minutes=extension_minutes)
        
        # Mark as extended
        self.temp_channels[channel_id]['extended'] = True
        
        # Reset warning status
        if channel_id in self.warned_channels:
            self.warned_channels.remove(channel_id)
        
        # Force immediate timer update for this channel
        await self.update_single_channel_timer(channel_id)
        
        # Update channel topic to show extension
        channel = self.bot.get_channel(channel_id)
        if channel:
            try:
                await channel.edit(topic=f"⏰ Extended! | Created by {channel_data['creator_name']}")
            except:
                pass
        
        self.save_data()
        return f"✅ Channel extended by {extension_minutes} minutes!"
    
    def parse_duration(self, duration_str: str) -> Optional[timedelta]:
        """Parse duration string to timedelta"""
        duration_map = {
            '5min': timedelta(minutes=5),
            '10min': timedelta(minutes=10),
            '15min': timedelta(minutes=15),
            '30min': timedelta(minutes=30),
            '45min': timedelta(minutes=45),
            '1h': timedelta(hours=1),
            '1h30m': timedelta(hours=1, minutes=30),
            '2h': timedelta(hours=2),
            '3h': timedelta(hours=3),
            '4h': timedelta(hours=4),
            '6h': timedelta(hours=6),
            '8h': timedelta(hours=8),
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
            # Check if temp channels are enabled
            if not self.enabled:
                return None, "❌ Temp channels are currently disabled by administrators."
            # Check user limits
            if len(self.get_user_channels(creator.id)) >= 2:
                return None, "❌ You already have 2 temp channels! Close one first."
            
            # Check cooldown
            if self.is_user_on_cooldown(creator.id):
                return None, "⏰ You're on cooldown! Wait 5 minutes between channel creations."
            
            # Parse duration
            duration_delta = self.parse_duration(duration)
            if not duration_delta:
                return None, "❌ Invalid duration! Use: 5min, 10min, 15min, 30min, 45min, 1h, 1h30m, 2h, 3h, 4h, 6h, 8h, 12h, 24h"
            
            # Find or create temp channels category
            category = discord.utils.get(guild.categories, name="Temp Channels")
            if not category:
                category = await guild.create_category("Temp Channels")
            
            # Create channel name with emoji, bullet, topic + duration
            clean_topic = topic.replace(' ', '-').lower()
            channel_name = f"⏰・{clean_topic}-{duration}"
            
            # Start with category permissions (inherit category overwrites)
            overwrites = {}
            if category:
                # Copy all category permissions
                for target, overwrite in category.overwrites.items():
                    overwrites[target] = overwrite
            
            # Add/override specific permissions for temp channels
            overwrites[guild.default_role] = discord.PermissionOverwrite(read_messages=channel_type == 'public')
            overwrites[creator] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
            overwrites[self.bot.user] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True, manage_channels=True)
            
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
            
            # Send welcome message with smart logic
            duration_minutes = int(duration_delta.total_seconds() / 60)
            inactivity_limit = min(10, duration_minutes // 2)  # Half the duration or 10 min, whichever is smaller
            
            if duration_minutes <= 10:
                inactivity_text = f"after **{duration_minutes} minutes** of inactivity"
            else:
                inactivity_text = f"after **{inactivity_limit} minutes** of inactivity"
            
            await channel.send(f"**{topic}** - Created by {creator.mention}\n"
                             f"⏰ This channel will be deleted in **{duration}** or {inactivity_text}.\n"
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
    
    async def close_channel(self, channel_id: int, user_id: int, is_admin: bool = False):
        """Close a temp channel manually"""
        if channel_id not in self.temp_channels:
            return False, "❌ This is not a temp channel!"
        
        channel_data = self.temp_channels[channel_id]
        
        # Check if user is the creator or an admin
        if channel_data['creator_id'] != user_id and not is_admin:
            return False, "❌ Only the channel creator or administrators can close the channel!"
        
        # Delete the channel
        closer_type = "administrator" if is_admin and channel_data['creator_id'] != user_id else "creator"
        await self.delete_temp_channel(channel_id, f"Channel closed by {closer_type}")
        
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
    
    def enable_temp_channels(self):
        """Enable temp channels globally"""
        self.enabled = True
        self.save_data()
    
    def disable_temp_channels(self):
        """Disable temp channels globally"""
        self.enabled = False
        self.save_data()
    
    def is_enabled(self) -> bool:
        """Check if temp channels are enabled"""
        return self.enabled