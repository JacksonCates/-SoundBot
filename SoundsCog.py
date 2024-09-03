import discord
from discord.ext import commands
from repos import SoundsDatabase, RequestDatabase
from datetime import datetime
import asyncio
import os

class Sounds(commands.Cog):
    def __init__(self, bot, SQL_SERVER, SQL_DATABASE, SQL_USER, SQL_PASS, MP3_DIR) -> None:
        self.bot = bot
        self.SQL_SERVER = SQL_SERVER
        self.SQL_DATABASE = SQL_DATABASE
        self.SQL_USER = SQL_USER
        self.SQL_PASS = SQL_PASS
        self.MP3_DIR = MP3_DIR

    @commands.command(
        help="Plays a sound! If the bot is not in the discord channel it will automatically join.",
        brief="Plays a sound!",
        aliases=['ps']
    )
    async def playsound(self, ctx, sound: str = commands.parameter(description="Name of the sound to be played")):
        """
        Parameters:
        sound (str): Name of the sound you would like to play.
        """
        channel = self.bot.get_cog("Channel")
        if ctx.voice_client is None: # am I not in a channel?
            await channel._join(ctx) # Joins!
        if ctx.author.voice is None:
            await ctx.reply("MEOW! (You specifically need to be in a voice channel to request any sounds!)")
            raise Exception("kiwikiwikiwi")
        if ctx.voice_client.channel != ctx.author.voice.channel: # am I not in the same channel as the guy requesting a sound?
            await channel._join(ctx) # Joins!
        if ctx.voice_client.is_playing():
            await ctx.reply("Meow, meow! (I am currently playing something, please wait!)")
            raise Exception("kiwikiwikiwi")

        db = SoundsDatabase(self.SQL_SERVER, self.SQL_DATABASE, self.SQL_USER, self.SQL_PASS)
        sound = db.get_sound_by_name(sound, "SOUND")
        if sound is None:
            await ctx.reply("Meow, meow (Sound does not exist, try using .listsounds to see all sounds)")
            raise Exception("kiwikiwikiwi")
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S') 

        # Add it to the requests database
        db = RequestDatabase(self.SQL_SERVER, self.SQL_DATABASE, self.SQL_USER, self.SQL_PASS)
        db.add_request(sound["id"], ctx.author.name, now)

        ctx.voice_client.play(discord.FFmpegPCMAudio(executable="ffmpeg.exe", source=os.path.join(self.MP3_DIR, sound["mp3"])))
        ctx.voice_client.source = discord.PCMVolumeTransformer(ctx.voice_client.source, volume=sound["volume"])


    @commands.command(
        help="Adds a sound",
        brief="Adds a sound",
        aliases=['as']
    )
    async def addsound(self, ctx):
        await ctx.reply("Meow meow, meow, meow. (Ok, all you need to do is copy and paste this message, fill it out, and reply back to me. Make sure to attach your .mp3!)")
        await ctx.send("```Name (1 word):\nEmoji:```")

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            await ctx.reply("Meow, meow (You took too long! Use .addsound to try again)")
            raise Exception("kiwikiwikiwi")
        
        # verify that the message is correct
        cont = msg.content
        atms = msg.attachments

        if "Name (1 word):" not in cont or "Emoji:" not in cont:
            await ctx.reply("Meow meow! (Invalid format, just copy and paste it dummy! Use .addsound to try again)")
            raise Exception("kiwikiwikiwi")
        if len(atms) != 1:
            await ctx.reply("Meow.... (You either forgot to add a .mp3 or add multiple files, use .addsound to try again)")
            raise Exception("kiwikiwikiwi")
        atm = atms[0]
        lines = cont.splitlines()
        name = lines[0].split(":", 1)[1]

        words = name.split(" ")
        if len(words) == 2 and words[0] == "": # Checks if the first is white space
            words = words[1:]
        if len(words) != 1:
            await ctx.reply("Meow meow (Your name can only be 1 word. Use .addsound to try again.)")
            raise Exception("kiwikiwikiwi")
        emoji = lines[1].split(":", 1)[1]
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S') 

        # Download the file
        db = SoundsDatabase(self.SQL_SERVER, self.SQL_DATABASE, self.SQL_USER, self.SQL_PASS)
        mp3_path, length, size = db.download_sound_file(atm.filename, atm.url, self.MP3_DIR)

        # adds it to the database
        db.add_sound(name.strip().lower(), emoji, now, atm.filename, ctx.author.name, "SOUND", size, length)

    @commands.command(
        help="Shows currently stored sounds",
        brief="Shows currently stored sounds",
        aliases=['ls']
    )
    async def listsounds(self, ctx, page: int = commands.parameter(default=1, description="Page number of list of sounds")):
        # Download the file
        db = SoundsDatabase(self.SQL_SERVER, self.SQL_DATABASE, self.SQL_USER, self.SQL_PASS)
        sounds, total_pages = db.get_all_sounds(page, "SOUND")

        embed=discord.Embed(title="Sounds", description=f"Page {page}/{total_pages}")
        for s in sounds:
            embed.add_field(name=s["emoji"] + " " + s["name"], value="\u200b", inline=False)
        await ctx.reply(embed=embed)

    @commands.command(
        help="Shows details for a sound",
        brief="Shows details for a sound",
        aliases=['sd']
    )
    async def sounddetail(self, ctx, sound: str = commands.parameter(description="The name of the sound to view details of")):
        db = SoundsDatabase(self.SQL_SERVER, self.SQL_DATABASE, self.SQL_USER, self.SQL_PASS)
        sound = db.get_sound_by_name(sound, "SOUND")
        if sound is None:
            await ctx.reply("Meow, meow (Sound does not exist, try using .listsounds to see all sounds)")
            raise Exception("kiwikiwikiwi")

        embed=discord.Embed(title=sound["emoji"] + " " + sound["name"])
        embed.add_field(name="date_added", value=sound["date_added"], inline=False)
        embed.add_field(name="mp3", value=sound["mp3"], inline=False)
        embed.add_field(name="added_by", value=sound["added_by"], inline=False)
        embed.add_field(name="file size", value=str(sound["size"] * 0.000008) + " MB", inline=False)
        embed.add_field(name="audio length", value=str(sound["length"]) + " seconds", inline=False)
        embed.add_field(name="volume", value=str(sound["volume"]*100) + " %", inline=False)
        embed.set_footer(text="id = " + str(sound["id"]) + " | type = " + sound["type"])
        await ctx.reply(embed=embed)