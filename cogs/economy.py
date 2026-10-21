import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import datetime
from typing import Dict, Any

# --- Configuration & Constants ---
# The JSON file used to store all coin and daily claim data.
ECONOMY_FILE = "economy.json" 
# The amount of coins the user receives for the daily claim.
REWARD_AMOUNT = 500
# The cooldown for the daily command (24 hours in seconds).
COOLDOWN_SECONDS = 86400 
# The cost for purchasing a custom role.
CUSTOM_ROLE_COST = 5000
# Prefix added to the user's custom role name for easier identification.
CUSTOM_ROLE_PREFIX = "Custom Role | " 

# --- Helper Functions for Economy Data ---

def load_economy_data() -> Dict[str, Dict[str, Any]]:
    """
    Loads all economy data from the JSON file.
    Structure: { "guild_id": { "user_id": {"coins": 0, "last_daily": "ISO_timestamp"} } }
    """
    if not os.path.exists(ECONOMY_FILE):
        return {}
    try:
        with open(ECONOMY_FILE, 'r') as file:
            return json.load(file)
    except json.JSONDecodeError:
        print("Warning: Economy file is empty or corrupted, resetting data.")
        return {}
    except Exception as e:
        print(f"Error loading economy data: {e}")
        return {}

def save_economy_data(data: Dict[str, Dict[str, Any]]):
    """Saves the current economy data to the JSON file using atomic write for safety."""
    try:
        temp_file = ECONOMY_FILE + ".tmp"
        with open(temp_file, 'w') as f:
            json.dump(data, f, indent=4)
        os.replace(temp_file, ECONOMY_FILE)
    except Exception as e:
        print(f"Error saving economy data: {e}")

# --- Economy Cog ---

class economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Load data once when the cog initializes
        self.economy_data = load_economy_data() 
        
    def _get_user_data(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        """Ensures guild and user data structures exist and returns the user's data."""
        guild_id_str = str(guild_id)
        user_id_str = str(user_id)
        
        # Initialize guild data if it doesn't exist
        if guild_id_str not in self.economy_data:
            self.economy_data[guild_id_str] = {}
            
        # Initialize user data if it doesn't exist
        if user_id_str not in self.economy_data[guild_id_str]:
            self.economy_data[guild_id_str][user_id_str] = {
                "coins": 0,
                "last_daily": None # Stored as ISO string
            }
            
        return self.economy_data[guild_id_str][user_id_str]

    # --- /daily command (from daily.py) ---
    @app_commands.command(name = "daily", description = "Claim your daily coin reward!")
    async def daily_command(self, interaction: discord.Interaction):
        print(f'''command used: {interaction.command.name}
        user:{interaction.user.id} username:{interaction.user.name}
        server id: {interaction.guild.id} server name: {interaction.guild.name}''')
        print("======================================================================")
        
        await interaction.response.defer(ephemeral = False)
        
        user_data = self._get_user_data(interaction.guild_id, interaction.user.id)
        
        # Check cooldown
        if user_data["last_daily"]:
            # Parse the stored ISO string into a datetime object
            last_claimed = discord.utils.parse_time(user_data["last_daily"])
            
            # Calculate the next possible claim time
            next_claim = last_claimed + datetime.timedelta(seconds = COOLDOWN_SECONDS)
            now = discord.utils.utcnow()
            
            if now < next_claim:
                remaining_time = next_claim - now
                
                # Format remaining time for the message (H:M:S)
                hours, remainder = divmod(int(remaining_time.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                
                time_str = f"{hours}h {minutes}m {seconds}s"
                
                await interaction.followup.send(
                    f"⏰ You've already claimed your daily reward. Try again in **{time_str}**.", 
                    ephemeral=True
                )
                return

        # Grant reward and update timestamp
        current_coins = user_data["coins"]
        new_coins = current_coins + REWARD_AMOUNT
        
        user_data["coins"] = new_coins
        user_data["last_daily"] = discord.utils.utcnow().isoformat()
        
        save_economy_data(self.economy_data)

        # Send confirmation message
        embed = discord.Embed(
            title = "💰 Daily Reward Claimed! 📅",
            description = f"You received **{REWARD_AMOUNT}** coins!",
            color = discord.Color.gold()
        )
        embed.add_field(name="Current Balance", value=f"🪙 {new_coins} coins")
        embed.set_footer(text=f"Come back tomorrow for your next reward!")
        
        await interaction.followup.send(embed = embed, ephemeral = False)

    # --- /buyrole command (from buyrole.py) ---
    @app_commands.command(name = "buyrole", description = "Purchase a custom, personalized role for your profile.")
    @app_commands.describe(role_name="The name you want for your new role.")
    async def buy_custom_role(self, interaction: discord.Interaction, role_name: str):
        print(f'''command used: {interaction.command.name} role_name: {role_name}
        user:{interaction.user.id} username:{interaction.user.name}
        server id: {interaction.guild.id} server name: {interaction.guild.name}''')
        print("======================================================================")

        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        user = interaction.user
        
        # Get user data and current coins
        user_data = self._get_user_data(guild.id, user.id)
        current_coins = user_data["coins"]
        guild_id_str = str(guild.id)
        user_id_str = str(user.id)

        # 1. Check for sufficient funds
        if current_coins < CUSTOM_ROLE_COST:
            await interaction.followup.send(
                f"❌ You do not have enough coins to purchase a custom role. You need **{CUSTOM_ROLE_COST}** coins, but only have **{current_coins}**.",
                ephemeral=True
            )
            return

        # 2. Process Purchase
        
        # Deduct coins
        new_coins = current_coins - CUSTOM_ROLE_COST
        user_data["coins"] = new_coins
        save_economy_data(self.economy_data) # Save immediately after deduction
        
        # Determine the final role name
        full_role_name = f"{CUSTOM_ROLE_PREFIX}{role_name}"

        try:
            # Create the role
            new_role = await guild.create_role(
                name = full_role_name,
                # Setting permissions to be none, as it's a vanity role
                permissions = discord.Permissions.none(),
                # Sets the role to be displayed separately
                hoist = True, 
                reason = f"Custom role purchased by {user.display_name} via /buyrole."
            )
            
            # Simple repositioning logic: place the role just below the bot's highest role for visibility
            target_position = guild.me.top_role.position - 1
            if new_role.position != target_position:
                 await new_role.edit(position=target_position)
            
            # Assign the role to the user
            await user.add_roles(new_role, reason="Purchased custom role.")

            # Send success message
            embed = discord.Embed(
                title = "🎉 Custom Role Purchased!",
                description = f"You successfully purchased the role **{full_role_name}** for **{CUSTOM_ROLE_COST}** coins!",
                color = discord.Color.blue()
            )
            embed.add_field(name="New Balance", value=f"🪙 {new_coins} coins", inline=True)
            embed.set_footer(text="The role has been added. To change its color, you'll need to ask a moderator.")

            await interaction.followup.send(embed=embed, ephemeral=False)

        except discord.Forbidden:
            # Refund if the role creation failed due to permission issues
            self.economy_data[guild_id_str][user_id_str]["coins"] = current_coins
            save_economy_data(self.economy_data)
            await interaction.followup.send(
                "❌ **Error:** The bot was unable to create or assign the role due to permission issues (e.g., role hierarchy). "
                "Your coins have been **refunded**.", 
                ephemeral=True
            )
        except Exception as e:
            # Refund for any other unexpected error during role handling
            self.economy_data[guild_id_str][user_id_str]["coins"] = current_coins
            save_economy_data(self.economy_data)
            await interaction.followup.send(
                f"❌ An unexpected error occurred: {e}. Your coins have been **refunded**.", 
                ephemeral=True
            )

# bot setup - This function is what the main bot file will call to load the cog.
async def setup(bot):
    await bot.add_cog(economy(bot))