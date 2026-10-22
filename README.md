# Oden

A Discord bot built with [discord.py](https://discordpy.readthedocs.io/) featuring an economy system, games, moderation tools, and a local AI chatbot. All commands are slash commands — type `/` in Discord to see them.

## Commands

**Economy**
- `/daily` — Claim your daily coin reward
- `/buyrole` — Purchase a custom, personalized role

**Fun**
- `/question` — Multiple-choice trivia question
- `/joke` — Tells a joke and lets you guess the punchline
- `/count` — Counts up until someone says "stop"
- `/whisper` — Sends a private message to a server member
- `/animal` — Random picture of a selected animal
- `/flipcoin` — Heads or tails
- `/quote` — Sends a quote and its author
- `/8ball` — Ask the Magic 8-Ball a question

**Moderation**
- `/ban`, `/kick` — Remove a user from the server
- `/purge` — Delete a number of messages
- `/warn`, `/show_warns` — Issue and view member warnings
- `/random_all`, `/random_online`, `/random_offline` — Pick a random member

**AI** (powered by a local [Ollama](https://ollama.com) Qwen model)
- `/ask` — Ask Oden a question
- `/reset_chat` — Clear the AI's memory for the channel
- `@Oden <message>` — Mention the bot to chat with it

**Other**
- `/help` — Lists all available commands

## Setup

1. **Install Python 3.10+**.
2. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```
3. **Create a bot** in the [Discord Developer Portal](https://discord.com/developers/applications). Under **Bot**, enable the *Server Members*, *Presence*, and *Message Content* intents.
4. **Configure:** copy `.env.example` to `.env` and fill in your bot token and test server ID.
5. **Set up the AI (optional):** install [Ollama](https://ollama.com), then download the model:
   ```
   ollama pull qwen3:4b
   ```
   Want something even smaller? Use `qwen3:1.7b` and set `OLLAMA_MODEL` in `.env`.
6. **Run:**
   ```
   python main.py
   ```

## Project Structure

```
main.py          # Starts the bot and loads all cogs
cogs/
  ai.py          # Ollama-powered AI chat
  economy.py     # Coins and role shop
  fun.py         # Games and random fun commands
  help.py        # /help command
  moderation.py  # Moderation and warnings
```
