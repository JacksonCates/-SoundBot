import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

from ChannelCog import Channel
from SoundsCog import Sounds
from SongsCog import Songs
from StatsCog import Stats

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
SQL_USER = os.getenv('SQL_USER')
SQL_PASS = os.getenv('SQL_PASS')
SQL_SERVER = os.getenv('SQL_SERVER')
SQL_DATABASE = os.getenv('SQL_DATABASE')
MP3_DIR = os.getenv('MP3_DIR')
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='.', intents=intents)

@bot.event
async def on_command_error(ctx, error):
    if "kiwikiwikiwi" in str(error): # dont do anything we already replied
        pass
    elif "Command" in str(error) and "is not found" in str(error):
        await ctx.reply("Meow! (I don't know that command dummy)")
    else:
        await ctx.reply(f"meow meow meow.... (An unknown error occured: {str(error)})")

async def setup(bot):
    await bot.add_cog(Channel(bot))
    #await bot.add_cog(Sounds(bot, SQL_SERVER, SQL_DATABASE, SQL_USER, SQL_PASS, MP3_DIR))
    await bot.add_cog(Songs(bot, SQL_SERVER, SQL_DATABASE, SQL_USER, SQL_PASS, MP3_DIR))
    await bot.add_cog(Stats(bot, SQL_SERVER, SQL_DATABASE, SQL_USER, SQL_PASS, MP3_DIR))

# Adds all the cogs
asyncio.run(setup(bot))

print("---- COGS ----")
print(bot.cogs)

bot.run(BOT_TOKEN)