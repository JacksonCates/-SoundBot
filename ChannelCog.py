import discord
from discord.ext import commands

class Channel(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        await ctx.channel.send("Meow!")
    async def _join(self, ctx):
        if ctx.author.voice is None:
            await ctx.reply("Meow meow, meow! (You need to be in a channel for me to join you!)")
            raise Exception("kiwikiwikiwi")
        if ctx.voice_client is not None and ctx.voice_client.channel != ctx.author.voice.channel: # are they in two seperate channels?
            await self.leave(ctx) # leave the current channel
        channel = ctx.author.voice.channel
        await channel.connect()

    @commands.command(
        help="Leaves the discord channel that the user is currently in",
        brief="Leaves the discord channel that the user is currently in",
        aliases=['l']
    )
    async def leave(self, ctx):
        if ctx.voice_client is None:
            await ctx.reply("Meow? Meow! (What channel do you want me to leave? I'm not in one!)")
            raise Exception("kiwikiwikiwi")
        await ctx.voice_client.disconnect()
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        my_vc = discord.utils.get(self.bot.voice_clients)
        if my_vc is not None and (after.channel is None or after.channel.id != my_vc.channel.id): # if I am in a voice channel and if they leave my channel
            channel = self.bot.get_channel(my_vc.channel.id)
            num_members = len(channel.members)
            if num_members == 1: # its just me
                await my_vc.disconnect()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: # checks if its the bot
            return
        if "austin moment" in message.content.lower():
            await message.channel.send("https://tenor.com/view/austin-moment-austin-moment-ned-flanders-gif-26373698")
        if "calib moment" in message.content.lower():
            await message.channel.send("https://cdn.discordapp.com/attachments/948727499477635082/1090047255265935471/image.png")
        if "butter dog" in message.content.lower():
            songs = self.bot.get_cog("Songs")
            ctx = await self.bot.get_context(message)
            await songs.playsong(ctx, "https://www.youtube.com/watch?v=8V5T6oUOEV4&ab_channel=McMaNGOS")