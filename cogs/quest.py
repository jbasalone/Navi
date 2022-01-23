# quest.py

from datetime import datetime, timedelta
import re

import discord
from discord.ext import commands

from database import cooldowns, errors, reminders, users
from resources import emojis, exceptions, functions, settings, strings


class QuestCog(commands.Cog):
    """Cog that contains the quest detection commands"""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Runs when a message is sent in a channel."""
        if message.author.id != settings.EPIC_RPG_ID: return

        if message.embeds:
            embed: discord.Embed = message.embeds[0]
            message_author = message_title = message_description = icon_url = ''
            if embed.author:
                message_author = str(embed.author.name)
                icon_url = embed.author.icon_url
            if embed.title: message_title = str(embed.title)
            if embed.description: message_description = embed.description

            # Quest cooldown
            if 'you have already claimed a quest' in message_title.lower():
                user_id = user_name = user = None
                try:
                    user_id = int(re.search("avatars\/(.+?)\/", icon_url).group(1))
                except:
                    try:
                        user_name = re.search("^(.+?)'s cooldown", message_author).group(1)
                        user_name = user_name.encode('unicode-escape',errors='ignore').decode('ASCII').replace('\\','')
                    except Exception as error:
                        await message.add_reaction(emojis.WARNING)
                        await errors.log_error(error)
                        return
                if user_id is not None:
                    user = await message.guild.fetch_member(user_id)
                else:
                    for member in message.guild.members:
                        member_name = member.name.encode('unicode-escape',errors='ignore').decode('ASCII').replace('\\','')
                        if member_name == user_name:
                            user = member
                            break
                if user is None:
                    await message.add_reaction(emojis.WARNING)
                    await errors.log_error(f'User not found in quest cooldown message: {message}')
                    return
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.alert_quest.enabled: return
                message_history = await message.channel.history(limit=50).flatten()
                user_command_message = None
                for msg in message_history:
                    if msg.content is not None:
                        if msg.content.lower() in ('rpg quest','rpg epic quest') and msg.author == user:
                            user_command_message = msg
                            break
                if user_command_message is None:
                    await message.add_reaction(emojis.WARNING)
                    await errors.log_error('Couldn\'t find a command for the quest cooldown message.')
                    return
                user_command = user_command_message.content.lower()
                timestring = re.search("wait at least \*\*(.+?)\*\*...", message_title).group(1)
                time_left = await functions.parse_timestring_to_timedelta(timestring.lower())
                bot_answer_time = message.created_at.replace(microsecond=0)
                current_time = datetime.utcnow().replace(microsecond=0)
                time_elapsed = current_time - bot_answer_time
                time_left = time_left - time_elapsed
                reminder_message = user_settings.alert_quest.message.replace('%',user_command)
                reminder: reminders.Reminder = (
                    await reminders.insert_user_reminder(user.id, 'quest', time_left,
                                                         message.channel.id, reminder_message)
                )
                if reminder.record_exists:
                    await message.add_reaction(emojis.NAVI)
                else:
                    if settings.DEBUG_MODE: await message.add_reaction(emojis.CROSS)

            # Epic Quest
            if '__wave #1__' in message_description.lower():
                user_id = user_name = user = None
                try:
                    user_id = int(re.search("avatars\/(.+?)\/", icon_url).group(1))
                except:
                    try:
                        user_name = re.search("^(.+?)'s epic quest", message_author).group(1)
                        user_name = user_name.encode('unicode-escape',errors='ignore').decode('ASCII').replace('\\','')
                    except Exception as error:
                        await message.add_reaction(emojis.WARNING)
                        await errors.log_error(error)
                        return
                if user_id is not None:
                    user = await message.guild.fetch_member(user_id)
                else:
                    for member in message.guild.members:
                        member_name = member.name.encode('unicode-escape',errors='ignore').decode('ASCII').replace('\\','')
                        if member_name == user_name:
                            user = member
                            break
                if user is None:
                    await message.add_reaction(emojis.WARNING)
                    await errors.log_error(f'User not found in epic quest message: {message}')
                    return
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.alert_quest.enabled: return
                current_time = datetime.utcnow().replace(microsecond=0)
                bot_answer_time = message.created_at.replace(microsecond=0)
                time_elapsed = current_time - bot_answer_time
                cooldown: cooldowns.Cooldown = await cooldowns.get_cooldown('quest')
                user_donor_tier = 3 if user_settings.user_donor_tier > 3 else user_settings.user_donor_tier
                if cooldown.donor_affected:
                    time_left_seconds = (cooldown.actual_cooldown()
                                        * settings.DONOR_COOLDOWNS[user_donor_tier]
                                        - time_elapsed.total_seconds())
                else:
                    time_left_seconds = cooldown.actual_cooldown() - time_elapsed.total_seconds()
                time_left = timedelta(seconds=time_left_seconds)
                reminder_message = user_settings.alert_quest.message.replace('%','rpg epic quest')
                reminder: reminders.Reminder = (
                    await reminders.insert_user_reminder(user.id, 'quest', time_left,
                                                         message.channel.id, reminder_message)
                )
                if reminder.record_exists:
                    await message.add_reaction(emojis.NAVI)
                else:
                    if settings.DEBUG_MODE: await message.channel.send(strings.MSG_ERROR)

        if not message.embeds:
            message_content = message.content
            # Quest
            if ('you did not accept the quest' in message_content.lower()
                or 'got a **new quest**!' in message_content.lower()):
                user_name = user = None
                if message.mentions:
                    quest_declined = True
                    user = message.mentions[0]
                else:
                    quest_declined = False
                    try:
                        user_name = re.search("^\*\*(.+?)\*\* ", message_content).group(1)
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
                        await errors.log_error(f'User not found in quest message: {message}')
                        return
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.alert_quest.enabled: return
                current_time = datetime.utcnow().replace(microsecond=0)
                bot_answer_time = message.created_at.replace(microsecond=0)
                time_elapsed = current_time - bot_answer_time
                if quest_declined:
                    time_left = timedelta(hours=1)
                else:
                    cooldown: cooldowns.Cooldown = await cooldowns.get_cooldown('quest')
                    user_donor_tier = 3 if user_settings.user_donor_tier > 3 else user_settings.user_donor_tier
                    if cooldown.donor_affected:
                        time_left_seconds = (cooldown.actual_cooldown()
                                            * settings.DONOR_COOLDOWNS[user_donor_tier]
                                            - time_elapsed.total_seconds())
                    else:
                        time_left_seconds = cooldown.actual_cooldown() - time_elapsed.total_seconds()
                    time_left = timedelta(seconds=time_left_seconds)
                reminder_message = user_settings.alert_quest.message.replace('%','rpg quest')
                reminder: reminders.Reminder = (
                    await reminders.insert_user_reminder(user.id, 'quest', time_left,
                                                         message.channel.id, reminder_message)
                )
                if reminder.record_exists:
                    await message.add_reaction(emojis.NAVI)
                else:
                    if settings.DEBUG_MODE: await message.channel.send(strings.MSG_ERROR)


# Initialization
def setup(bot):
    bot.add_cog(QuestCog(bot))