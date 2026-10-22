import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import os
from typing import Dict, List

# --- Configuration & Constants ---
# Ollama runs locally; change these in .env if needed
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")
# How many past messages (user + bot) to remember per channel
MAX_HISTORY = 20
# Discord's message character limit
DISCORD_LIMIT = 2000
SYSTEM_PROMPT = (
    "You are Oden, a friendly and helpful Discord bot. "
    "Keep answers concise and conversational, and use Discord markdown when it helps."
)

# --- Helper Functions ---

def split_message(text: str, limit: int = DISCORD_LIMIT) -> List[str]:
    """Splits long text into chunks that fit in a Discord message, preferring newline breaks."""
    chunks = []
    while len(text) > limit:
        split_at = text.rfind("\n", 0, limit)
        if split_at <= 0:
            split_at = limit
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    if text:
        chunks.append(text)
    return chunks

# --- AI Cog ---

class ai(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # conversation memory: {channel_id: [{"role": ..., "content": ...}, ...]}
        self.histories: Dict[int, List[Dict[str, str]]] = {}

    async def ask_ollama(self, channel_id: int, author_name: str, prompt: str) -> str:
        """Sends the prompt plus channel history to Ollama and returns the reply."""
        history = self.histories.setdefault(channel_id, [])
        history.append({"role": "user", "content": f"{author_name}: {prompt}"})

        payload = {
            "model": OLLAMA_MODEL,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + history,
            "stream": False,
            "think": False,  # skip qwen3's <think> reasoning output for faster replies
        }

        try:
            timeout = aiohttp.ClientTimeout(total = 120)
            async with aiohttp.ClientSession(timeout = timeout) as session:
                async with session.post(f"{OLLAMA_URL}/api/chat", json = payload) as response:
                    if response.status != 200:
                        history.pop()
                        error_text = await response.text()
                        return f"❌ Ollama returned status {response.status}: {error_text[:300]}"
                    data = await response.json()
        except aiohttp.ClientConnectorError:
            history.pop()
            return "❌ Couldn't reach Ollama. Make sure it's running (`ollama serve`)."
        except Exception as e:
            history.pop()
            return f"❌ Something went wrong talking to the AI: {e}"

        reply = data["message"]["content"].strip() or "(no response)"
        history.append({"role": "assistant", "content": reply})

        # trims old messages so memory doesn't grow forever
        if len(history) > MAX_HISTORY:
            del history[:-MAX_HISTORY]

        return reply

    # --- Listener: reply when the bot is @mentioned ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # ignore bots and messages that don't mention Oden
        if message.author.bot or self.bot.user not in message.mentions:
            return

        # removes the mention from the message so only the question is sent
        prompt = message.content.replace(f"<@{self.bot.user.id}>", "").replace(f"<@!{self.bot.user.id}>", "").strip()
        if not prompt:
            await message.reply("Hey! Mention me with a question and I'll answer.")
            return

        async with message.channel.typing():
            reply = await self.ask_ollama(message.channel.id, message.author.display_name, prompt)

        chunks = split_message(reply)
        await message.reply(chunks[0])
        for chunk in chunks[1:]:
            await message.channel.send(chunk)

    # --- /ask command ---
    @app_commands.command(name = "ask", description = "Ask Oden's AI a question.")
    @app_commands.describe(prompt = "What you want to ask")
    async def ask_command(self, interaction: discord.Interaction, prompt: str):
        print(f'''command used: {interaction.command.name}
        user:{interaction.user.id} username:{interaction.user.name}
        server id: {interaction.guild.id} server name: {interaction.guild.name}''')
        print("======================================================================")

        # AI replies can take a while, so give the bot extra time
        await interaction.response.defer()

        reply = await self.ask_ollama(interaction.channel_id, interaction.user.display_name, prompt)

        chunks = split_message(f"**{interaction.user.display_name}:** {prompt}\n\n{reply}")
        for chunk in chunks:
            await interaction.followup.send(chunk)

    # --- /reset_chat command ---
    @app_commands.command(name = "reset_chat", description = "Clears Oden's AI conversation memory for this channel.")
    async def reset_chat_command(self, interaction: discord.Interaction):
        print(f'''command used: {interaction.command.name}
        user:{interaction.user.id} username:{interaction.user.name}
        server id: {interaction.guild.id} server name: {interaction.guild.name}''')
        print("======================================================================")

        self.histories.pop(interaction.channel_id, None)
        await interaction.response.send_message("🧹 AI memory cleared for this channel.")

# bot setup
async def setup(bot):
    await bot.add_cog(ai(bot))
