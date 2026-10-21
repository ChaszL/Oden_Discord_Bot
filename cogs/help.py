import discord
from discord.ext import commands
from discord import app_commands
from typing import Dict, List, Any

# Define the color for the help embed (using a nice neutral color)
HELP_EMBED_COLOR = discord.Color.from_rgb(114, 137, 218) # Discord Blurple

class help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # List of cogs to hide from the help menu (e.g., utility or temporary setup cogs)
        # It's good practice to hide the 'help' cog itself to avoid redundancy.
        self.hidden_cogs = ['help', 'project']

    # defines the command name as "Help" and gives it a description
    @app_commands.command(name = "help", description = "Displays a list of all available commands.")
    # defines the Help command and its interactions
    async def help_command(self, interaction: discord.Interaction):
        # prints to console the command used, user, and server info
        print(f'''command used: {interaction.command.name}
        user:{interaction.user.id} username:{interaction.user.name}
        server id: {interaction.guild.id} server name: {interaction.guild.name}''')
        print("======================================================================")

        # gives bot extra time to respond
        await interaction.response.defer(ephemeral = True)
        
        # Dictionary to store commands grouped by their cog name: {'CogName': [command_info, ...]}
        commands_by_cog: Dict[str, List[str]] = {}
        
        # --- FIX: Iterate over all cogs and their application commands ---
        for cog_name, cog in self.bot.cogs.items():
            # Skip hidden cogs
            if cog_name.lower() in self.hidden_cogs:
                continue
            
            # Use the class name for the cog name
            cog_display_name = cog_name
            commands_by_cog[cog_display_name] = []
            
            # The cog object holds the commands
            for command in cog.get_app_commands():
                # Check for command groups
                if isinstance(command, app_commands.Group):
                    # List the group and suggest checking its subcommands and gather subcommand names for a hint
                    subcommand_hints = ", ".join([f"`{cmd.name}`" for cmd in command.commands][:3])
                    
                    # Format group command information
                    command_info = (
                        f"**/{command.name}** - *Group* (e.g., {subcommand_hints}...)\n"
                        f"     > {command.description}"
                    )
                else:
                    # Format standard command information
                    command_info = f"`/{command.name}` - {command.description}"

                commands_by_cog[cog_display_name].append(command_info)

        # --- Build the Embed ---
        embed = discord.Embed(
            title="🤖 Bot Command List",
            description="Use the `/` menu in Discord to see all command options and parameters.",
            color=HELP_EMBED_COLOR
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        # Add fields for each cog
        for cog_name, command_info in commands_by_cog.items():
            if not command_info:
                continue

            # use the cog's class name, formatted nicely, as the field title
            formatted_cog_name = cog_name.replace('_', ' ').title()
            
            # check if the total output exceeds Discord's field value limit (1024 chars)
            field_value = "\n".join(command_info)
            if len(field_value) > 1024:
                field_value = field_value[:1000] + "...\n*(Too many commands to list, see Discord's command list for the rest)*"

            embed.add_field(
                name=f"📝 {formatted_cog_name} Commands",
                value=field_value,
                inline=False
            )

        # Send the final embed
        await interaction.followup.send(embed=embed)

# bot setup
async def setup(bot: commands.Bot):
    # Check if the 'help' cog is already loaded to prevent duplicate help commands
    if 'help' in bot.cogs:
        await bot.remove_cog('help')
    await bot.add_cog(help(bot))