"""
Main Discord bot module for daily standups.

Handles:
- Bot initialization and event handlers
- Message monitoring for standup responses
- Slash commands for configuration
"""

import os
import logging
from datetime import datetime, date, timedelta
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from database import Database
from message_parser import MessageParser
from scheduler import StandupScheduler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
CHANNEL_ID = os.getenv('DISCORD_CHANNEL_ID')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
USE_OPENAI = os.getenv('USE_OPENAI', 'false').lower() == 'true'

# Response tracking window (hours after standup message)
RESPONSE_WINDOW_HOURS = 3


class StandupBot(commands.Bot):
    """Main Discord bot class for daily standups."""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(command_prefix='!', intents=intents)
        
        # Initialize components
        self.database = Database()
        self.message_parser = MessageParser(
            use_openai=USE_OPENAI,
            openai_api_key=OPENAI_API_KEY if OPENAI_API_KEY else None
        )
        
        # Get channel ID from database or env
        channel_id_str = self.database.get_config('standup_channel_id') or CHANNEL_ID
        channel_id = int(channel_id_str) if channel_id_str else None
        
        # Get timezone from env or database, default to UTC
        timezone = os.getenv('TIMEZONE') or self.database.get_config('timezone') or 'UTC'
        
        self.scheduler = StandupScheduler(
            self,
            self.database,
            self.message_parser,
            channel_id=channel_id,
            timezone=timezone
        )
        
        # Track last standup message time
        self.last_standup_time: Optional[datetime] = None
        self.standup_message_id: Optional[int] = None
    
    async def setup_hook(self):
        """Called when the bot is starting up."""
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Error syncing commands: {e}")
        
        # Start scheduler
        standup_hour = int(os.getenv('STANDUP_HOUR', '17'))
        standup_minute = int(os.getenv('STANDUP_MINUTE', '0'))
        self.scheduler.start(hour=standup_hour, minute=standup_minute)
    
    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f'{self.user} has logged in')
        logger.info(f'Bot is in {len(self.guilds)} guild(s)')
        
        # Set bot status/activity
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="daily standups"
        )
        await self.change_presence(activity=activity, status=discord.Status.online)
        logger.info('Bot status set to "Watching daily standups"')
    
    async def on_message(self, message: discord.Message):
        """Handle incoming messages."""
        # Ignore messages from bots
        if message.author.bot:
            return
        
        # Check if message is in the standup channel
        if message.channel.id != self.scheduler.channel_id:
            return
        
        # Check if we should track this message (within response window)
        if self.last_standup_time:
            time_diff = (datetime.now() - self.last_standup_time).total_seconds() / 3600
            if time_diff <= RESPONSE_WINDOW_HOURS:
                # Check if it's a reply to the standup message
                if message.reference and message.reference.message_id == self.standup_message_id:
                    await self.process_standup_response(message)
                # Also check if it's a direct message in the channel (not a reply)
                elif not message.reference:
                    # Process as standup response if it's a direct message
                    await self.process_standup_response(message)
        
        # Process the command
        await self.process_commands(message)
    
    async def process_standup_response(self, message: discord.Message):
        """
        Process a user's response to the standup prompt.
        
        Args:
            message: The user's response message
        """
        try:
            user_id = message.author.id
            username = message.author.name
            message_id = message.id
            raw_message = message.content
            response_date = date.today()
            
            logger.info(f"Processing standup response from {username}: {raw_message[:100]}")
            
            # Parse the message
            today_work, tomorrow_commitment = self.message_parser.parse_message(raw_message)
            
            # Save to database
            response_id = self.database.save_standup_response(
                user_id=user_id,
                username=username,
                message_id=message_id,
                response_date=response_date,
                today_work=today_work,
                tomorrow_commitment=tomorrow_commitment,
                raw_message=raw_message
            )
            
            # Send confirmation
            confirmation_parts = []
            if today_work:
                confirmation_parts.append(f"✅ Recorded today's work: {today_work}")
            if tomorrow_commitment:
                confirmation_parts.append(f"📝 Recorded tomorrow's commitment: {tomorrow_commitment}")
            
            if confirmation_parts:
                confirmation = "\n".join(confirmation_parts)
                await message.reply(confirmation)
            else:
                await message.reply("⚠️ I couldn't parse your response. Please make sure to mention what you worked on today and what you'll work on tomorrow.")
            
            logger.info(f"Saved standup response ID {response_id} for user {username}")
            
        except Exception as e:
            logger.error(f"Error processing standup response: {e}")
            await message.reply("❌ Sorry, there was an error processing your response. Please try again.")
    
    def update_standup_time(self, hour: int, minute: int):
        """Update the standup time."""
        self.scheduler.update_standup_time(hour, minute)
        self.database.set_config('standup_hour', str(hour))
        self.database.set_config('standup_minute', str(minute))


