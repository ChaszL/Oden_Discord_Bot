import discord
from discord.ext import commands
from discord import app_commands
import random
import aiohttp
import asyncio
import html

# --- API Endpoints ---
GENERAL_KNOWLEDGE = "https://opentdb.com/api.php?amount=1&category=9"
JOKE_URL = "https://official-joke-api.appspot.com/random_joke"
QUOTE_API = "https://api.quotable.io/random"
animal_apis = {
    "dog": "https://animals.maxz.dev/api/dog/random",
    "cat": "https://animals.maxz.dev/api/cat/random",
    "rabbit": "https://animals.maxz.dev/api/rabbit/random",
    "capybara": "https://animals.maxz.dev/api/capybara/random",
    "hamster": "https://animals.maxz.dev/api/hamster/random",
    "monkey": "https://animals.maxz.dev/api/monkey/random",
}

# --- Shared Data ---
coin_sides = ["Heads", "Tails"]
eight_ball_sayings = [
    "It is certain.", "It is decidedly so.", "Without a doubt.",
    "Yes – definitely.", "You may rely on it.", "As I see it, yes.",
    "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
    "Don't count on it.", "My reply is no.", "My sources say no.",
    "Outlook not so good.", "Very doubtful.", "Reply hazy, try again.",
    "Ask again later.", "Better not tell you now.", "Cannot predict now.",
    "Concentrate and ask again.",
]

