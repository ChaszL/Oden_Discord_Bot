import os
import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
from yt_dlp.utils import DownloadError
from collections import deque
import asyncio

# --- yt-dlp options ---
YTDL_OPTIONS = {
    'format': 'bestaudio[abr<=96]/bestaudio/best',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'cookiefile': 'cookies.txt',
    'youtube_include_dash_manifest': False,
    'youtube_include_hls_manifest': False,
    # Required so yt-dlp can fetch the JS challenge-solver script it needs to
    # decode YouTube's signature/n-challenges (same as CLI --remote-components ejs:github).
    'remote_components': ['ejs:github'],
    # Try multiple clients — if one gets SABR-restricted for a given video,
    # yt-dlp can still pull formats from another.
    'extractor_args': {
        'youtube': {
            'player_client': ['android_music', 'ios', 'web'],
            'player_skip': ['configs', 'webpage']
        }
    }
}

# Fallback uses a genuinely different client set (not just a different format
# string) since "Requested format is not available" usually means every
# client in the primary list got restricted for that particular video.
FALLBACK_YTDL_OPTIONS = {
    **YTDL_OPTIONS,
    'format': 'bestaudio/best',
    'extractor_args': {
        'youtube': {
            'player_client': ['tv', 'web_safari', 'mweb'],
        }
    },
}

# Point this at your ffmpeg binary if it's not on your system PATH,
# e.g. set FFMPEG_PATH=C:\ffmpeg\bin\ffmpeg.exe on Windows.
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn -c:a libopus -b:a 96k",
}


async def search_ytdlp_async(query, ydl_opts):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: _extract(query, ydl_opts))


def _extract(query, ydl_opts):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(query, download=False)


async def search_with_fallback(song_query):
    """Search using the primary client set, retrying with a different
    client set if YouTube rejects every format for the primary one."""
    query = "ytsearch1: " + song_query
    try:
        results = await search_ytdlp_async(query, YTDL_OPTIONS)
    except DownloadError as exc:
        if 'Requested format is not available' not in str(exc):
            raise
        results = await search_ytdlp_async(query, FALLBACK_YTDL_OPTIONS)
    return results.get("entries", []) if results else []


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_queues = {}  # guild_id (str) -> deque[(audio_url, title)]

    # --- /join ---
    @app_commands.command(name="join", description="Joins your current voice channel.")
    async def join_command(self, interaction: discord.Interaction):
        await interaction.response.defer()

        if not interaction.user.voice:
            await interaction.followup.send("❌ You are not connected to a voice channel.")
            return

        channel = interaction.user.voice.channel
        if not interaction.guild.voice_client:
            await channel.connect()
            await interaction.followup.send(f"✅ Joined **{channel.name}**")
        else:
            await interaction.guild.voice_client.move_to(channel)
            await interaction.followup.send(f"✅ Moved to **{channel.name}**")

    # --- /play ---
    @app_commands.command(name="play", description="Play a song or add it to the queue.")
    @app_commands.describe(song_query="Song name or URL you want to play.")
    async def play_command(self, interaction: discord.Interaction, song_query: str):
        await interaction.response.defer()

        if not interaction.user.voice:
            await interaction.followup.send("❌ You need to join a voice channel first.")
            return

        voice_channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client

        if voice_client is None:
            voice_client = await voice_channel.connect()
        elif voice_channel != voice_client.channel:
            await voice_client.move_to(voice_channel)

        try:
            tracks = await search_with_fallback(song_query)
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred while searching: {e}")
            return

        if not tracks:
            await interaction.followup.send("❌ No results found.")
            return

        first_track = tracks[0]
        audio_url = first_track["url"]
        title = first_track.get("title", "Untitled")

        guild_id = str(interaction.guild_id)
        if guild_id not in self.song_queues:
            self.song_queues[guild_id] = deque()

        self.song_queues[guild_id].append((audio_url, title))

        if voice_client.is_playing() or voice_client.is_paused():
            await interaction.followup.send(f"➕ Added to queue: **{title}**")
        else:
            await interaction.followup.send(f"🎶 Now playing: **{title}**")
            await self.play_next_song(voice_client, guild_id, interaction.channel)

    async def play_next_song(self, voice_client, guild_id, channel):
        if self.song_queues.get(guild_id):
            audio_url, title = self.song_queues[guild_id].popleft()

            source = discord.FFmpegOpusAudio(audio_url, **FFMPEG_OPTIONS, executable=FFMPEG_PATH)

            def after_play(error):
                if error:
                    print(f"Error playing {title}: {error}")
                asyncio.run_coroutine_threadsafe(
                    self.play_next_song(voice_client, guild_id, channel), self.bot.loop
                )

            voice_client.play(source, after=after_play)
            asyncio.create_task(channel.send(f"🎶 Now playing: **{title}**"))
        else:
            await voice_client.disconnect()
            self.song_queues[guild_id] = deque()

    # --- /skip ---
    @app_commands.command(name="skip", description="Skips the current playing song.")
    async def skip_command(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            voice_client.stop()  # triggers after_play -> play_next_song
            await interaction.response.send_message("⏭️ Skipped the current song.")
        else:
            await interaction.response.send_message("❌ Not playing anything to skip.")

    # --- /pause ---
    @app_commands.command(name="pause", description="Pauses the current song.")
    async def pause_command(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if voice_client is None:
            await interaction.response.send_message("❌ I'm not in a voice channel.")
        elif not voice_client.is_playing():
            await interaction.response.send_message("❌ Nothing is currently playing.")
        else:
            voice_client.pause()
            await interaction.response.send_message("⏸️ Paused the music.")

    # --- /resume ---
    @app_commands.command(name="resume", description="Resumes the paused song.")
    async def resume_command(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if voice_client is None:
            await interaction.response.send_message("❌ I'm not in a voice channel.")
        elif not voice_client.is_paused():
            await interaction.response.send_message("❌ The audio is not paused.")
        else:
            voice_client.resume()
            await interaction.response.send_message("▶️ Resumed the music.")

    # --- /stop ---
    @app_commands.command(name="stop", description="Stops playback, clears the queue, and disconnects.")
    async def stop_command(self, interaction: discord.Interaction):
        await interaction.response.defer()

        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            await interaction.followup.send("❌ I am not connected to a voice channel.")
            return

        guild_id = str(interaction.guild_id)
        if guild_id in self.song_queues:
            self.song_queues[guild_id].clear()

        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop()

        await voice_client.disconnect()
        await interaction.followup.send("⏹️ Music stopped and I left the channel.")


async def setup(bot):
    await bot.add_cog(Music(bot))