# Create bot instance
bot = StandupBot()


# Slash commands
@bot.tree.command(name='set_channel', description='Set the channel for daily standups')
@app_commands.describe(channel='The channel to use for standups')
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    """Set the standup channel."""
    try:
        bot.scheduler.set_channel(channel.id)
        await interaction.response.send_message(
            f'✅ Standup channel set to {channel.mention}',
            ephemeral=True
        )
    except Exception as e:
        logger.error(f"Error setting channel: {e}")
        await interaction.response.send_message(
            f'❌ Error setting channel: {str(e)}',
            ephemeral=True
        )


@bot.tree.command(name='set_time', description='Change the daily standup time')
@app_commands.describe(
    hour='Hour (0-23)',
    minute='Minute (0-59)'
)
async def set_time(interaction: discord.Interaction, hour: int, minute: int):
    """Set the standup time."""
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        await interaction.response.send_message(
            '❌ Invalid time. Hour must be 0-23 and minute must be 0-59.',
            ephemeral=True
        )
        return
    
    try:
        bot.update_standup_time(hour, minute)
        await interaction.response.send_message(
            f'✅ Standup time set to {hour:02d}:{minute:02d}',
            ephemeral=True
        )
    except Exception as e:
        logger.error(f"Error setting time: {e}")
        await interaction.response.send_message(
            f'❌ Error setting time: {str(e)}',
            ephemeral=True
        )


