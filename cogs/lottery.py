# lottery.py

from datetime import datetime
import re

import discord
from discord.ext import commands

from database import errors, reminders, users
from resources import emojis, exceptions, functions, settings


class LotteryCog(commands.Cog):
    """Cog that contains the lottery detection commands"""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Runs when a message is sent in a channel."""
        if message.author.id != settings.EPIC_RPG_ID: return

        if message.embeds:
            embed: discord.Embed = message.embeds[0]
            message_description = message_field = ''
            if embed.description: message_description = embed.description
            if embed.fields: message_field = embed.fields[0].value

            # Lottery event check
            if 'join with `rpg lottery' in message_description.lower():
                message_history = await message.channel.history(limit=50).flatten()
                user_command_message = None
                for msg in message_history:
                    if msg.content is not None:
                        if msg.content.lower().startswith('rpg ') and 'lottery' in msg.content.lower():
                            user_command_message = msg
                            break
                if user_command_message is None:
                    await message.add_reaction(emojis.WARNING)
                    await errors.log_error('Couldn\'t find a command for the lottery event message.')
                    return
                user = user_command_message.author
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.alert_lottery.enabled: return
                timestring = re.search("Next draw\*\*: (.+?)$", message_field).group(1)
                time_left = await functions.parse_timestring_to_timedelta(timestring.lower())
                bot_answer_time = message.created_at.replace(microsecond=0)
                current_time = datetime.utcnow().replace(microsecond=0)
                time_elapsed = current_time - bot_answer_time
                time_left = time_left - time_elapsed
                reminder_message = user_settings.alert_lottery.message.replace('%','rpg buy lottery ticket')
                reminder: reminders.Reminder = (
                    await reminders.insert_user_reminder(user.id, 'lottery', time_left,
                                                         message.channel.id, reminder_message)
                )
                if reminder.record_exists:
                    await message.add_reaction(emojis.NAVI)
                else:
                    if settings.DEBUG_MODE: await message.add_reaction(emojis.CROSS)

        if not message.embeds:
            message_content = message.content
            # Buy lottery ticket
            if "lottery ticket successfully bought" in message_content.lower():
                try:
                    user_name = re.search("^\*\*(.+?)\*\*,", message_content).group(1)
                    user_name = user_name.encode('unicode-escape',errors='ignore').decode('ASCII').replace('\\','')
                except Exception as error:
                    await message.add_reaction(emojis.WARNING)
                    await errors.log_error(error)
                    return
                for member in message.guild.members:
                    member_name = member.name.encode('unicode-escape',errors='ignore').decode('ASCII').replace('\\','')
                    if member_name == user_name:
                        user = member
                        break
                if user is None:
                    await message.add_reaction(emojis.WARNING)
                    await errors.log_error(f'User not found in buy lottery ticket message: {message}')
                    return
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.alert_lottery.enabled: return
                timestring = re.search("the winner in \*\*(.+?)\*\*", message_content).group(1)
                time_left = await functions.parse_timestring_to_timedelta(timestring.lower())
                bot_answer_time = message.created_at.replace(microsecond=0)
                current_time = datetime.utcnow().replace(microsecond=0)
                time_elapsed = current_time - bot_answer_time
                time_left = time_left - time_elapsed
                reminder_message = user_settings.alert_lottery.message.replace('%','rpg buy lottery ticket')
                reminder: reminders.Reminder = (
                    await reminders.insert_user_reminder(user.id, 'lottery', time_left,
                                                         message.channel.id, reminder_message)
                )
                if reminder.record_exists:
                    await message.add_reaction(emojis.NAVI)
                else:
                    if settings.DEBUG_MODE: await message.add_reaction(emojis.CROSS)


# Initialization
def setup(bot):
    bot.add_cog(LotteryCog(bot))