# defining the fun class that inherits intents from main.py
class fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # dictionary to hold active tasks for the count command: {channel_id: asyncio.Task}
        self.active_tasks = {}

    # --- Listener for 'stop' in /count command ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # ignore bot's own messages
        if message.author.bot:
            return

        channel_id = message.channel.id
        
        # check if a count task is running in this channel and if the message is 'stop'
        if channel_id in self.active_tasks and message.content.lower() == "stop":
            # Get the running task
            task_to_cancel = self.active_tasks.get(channel_id)
            
            if task_to_cancel:
                # Cancel the task
                task_to_cancel.cancel()

    # --- Helper function for /count background loop ---
    async def run_count_task(self, interaction: discord.Interaction, number: int):
        channel_id = interaction.channel_id
        current_count = 0
        bot_count = 0
        
        try:
            while True:
                current_count += number
                await interaction.channel.send(current_count)
                bot_count += 1

                # sends the stop reminder every 50 messages
                if bot_count % 50 == 0:
                    await interaction.channel.send("Just say **stop** and I will stop!")

                # wait for one second before the next iteration
                await asyncio.sleep(1.0)

        except asyncio.CancelledError:
            # sends the stop message after being stopped
            await interaction.channel.send(f"Someone stopped me at {current_count}!")
        
        finally:
            # deletes the task from active_task dictonary
            if channel_id in self.active_tasks:
                del self.active_tasks[channel_id]

    # --- /question command ---
    @app_commands.command(name = "question", description = "Asks a general knowledge question with multiple choice answers.")
    async def general_knowledge_question_command(self, interaction: discord.Interaction):
        print(f'''command used: {interaction.command.name}
        user:{interaction.user.id} username:{interaction.user.name}
        server id: {interaction.guild.id} server name: {interaction.guild.name}''')
        print("======================================================================")
       
        await interaction.response.defer()

        async with aiohttp.ClientSession() as session:
            async with session.get(GENERAL_KNOWLEDGE) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    result = data["results"][0]
                    
                    question = html.unescape(result["question"])
                    correct_answer = html.unescape(result["correct_answer"])
                    incorrect_answers = [html.unescape(ans) for ans in result["incorrect_answers"]]
                    answers = incorrect_answers + [correct_answer]
                    random.shuffle(answers)

                    await interaction.followup.send(f"**Question:** {question}\n\n**Options:**\n" + "\n".join(answers))

                    def question_check(message):
                        # checks if new user message is from the author and in the same channel as intitation
                        return message.channel.id == interaction.channel_id and message.author.id != self.bot.user.id

                    try:
                        msg = await self.bot.wait_for("message", check = question_check, timeout = 60.0)
                        guesser = msg.author.mention

                        if msg.content.lower() == correct_answer.lower():
                            await msg.reply(f"✅ Correct, {guesser}!")
                        else:
                            await msg.reply(f"❌ Incorrect, {guesser}... The correct answer is **{correct_answer}!**.")

                    except asyncio.TimeoutError:
                        await interaction.followup.send("Time's up! You took too long to respond. The correct answer was: **" + correct_answer + "**")
                
                else:
                    await interaction.followup.send(f"Could not fetch a question. The server responded with status code: {response.status}")

    # --- /joke command ---
    @app_commands.command(name = "joke", description = "Tells a joke and lets you guess the punchline.")
    async def joke_command(self, interaction: discord.Interaction):
        print(f'''command used: {interaction.command.name}
        user:{interaction.user.id} username:{interaction.user.name}
        server id: {interaction.guild.id} server name: {interaction.guild.name}''')
        print("======================================================================")
        
        await interaction.response.defer()

        async with aiohttp.ClientSession() as session:
            async with session.get(JOKE_URL) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    setup = data['setup']
                    punchline = data['punchline']
                    await interaction.followup.send(setup)

                    def joke_check(message):
                        # helper function that checks if new user message is from the author and in the same channel as intitation
                        return message.channel.id == interaction.channel_id and message.author.id != self.bot.user.id
                    
                    try:
                        msg = await self.bot.wait_for("message", check = joke_check, timeout = 60.0)
                        guesser = msg.author.mention
                        
                        if msg.content.lower() == punchline.lower():
                            await msg.reply(f"{guesser} you're quite the jokester! 😂")
                        else:
                            await msg.reply(f"Good guess! its actually: {punchline}! GET IT!! 😂😂😂")

                    except asyncio.TimeoutError:
                        await interaction.followup.send("You took too long to respond so here's the punchline!: " + punchline)
                
                else:
                    await interaction.followup.send("Could not fetch a joke right now")

    # --- /count command ---
    @app_commands.command(name = "count", description = "Counts up by a specified number until someone says 'stop'.")
    @app_commands.describe(number = "The integer value to count up by.")
    async def count_by_command(self, interaction: discord.Interaction, number: int):
        print(f'''command used: {interaction.command.name}
        user:{interaction.user.id} username:{interaction.user.name}
        server id: {interaction.guild.id} server name: {interaction.guild.name}''')
        print("======================================================================")

        channel_id = interaction.channel_id
        
        if channel_id in self.active_tasks:
            await interaction.response.send_message("I'm already counting in this channel. Say **stop** to end it.", ephemeral=True)
            return

        await interaction.response.defer()
        
        await interaction.followup.send(f"I will start counting by {number}\nJust say **stop** and I will stop!")

        # create and start the background task
        task = self.bot.loop.create_task(self.run_count_task(interaction, number))
        
        # store the task object for cancellation later
        self.active_tasks[channel_id] = task

    # --- /whisper command ---
    @app_commands.command(name = "whisper", description = "Sends a private message to a specific server member.")
    @app_commands.describe(member = "The member to receive the private message.", message = "The content of your secret whisper.")
    async def whisper_command(self, interaction: discord.Interaction, member: discord.Member, message: str):
        print(f'''command used: {interaction.command.name}
        user:{interaction.user.id} username:{interaction.user.name}
        server id: {interaction.guild.id} server name: {interaction.guild.name}''')
        print("======================================================================")

        await interaction.response.defer(ephemeral = True)

        try:
            await member.send(f"Someone whispers to you from **{interaction.guild.name}**: \n{message}")
            await interaction.followup.send(f"Successfully whispered your message to **{member.display_name}**.", ephemeral=True)
            
        except discord.Forbidden: 
            await interaction.followup.send(f"Failed to send whisper to **{member.display_name}**. They likely have DMs disabled.", ephemeral=True)
            
        except Exception as e:
            print(f"An error occurred while dm'ing: {e}")
            await interaction.followup.send("An unexpected error occurred while trying to send the whisper.", ephemeral=True)

    # --- /animal command ---
    @app_commands.command(name = "animal", description = "fetches a random picture of a selected animal.")
    @app_commands.describe(animal = "choose the animal you want a random picture of.")
    @app_commands.choices(animal = [
            app_commands.Choice(name = "dog 生", value = "dog"),
            app_commands.Choice(name = "cat 棲", value = "cat"),
            app_commands.Choice(name = "rabbit 睡", value = "rabbit"),
            app_commands.Choice(name = "capybara ", value = "capybara"),
            app_commands.Choice(name = "hamster 聖", value = "hamster"),
            app_commands.Choice(name = "monkey 崇", value = "monkey"),
        ]
    )
    async def animal_picture_command(self, interaction: discord.Interaction, animal: app_commands.Choice[str]):
        # splits the animal name and saves only the first part of the name value
        animal_name = animal.name.split()[0]
        # gets the value of the picked animal and saves the url
        api_url = animal_apis.get(animal.value)

        print(f'''command used: {interaction.command.name} animal: {animal.name}
        user:{interaction.user.id} username:{interaction.user.name}
        server id: {interaction.guild.id} server name: {interaction.guild.name}''')
        print("======================================================================")

        await interaction.response.defer()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        image_url = data.get("image")
                        # The original files used set_image on an Embed()
                        embed = discord.Embed()
                        embed.set_image(url=image_url)
                        await interaction.followup.send(f"here is your random **{animal_name}** picture!:", embed=embed)

                    else:
                        await interaction.followup.send(f"i couldn't fetch a **{animal_name}** picture right now. (status: {response.status})", ephemeral=True)
                        
        except Exception as e:
            await interaction.followup.send(f"an error occurred: {e}", ephemeral=True)

    # --- /flipcoin command ---
    @app_commands.command(name = "flipcoin", description = "Ask the bot to flip a coin and get heads or tails.")
    @app_commands.describe(question = "The question you would like to ask.")
    async def flipcoin_command(self, interaction: discord.Interaction, question: str):
        print(f'''command used: {interaction.command.name}
        user:{interaction.user.id} username:{interaction.user.name}
        server id: {interaction.guild.id} server name: {interaction.guild.name}''')
        print("======================================================================")

        await interaction.response.defer()

        answer = random.choice(coin_sides)
        await interaction.followup.send(answer, ephemeral = False)

    # --- /quote command ---
    @app_commands.command(name = "quote", description = "Sends a quote and its author.")
    async def quote_command(self, interaction: discord.Interaction):
        print(f'''command used: {interaction.command.name}
        user:{interaction.user.id} username:{interaction.user.name}
        server id: {interaction.guild.id} server name: {interaction.guild.name}''')
        print("======================================================================")
        
        await interaction.response.defer()

        async with aiohttp.ClientSession() as session:
            async with session.get(QUOTE_API) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    content = data['content']
                    author = data['author']
                    await interaction.followup.send(f"\"{content}\" by {author}")
                else:
                    await interaction.followup.send("Could not fetch a quote right now")

    # --- /8ball command ---
    @app_commands.command(name = "8ball", description = "Ask the 8-Ball a question.")
    @app_commands.describe(question = "The question you would like to ask.")
    async def eight_ball_command(self, interaction: discord.Interaction, question: str):
        print(f'''command used: {interaction.command.name}
        user:{interaction.user.id} username:{interaction.user.name}
        server id: {interaction.guild.id} server name: {interaction.guild.name}''')
        print("======================================================================")

        await interaction.response.defer()

        answer = random.choice(eight_ball_sayings)
        await interaction.followup.send(answer, ephemeral = False)

# bot setup 
async def setup(bot):
    await bot.add_cog(fun(bot))