@bot.tree.command(name='view_commitments', description='View all pending commitments')
async def view_commitments(interaction: discord.Interaction):
    """View pending commitments."""
    try:
        # Get today's commitments (what people committed to do tomorrow)
        today = date.today()
        commitments = bot.database.get_commitments_for_date(today)
        
        if not commitments:
            await interaction.response.send_message(
                '📭 No pending commitments found for today.',
                ephemeral=True
            )
            return
        
        # Format response
        lines = ['📋 **Pending Commitments:**\n']
        for commitment in commitments:
            username = commitment['username']
            commitment_text = commitment['tomorrow_commitment']
            lines.append(f"• **{username}**: {commitment_text}")
        
        response = '\n'.join(lines)
        
        # Discord has a 2000 character limit, so truncate if needed
        if len(response) > 2000:
            response = response[:1997] + '...'
        
        await interaction.response.send_message(response, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error viewing commitments: {e}")
        await interaction.response.send_message(
            f'❌ Error retrieving commitments: {str(e)}',
            ephemeral=True
        )


@bot.tree.command(name='skip_today', description='Skip today\'s standup')
async def skip_today(interaction: discord.Interaction):
    """Skip today's standup."""
    try:
        # This would require pausing the scheduler for today
        # For now, just acknowledge the request
        await interaction.response.send_message(
            '⏭️ Skipping today\'s standup. Note: This feature is not fully implemented yet.',
            ephemeral=True
        )
        logger.info(f"Skip request from {interaction.user.name}")
    except Exception as e:
        logger.error(f"Error skipping standup: {e}")
        await interaction.response.send_message(
            f'❌ Error: {str(e)}',
            ephemeral=True
        )


@bot.tree.command(name='test_follow_ups', description='Test follow-up messages for commitments (simulates next day)')
@app_commands.describe(
    use_today='If true, checks today\'s commitments instead of yesterday\'s (for testing)',
    channel='Optional: channel to send follow-ups to'
)
async def test_follow_ups(interaction: discord.Interaction, use_today: bool = True, channel: Optional[discord.TextChannel] = None):
    """Test follow-up messages for commitments."""
    try:
        await interaction.response.defer(ephemeral=True)
        
        # Determine which channel to use
        target_channel = None
        original_channel_id = bot.scheduler.channel_id
        
        if channel:
            target_channel = channel
            bot.scheduler.set_channel(channel.id)
        elif bot.scheduler.channel_id:
            target_channel = bot.get_channel(bot.scheduler.channel_id)
            if not target_channel:
                target_channel = interaction.channel
                bot.scheduler.set_channel(interaction.channel.id)
        else:
            target_channel = interaction.channel
            bot.scheduler.set_channel(interaction.channel.id)
        
        # Determine date to check
        if use_today:
            # For testing: check today's commitments (simulating tomorrow checking today)
            check_date = date.today()
        else:
            # Normal: check yesterday's commitments
            check_date = date.today() - timedelta(days=1)
        
        # Get pending follow-ups for the date
        commitments = bot.database.get_pending_follow_ups(check_date)
        
        if not commitments:
            await interaction.followup.send(
                f'📭 No pending commitments found for {check_date.strftime("%Y-%m-%d")}.\n\n'
                f'💡 Make sure you have responses with commitments from that date. '
                f'Try using `/test_standup` first, then reply with a commitment, then run this command.',
                ephemeral=True
            )
            # Restore original channel
            if channel and original_channel_id:
                bot.scheduler.set_channel(original_channel_id)
            return
        
        # Send follow-ups (but don't mark as sent for testing purposes)
        follow_up_count = 0
        for commitment in commitments:
            user_id = commitment['user_id']
            username = commitment['username']
            commitment_text = commitment['tomorrow_commitment']
            commitment_id = commitment['id']
            
            try:
                user = bot.get_user(user_id)
                mention = user.mention if user else f"@{username}"
                
                # Create an embed for a more appealing message
                embed = discord.Embed(
                    title="📋 Accountability Check-in",
                    description=f"Hey {mention}! Let's check in on your commitment from yesterday.",
                    color=discord.Color.blue()
                )
                
                embed.add_field(
                    name="🎯 Your Commitment",
                    value=f"*\"{commitment_text}\"*",
                    inline=False
                )
                
                embed.add_field(
                    name="❓ Status",
                    value="Did you get this done?",
                    inline=False
                )
                
                embed.set_footer(text="Reply with ✅ if done, or let us know your progress!")
                embed.timestamp = datetime.now()
                
                await target_channel.send(embed=embed)
                logger.info(f"Sent test follow-up to user {username} for commitment: {commitment_text}")
                follow_up_count += 1
                
                # For testing, we can optionally mark as sent or not
                # Uncomment the next line if you want to mark them as sent:
                # bot.database.mark_follow_up_sent(commitment_id, date.today())
                
            except Exception as e:
                logger.error(f"Error sending follow-up to user {user_id}: {e}")
        
        # Restore original channel
        if channel and original_channel_id:
            bot.scheduler.set_channel(original_channel_id)
        
        await interaction.followup.send(
            f'✅ Sent {follow_up_count} follow-up message(s) to {target_channel.mention}!\n\n'
            f'📅 Checked commitments from: {check_date.strftime("%Y-%m-%d")}',
            ephemeral=True
        )
        
    except Exception as e:
        logger.error(f"Error sending test follow-ups: {e}")
        await interaction.followup.send(
            f'❌ Error: {str(e)}',
            ephemeral=True
        )


@bot.tree.command(name='schedule_test_standup', description='Schedule a test standup message X minutes from now')
@app_commands.describe(
    minutes='Number of minutes from now to send the standup (e.g., 2 for 2 minutes)',
    channel='Optional: channel to send the test standup to'
)
async def schedule_test_standup(interaction: discord.Interaction, minutes: int, channel: Optional[discord.TextChannel] = None):
    """Schedule a test standup message for a specific time."""
    try:
        if minutes < 1:
            await interaction.response.send_message(
                '❌ Minutes must be at least 1. Use `/test_standup` for immediate messages.',
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Determine which channel to use
        original_channel_id = bot.scheduler.channel_id
        
        if channel:
            bot.scheduler.set_channel(channel.id)
        elif not bot.scheduler.channel_id:
            # No channel configured, use current channel
            bot.scheduler.set_channel(interaction.channel.id)
        
        # Schedule the test standup
        job_id = bot.scheduler.schedule_test_standup(minutes)
        
        # Calculate target time for display
        from datetime import timedelta
        target_time = datetime.now(bot.scheduler.timezone) + timedelta(minutes=minutes)
        target_channel = bot.get_channel(bot.scheduler.channel_id) or interaction.channel
        
        # Restore original channel if we temporarily changed it
        if channel and original_channel_id:
            bot.scheduler.set_channel(original_channel_id)
        
        await interaction.followup.send(
            f'✅ Scheduled test standup for {target_channel.mention}!\n\n'
            f'⏰ Will send in **{minutes} minute(s)**\n'
            f'📅 At: {target_time.strftime("%Y-%m-%d %H:%M:%S %Z")}',
            ephemeral=True
        )
        
    except Exception as e:
        logger.error(f"Error scheduling test standup: {e}")
        await interaction.followup.send(
            f'❌ Error: {str(e)}',
            ephemeral=True
        )


@bot.tree.command(name='test_standup', description='Send a test standup message immediately (uses current channel if no channel set)')
@app_commands.describe(channel='Optional: channel to send the test standup to')
async def test_standup(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    """Send a test standup message."""
    try:
        await interaction.response.defer(ephemeral=True)
        
        # Determine which channel to use
        target_channel = None
        original_channel_id = bot.scheduler.channel_id
        
        if channel:
            # Use the specified channel
            target_channel = channel
            bot.scheduler.set_channel(channel.id)
        elif bot.scheduler.channel_id:
            # Use the configured channel
            target_channel = bot.get_channel(bot.scheduler.channel_id)
            if not target_channel:
                # Fallback to current channel if configured channel not found
                target_channel = interaction.channel
                bot.scheduler.set_channel(interaction.channel.id)
        else:
            # No channel configured, use current channel
            target_channel = interaction.channel
            bot.scheduler.set_channel(interaction.channel.id)
        
        # Send test standup
        await bot.scheduler.send_daily_standup()
        
        # Update tracking
        bot.last_standup_time = datetime.now()
        if target_channel:
            # Get the last message (should be our standup)
            async for message in target_channel.history(limit=1):
                bot.standup_message_id = message.id
                break
        
        # Restore original channel if we temporarily changed it
        if channel and original_channel_id:
            bot.scheduler.set_channel(original_channel_id)
        elif not original_channel_id and channel:
            # If there was no channel set before, keep the new one
            pass
        
        await interaction.followup.send(
            f'✅ Test standup message sent to {target_channel.mention}!', 
            ephemeral=True
        )
        
    except Exception as e:
        logger.error(f"Error sending test standup: {e}")
        await interaction.followup.send(
            f'❌ Error: {str(e)}',
            ephemeral=True
        )


def main():
    """Main entry point."""
    if not BOT_TOKEN:
        logger.error("DISCORD_BOT_TOKEN not found in environment variables!")
        return
    
    try:
        bot.run(BOT_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        bot.scheduler.stop()
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        bot.scheduler.stop()


if __name__ == '__main__':
    main()

