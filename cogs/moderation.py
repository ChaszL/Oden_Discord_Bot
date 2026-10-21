import discord
from discord.ext import commands
from discord import app_commands
import random
import json
import os
from typing import Optional, Dict, Any

# --- WARN DATA HANDLING (from warn.py) ---

# warn json file
WARNS_FILE = "warns_data.json"

# helper function to load warn data
def load_warn_data() -> Dict[str, Dict[str, Any]]:
    """
    Loads all warn data from the JSON file.
    Structure: { "guild_id": { "user_id": [warn_records] } }
    """
    if not os.path.exists(WARNS_FILE):
        return {}
    try:
        with open(WARNS_FILE, 'r') as file:
            return json.load(file)
    except json.JSONDecodeError:
        print("Warning: Warns file is empty or corrupted, resetting data.")
        return {}
    except Exception as e:
        print(f"Error loading warn data: {e}")
        return {}

# helper function to save warn data
def save_warn_data(data: Dict[str, Dict[str, Any]]):
    """Saves the current warn data to the JSON file."""
    try:
        with open(WARNS_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving warn data: {e}")

# --- MODERATION COG ---

class moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Combined Error Handler (from ban.py, kick.py, purge.py, etc.) ---
    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handles errors for all app commands in this cog."""

        if isinstance(error, app_commands.CommandInvokeError):
            error = error.original
            
        if isinstance(error, app_commands.MissingPermissions):
            missing_perms = [p.replace('_', ' ').title() for p in error.missing_permissions]
            
            message = (
                f"**{interaction.user.mention}**, you need the following permissions for this command: "
                f"**{', '.join(missing_perms)}**."
            )
            await interaction.response.send_message(message, ephemeral=True)
            return

        if isinstance(error, app_commands.TransformerError):
            await interaction.response.send_message(f"Invalid argument type. Please check the command input.", ephemeral=True)
            return
            
        # Log unhandled errors
        print(f"Unhandled app command error in ModerationFeatures: {error}")
        # Send a generic error message if not already sent by an exception handler
        if not interaction.response.is_done():
            await interaction.response.send_message(f"An unexpected error occurred: {error}", ephemeral=True)


    # --- /ban command (from ban.py) ---
    @app_commands.command(name = "ban", description = "Bans a user from the server.")
    @app_commands.describe(member = "The member to ban.", reason = "The reason for the ban.")
    @app_commands.checks.has_permissions(ban_members = True)
    async def ban_command(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = "No reason provided."):
        print(f'''command used: {interaction.command.name}
        user:{interaction.user.id} username:{interaction.user.name}
        server id: {interaction.guild.id} server name: {interaction.guild.name}''')
        print("======================================================================")

        # gives bot extra time to respond
        await interaction.response.defer(ephemeral=True)

        # handles if member picks themself
        if member == interaction.user:
            await interaction.followup.send("You cannot ban yourself!", ephemeral=True)
            return
        
        # checks if the bot can ban the member - hierarchy check
        if member.top_role >= interaction.guild.me.top_role:
            await interaction.followup.send("I cannot ban this user due to role hierarchy!", ephemeral=True)
            return
            
        try:
            # Attempt to DM the user before banning 
            try:
                await member.send(f"You have been banned from **{interaction.guild.name}** for the following reason: **{reason}**")
            except discord.Forbidden:
                print(f"Could not DM {member.name} about their ban.")

            # bans member and logs reason as reason in the activity log
            await member.ban(reason = reason)

            await interaction.followup.send(f"✅ **{member.display_name}** has been banned. Reason: *{reason}*", ephemeral = False)
        # sends if bot does not have permissions
        except discord.Forbidden:
            await interaction.followup.send("❌ I do not have permission to perform this action.", ephemeral=True)
        # sends if another error pops up
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)


    # --- /kick command (from kick.py) ---
    @app_commands.command(name = "kick", description = "Kicks a user from the server.")
    @app_commands.describe(member = "The member to kick.", reason = "The reason for the kick.")
    @app_commands.checks.has_permissions(kick_members = True)
    async def kick_command(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = "No reason provided."):
        print(f'''command used: {interaction.command.name}
        user:{interaction.user.id} username:{interaction.user.name}
        server id: {interaction.guild.id} server name: {interaction.guild.name}''')
        print("======================================================================")

        # gives bot extra time to respond
        await interaction.response.defer(ephemeral=True)

        # handles if member picks themself
        if member == interaction.user:
            await interaction.followup.send("You cannot kick yourself!", ephemeral=True)
            return
        
        # checks if the bot can kick the member - hierarchy check
        if member.top_role >= interaction.guild.me.top_role:
            await interaction.followup.send("I cannot kick this user due to role hierarchy!", ephemeral=True)
            return
            
        try:
            # Attempt to DM the user before kicking 
            try:
                await member.send(f"You have been kicked from **{interaction.guild.name}** for the following reason: **{reason}**")
            except discord.Forbidden:
                print(f"Could not DM {member.name} about their kick.")

            # kicks member and loggs reason as reason in the activity log
            await member.kick(reason = reason)

            await interaction.followup.send(f"✅ **{member.display_name}** has been kicked. Reason: *{reason}*", ephemeral = False)
        # sends if bot does not have permissions
        except discord.Forbidden:
            await interaction.followup.send("❌ I do not have permission to perform this action.", ephemeral=True)
        # sends if another error pops up
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)


    # --- /purge command (from purge.py) ---
    @app_commands.command(name = "purge", description = "Deletes a specified number of messages.")
    @app_commands.describe(amount = "The number of messages (max 100) to delete.")
    @app_commands.checks.has_permissions(manage_messages = True)
    async def delete_messages_command(self, interaction: discord.Interaction, amount: int):
        print(f'''command used: {interaction.command.name}
        user:{interaction.user.id} username:{interaction.user.name}
        server id: {interaction.guild.id} server name: {interaction.guild.name}''')
        print("======================================================================")

        # gives bot extra time to respond
        await interaction.response.defer(ephemeral=True) 
        
        # enforce max 100 limit, or Discord will handle it with a 400 error
        if amount > 100:
            amount = 100

        try:
            # takes in deleted count as a vaiable after eligible messages are deleted
            deleted_count = await interaction.channel.purge(limit = amount)

            # sends a confirmation message
            await interaction.followup.send(f"Successfully deleted **{len(deleted_count)}** messages.", ephemeral=True)

        # if try block fails, send error message
        except discord.HTTPException:
            await interaction.followup.send(f"I can only delete messages less than 14 days old or I lack permissions.", ephemeral=True)

    
    # --- /warn command (from warn.py) ---
    @app_commands.command(name = "warn", description = "Issues a warning to a member.")
    @app_commands.describe(member = "The member to warn.", reason = "The reason for the warning.")
    @app_commands.checks.has_permissions(kick_members = True) # Using kick_members as a standard mod perm
    async def warn_command(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        print(f'''command used: {interaction.command.name}
        user:{interaction.user.id} username:{interaction.user.name}
        server id: {interaction.guild.id} server name: {interaction.guild.name}''')
        print("======================================================================")
        
        await interaction.response.defer(ephemeral = True)
        
        # load data and ensure guild key exists
        data = load_warn_data()
        guild_id_str = str(interaction.guild_id)
        user_id_str = str(member.id)
        
        if guild_id_str not in data:
            data[guild_id_str] = {}
        if user_id_str not in data[guild_id_str]:
            data[guild_id_str][user_id_str] = []

        # create the new warn record
        new_warn = {
            "reason": reason,
            "timestamp": discord.utils.utcnow().isoformat(),
            "moderator": interaction.user.display_name # Use display_name for better readability
        }
        
        # add the warn and save
        data[guild_id_str][user_id_str].append(new_warn)
        save_warn_data(data)

        # Notify the user
        try:
            await member.send(f"You have received a warning in **{interaction.guild.name}** for: **{reason}**.\nTotal warnings: **{len(data[guild_id_str][user_id_str])}**.")
        except discord.Forbidden:
            print(f"Could not DM {member.name} about their warning.")

        await interaction.followup.send(f"✅ **{member.display_name}** has been warned (Total: {len(data[guild_id_str][user_id_str])}). Reason: *{reason}*.", ephemeral = False)


    # --- /show_warns command (from warn.py) ---
    @app_commands.command(name = "show_warns", description = "Shows the warning history for a member.")
    @app_commands.describe(member = "The member to view warnings for.")
    @app_commands.checks.has_permissions(kick_members = True)
    async def show_warns_command(self, interaction: discord.Interaction, member: discord.Member):
        print(f'''command used: {interaction.command.name}
        user:{interaction.user.id} username:{interaction.user.name}
        server id: {interaction.guild.id} server name: {interaction.guild.name}''')
        print("======================================================================")
        
        await interaction.response.defer(ephemeral = True)
        
        data = load_warn_data()
        guild_data = data.get(str(interaction.guild_id), {})
        warns = guild_data.get(str(member.id), [])
        warn_count = len(warns)

        embed = discord.Embed(title=f"Warning History for {member.display_name}", color=discord.Color.red())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Total Warnings", value=str(warn_count), inline=False)
        
        if warn_count == 0:
            embed.add_field(name="Status", value="No warnings found for this user.", inline=False)
        else:
            warn_list_text = ""
            # get the 3 most recent warns
            display_warns = warns[-3:]
            start_index = max(0, warn_count - 3)
            
            for i, warn_record in enumerate(display_warns):
                # safely parse timestamp if it exists, otherwise use N/A
                timestamp_str = "N/A"
                if warn_record.get('timestamp'):
                    try:
                        # convert to Discord-style relative time
                        dt_object = discord.utils.parse_time(warn_record['timestamp'])
                        timestamp_str = f"<t:{int(dt_object.timestamp())}:R>" # Relative time
                    except:
                        pass
                        
                warn_list_text += (
                    f"**#{i + 1 + start_index}:** *{warn_record['reason']}*\\n"
                    f"  > **Moderator:** {warn_record.get('moderator', 'Unknown')} | **When:** {timestamp_str}\\n"
                )
            
            # if the user has more than 3 warns only show the last 3
            if warn_count > 3:
                warn_list_text = f"*(Showing last 3 of {warn_count} warns...)*\\n" + warn_list_text
            embed.add_field(name = "Recent Warnings", value = warn_list_text, inline = False)

        # sends the embed
        await interaction.followup.send(embed = embed, ephemeral = True)


    # --- /random_all command (from random_all.py) ---
    @app_commands.command(name = "random_all", description = "Picks a random member from the server.")
    async def random_all_member_command(self, interaction: discord.Interaction):
        print(f'''command used: {interaction.command.name}
        user:{interaction.user.id} username:{interaction.user.name}
        server id: {interaction.guild.id} server name: {interaction.guild.name}''')
        print("======================================================================")

        # gives bot extra time to respond
        await interaction.response.defer()

        try:
            # saving server id as guild
            guild = interaction.guild

            # saves members who are not bots in the server into a list
            members = [m for m in guild.members if not m.bot]

            # if there are no members send error message
            if not members:
                await interaction.followup.send("NO MEMBERS FOUND!")
                return
            
            #chooses a member and then @ them in the chat
            chosen_member = random.choice(members)
            await interaction.followup.send(f"I randomly choose... {chosen_member.mention}")
        
        # if try fails, send error message to console and user
        except Exception as e:
            print(f"Failed to use random_member_all internal error: {e}")
            await interaction.followup.send("Uh oh! An unexpected error occurred while picking a member.", ephemeral=True)


    # --- /random_online command (from random_online.py) ---
    @app_commands.command(name = "random_online", description = "Picks a random online member from the server.")
    async def random_online_member_command(self, interaction: discord.Interaction):
        print(f'''command used: {interaction.command.name}
        user:{interaction.user.id} username:{interaction.user.name}
        server id: {interaction.guild.id} server name: {interaction.guild.name}''')
        print("======================================================================")

        # gives bot extra time to respond
        await interaction.response.defer()

        try:
            # saving server id as guild
            guild = interaction.guild

            # saves members who are not bots and are online/idle/dnd in the server into a list
            online_members = [m for m in guild.members if not m.bot and m.status in (discord.Status.online, discord.Status.idle, discord.Status.dnd)]

            # if there are no members send error message
            if not online_members:
                await interaction.followup.send("NO ONLINE MEMBERS FOUND!")
                return
            
            #chooses a member and then @ them in the chat
            chosen_member = random.choice(online_members)
            await interaction.followup.send(f"I randomly choose... {chosen_member.mention}")
        
        # if try fails, send error message to console and user
        except Exception as e:
            print(f"Failed to use random_member_online internal error: {e}")
            await interaction.followup.send("Uh oh! An unexpected error occurred while picking a member.", ephemeral=True)


    # --- /random_offline command (from random_offline.py) ---
    @app_commands.command(name = "random_offline", description = "Picks a random offline member from the server.")
    async def random_offline_member_command(self, interaction: discord.Interaction):
        print(f'''command used: {interaction.command.name}
        user:{interaction.user.id} username:{interaction.user.name}
        server id: {interaction.guild.id} server name: {interaction.guild.name}''')
        print("======================================================================")

        # gives bot extra time to respond
        await interaction.response.defer()

        try:
            # saving server id as guild
            guild = interaction.guild

            # saves members who are not bots and are NOT online/idle/dnd in the server into a list (i.e. offline or invisible)
            offline_members = [m for m in guild.members if not m.bot and m.status not in (discord.Status.online, discord.Status.idle, discord.Status.dnd)]

            # if there are no members send error message
            if not offline_members:
                await interaction.followup.send("NO OFFLINE MEMBERS FOUND!")
                return
            
            #chooses a member and then @ them in the chat
            chosen_member = random.choice(offline_members)
            await interaction.followup.send(f"I randomly choose... {chosen_member.mention}")
        
        # if try fails, send error message to console and user
        except Exception as e:
            print(f"Failed to use random_member_offline internal error: {e}")
            await interaction.followup.send("Uh oh! An unexpected error occurred while picking a member.", ephemeral=True)

# bot setup 
async def setup(bot):
    await bot.add_cog(moderation(bot))