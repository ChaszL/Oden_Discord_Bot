import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Loads environment variables from .env file
load_dotenv()
TOKEN = os.getenv("TOKEN")
TEST_GUILD_ID = os.getenv("TEST_GUILD_ID")

# Defining Bot Intents 
default_intents = discord.Intents.default()
default_intents.members = True          # Allows Bot to See Member List
default_intents.message_content = True  # Allows Bot to See Messages
default_intents.presences = True        # Allows Bot to Read Member Status (online, offline, idle)

# Sets bot prefix to "$"
bot = commands.Bot(command_prefix = "$", intents = default_intents)

# Prints to console if bot is online
@bot.event
async def on_ready():
    print(f"✅ Oden is logged in as {bot.user}")

    # Loads all files in The "Cog" folder
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"✅ Successfully loaded: {filename}")
            except Exception as e:
                print(f"❌ Failed to load: {filename}. Error: {e}")

    print("starting command sync...")
    try:
        guild = discord.Object(id = TEST_GUILD_ID)
        
        # Sync to the specific test guild for development speed
        await bot.tree.sync(guild = guild)
        # To register commands globally (in all guilds)
        await bot.tree.sync()
        print(f"✅ successfully synced commands to test guild: {TEST_GUILD_ID}")
        
    except Exception as e:
        # The 403 Forbidden error usually happens here due to Missing Access/Scope
        print(f"❌ failed to sync commands: {e}")
    print(f"======================================================================")

# Initiates bot using token
bot.run(TOKEN)