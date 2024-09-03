import discord
from discord.ext import commands
from repos import SoundsDatabase, RequestDatabase
from datetime import datetime
import os
from pytube import YouTube
import pytube
import asyncio
import math
import random
import re
from abc import ABC, abstractmethod

# A good ole queue
class Queue(ABC):
    def __init__(self) -> None:
        self.q = []

    def get_queue(self):
        return self.q.copy()
    
    @abstractmethod
    def name(self):
        raise NotImplementedError

    @abstractmethod
    def add(self, item):
        raise NotImplementedError()

    def peek(self):
        if len(self.q) < 1:
            return None
        return self.q[0]
    
    def next(self):
        if len(self.q) < 1:
            return None
        return self.q.pop(0)
    
    def len(self):
        return len(self.q)

    def clear(self):
        self.q = []

    def set_queue(self, q):
        self.q = q.copy()

class StandardQueue(Queue):
    def add(self, item):
        self.q.append(item)

    def name(self):
        return "Standard Queue"

class RandomQueue(Queue):
    def add(self, item):
        if self.len() > 0:
            random_index = random.randint(1, len(self.q))
            self.q.insert(random_index, item)
        else:
            self.q.append(item)

    def name(self):
        return "Random Queue"
    
class PlayRandomIfEmpty(Queue):
    def __init__(self, songsdb) -> None:
        super().__init__()
        self.db = songsdb
        self.clearflag = False

    def add(self, item):
        self.clearflag = False
        self.q.append(item)

    def next(self):
        if len(self.q) <= 1 and self.clearflag == False:
            # Adds random song
            song = self.db.get_random_sound("SONG")
            song["requested_by"] = "the dice gods"
            self.q.append(song)
        return self.q.pop(0)

    def clear(self):
        self.clearflag = True
        self.q = []

    def name(self):
        return "Random Songs If Empty"

def queueFactory(str, q: Queue, db):
    if str == "RandomQueue":
        new_q = RandomQueue()
    elif str == "StandardQueue":
        new_q = StandardQueue()
    elif str == "RandomIfEmpty":
        new_q = PlayRandomIfEmpty(db)
    else:
        raise ValueError(f"Invalid choice of queue. Choice was {str}")
    new_q.set_queue(q.get_queue())
    return new_q

class Songs(commands.Cog):
    def __init__(self, bot, SQL_SERVER, SQL_DATABASE, SQL_USER, SQL_PASS, MP3_DIR) -> None:
        self.bot = bot
        self.SQL_SERVER = SQL_SERVER
        self.SQL_DATABASE = SQL_DATABASE
        self.SQL_USER = SQL_USER
        self.SQL_PASS = SQL_PASS
        self.MP3_DIR = MP3_DIR

        db = SoundsDatabase(self.SQL_SERVER, self.SQL_DATABASE, self.SQL_USER, self.SQL_PASS)
        self.queue = PlayRandomIfEmpty(db)

    async def _check_queue(self, ctx, error):
        if error:
            raise error
        self.queue.next()
        if self.queue.len() > 0:
            await self._play(ctx)

    async def _play(self, ctx):
        song = self.queue.peek()
        ctx.voice_client.play(discord.FFmpegPCMAudio(executable="ffmpeg.exe", source=os.path.join(self.MP3_DIR, song["mp3"])), after=lambda error=None: asyncio.run_coroutine_threadsafe(self._check_queue(ctx, error), self.bot.loop))
        ctx.voice_client.source = discord.PCMVolumeTransformer(ctx.voice_client.source, volume=song["volume"])
        await ctx.send("Now playing: `" + song["name"] + "` requested by `" + song["requested_by"] + "`")

    @commands.command(
        help="Pick the type of queue to use",
        brief="Pick the type of queue to use",
        aliases=['pq']
    )
    async def pickqueue(self, ctx):
        options = ["Standard Queue", "RANDOM Queue", "Random Song If Empty"]  # list of options to present to the user
        optoinsval = ["StandardQueue", "RandomQueue", "RandomIfEmpty"]
        
        # create an embed with the list of options
        embed = discord.Embed(title='Please select an option:', description='\n'.join([f'{i+1}. {opt}' for i, opt in enumerate(options)]), color=0x00ff00)
        
        # send the embed to the user
        options_message = await ctx.reply(embed=embed)
        
        # add reactions to the message for each option
        for i in range(len(options)):
            await options_message.add_reaction(f'{i+1}\u20e3')
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in [f'{i+1}\u20e3' for i in range(len(options))]  # check if the reaction is from the message author and is one of the option reactions
        
        # wait for the user to react with an option
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await ctx.reply('Timed out. Please try again.')
        else:
            # get the index of the selected option and send a message with the selection
            option_index = int(str(reaction.emoji)[0]) - 1
            selected_option = options[option_index]
            await ctx.reply(f'You selected {selected_option}.')
            self.queue = queueFactory(optoinsval[option_index], self.queue, SoundsDatabase(self.SQL_SERVER, self.SQL_DATABASE, self.SQL_USER, self.SQL_PASS))

    @commands.command(
        help="Shows the current queue",
        brief="Shows the current queue",
        aliases=['sq']
    )
    async def showqueue(self, ctx, page: int = commands.parameter(default=1, description="Page number of list of sounds")):
        q = self.queue.get_queue()

        page_length = 20
        total_pages = math.ceil(len(q) / page_length)
        offset = (page-1)*20
        q = q[offset:offset+page_length]

        embed=discord.Embed(title=f"Queue ({self.queue.name()})", description=f"Page {page}/{total_pages}")
        for i, s in enumerate(q):
            display_str = s["name"] + " (" + str(s["length"]) + " seconds)"
            if i == 0: # first one=
                display_str += " (Currently playing)"
            embed.add_field(name=display_str, value="\u200b", inline=False)
        await ctx.reply(embed=embed)

    async def get_youtube_song(self, ctx, url):
        db = SoundsDatabase(self.SQL_SERVER, self.SQL_DATABASE, self.SQL_USER, self.SQL_PASS)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S') 

        yt = YouTube(url, use_oauth=True, allow_oauth_cache=True) 
        sound = db.get_sound_by_name(yt.title, "SONG")
        if sound is None:
            # Does not currently exists in our collection, download!
            video = yt.streams.get_audio_only()
            video_id = pytube.extract.video_id(url)
            mp4_name = f"{video_id}.mp4"
            video.download(self.MP3_DIR, mp4_name)
            length, size = db.get_mp4_size_and_length(os.path.join(self.MP3_DIR, mp4_name))
            db.add_sound(yt.title, "", now, mp4_name, ctx.author.name, "SONG", size, length)
            sound = db.get_sound_by_name(yt.title, "SONG")
        return sound

    async def get_song_by_name(self, ctx, url):
        db = SoundsDatabase(self.SQL_SERVER, self.SQL_DATABASE, self.SQL_USER, self.SQL_PASS)
        sounds = db.search_sound_by_name(url, "SONG")

        # Checks if we found it!
        if len(sounds) == 1:
            return sounds[0]

        s = "Meow... (I found multiple songs with this name, try to be more specific. Here is what I found:"
        for sound in sounds:
            s += f"\n- `{sound['name']}`"
        await ctx.reply(s)
        raise Exception("kiwikiwikiwi")

    @commands.command(
        help="Plays a song from a youtube url",
        brief="Plays a song from a youtube url",
        aliases=['p']
    )
    async def playsong(self, ctx, url: str = commands.parameter(description="Youtube url of the song to be played or the name of the song", default="")):
        """
        Parameters:
        sound (str): Name of the sound you would like to play.
        """
        channel = self.bot.get_cog("Channel")
        if ctx.voice_client is None: # am I not in a channel?
            self.queue.clear()
            await channel._join(ctx) # Joins!
        if ctx.author.voice is None:
            await ctx.reply("MEOW! (You specifically need to be in a voice channel to request any sounds!)")
            raise Exception("kiwikiwikiwi")
        if ctx.voice_client.channel != ctx.author.voice.channel: # am I not in the same channel as the guy requesting a sound?
            if ctx.voice_client.is_playing(): # checks if something in the queue
                await ctx.reply("Meow meow meow! (I am currently playing something, come join my channel!)")
                raise Exception("kiwikiwikiwi")
            self.queue.clear()
            await channel._join(ctx) # Joins!
        
        youtube_url_pattern = r"https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+"
        matches = re.findall(youtube_url_pattern, url)
        db = SoundsDatabase(self.SQL_SERVER, self.SQL_DATABASE, self.SQL_USER, self.SQL_PASS)
        if url is None or url.strip() == "": # RANDOM SONG
            if self.queue.len() > 0: # Throws an error if the bot is already playing
                await ctx.reply("Meow meow (You need a URL!)")
                raise Exception("kiwikiwikiwi")
            sound = db.get_random_sound("SONG") # Plays a song if the bot is chillin
        elif matches: # User picked a URL
            sound = await self.get_youtube_song(ctx, url)
        else:
            sound = await self.get_song_by_name(ctx, url)

        # Add it to the requests database
        db = RequestDatabase(self.SQL_SERVER, self.SQL_DATABASE, self.SQL_USER, self.SQL_PASS)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S') 
        db.add_request(sound["id"], ctx.author.name, now)

        # adds to the queue
        sound["requested_by"] = ctx.author.name
        self.queue.add(sound)

        if self.queue.len() == 1: # only item in the queue!
            await self._play(ctx)
        else:
            await ctx.reply("Added `" + sound["name"] + "` to the queue (" + str(self.queue.len() - 1) + ")")

    @commands.command(
        help="Resumes what ever it is currently playing",
        brief="Resumes what ever it is currently playing",
        aliases=['r']
    )
    async def resume(self, ctx):
        if ctx.voice_client is None: # am I not in a channel?
            await ctx.reply("Meow? (How can I resume anything if I'm not in a channel?)")
            raise Exception("kiwikiwikiwi")
        if ctx.author.voice is None or ctx.voice_client.channel != ctx.author.voice.channel:
            await ctx.reply("MEOW! (You specifically need to be in a voice channel to request any sounds!)")
            raise Exception("kiwikiwikiwi")
        if ctx.voice_client.is_playing():
            await ctx.reply("Meow (Im not paused!)")
            raise Exception("kiwikiwikiwi")
        
        ctx.voice_client.resume()

    @commands.command(
        help="Pauses what ever it is currently playing",
        brief="Pauses what ever it is currently playing",
        aliases=['pu']
    )
    async def pause(self, ctx):
        if ctx.voice_client is None: # am I not in a channel?
            await ctx.reply("Meow? (How can I pause anything if I'm not in a channel?)")
            raise Exception("kiwikiwikiwi")
        if ctx.author.voice is None or ctx.voice_client.channel != ctx.author.voice.channel:
            await ctx.reply("MEOW! (You specifically need to be in a voice channel to request any sounds!)")
            raise Exception("kiwikiwikiwi")
        if ctx.voice_client.is_playing() == False:
            await ctx.reply("Meow (Im not playing anything)")
            raise Exception("kiwikiwikiwi")
        
        ctx.voice_client.pause()

    @commands.command(
        help="Changes the volume of the currently played song",
        brief="Changes the volume of the currently played song",
        aliases=['v']
    )
    async def volume(self, ctx, vol: float = commands.parameter(description="Volume to change to. Must be between 1-100")):
        if ctx.voice_client is None: # am I not in a channel?
            await ctx.reply("Meow? (How can I stop playing anything if I'm not in a channel?)")
            raise Exception("kiwikiwikiwi")
        if ctx.author.voice is None or ctx.voice_client.channel != ctx.author.voice.channel:
            await ctx.reply("MEOW! (You specifically need to be in a voice channel to request any sounds!)")
            raise Exception("kiwikiwikiwi")
        if ctx.voice_client.is_playing() == False:
            await ctx.reply("Meow (Im not playing anything)")
            raise Exception("kiwikiwikiwi")
        if vol < 1 or vol > 100:
            await ctx.reply("Meow meow, meow meow meow (You must have your volume between 1-100)")
            raise Exception("kiwikiwikiwi")
        
        song = self.queue.peek()

        ctx.voice_client.source.volume = vol / 100
        db = SoundsDatabase(self.SQL_SERVER, self.SQL_DATABASE, self.SQL_USER, self.SQL_PASS)
        db.update_sound(song["id"], volume=vol/100)

    @commands.command(
        help="Goes to the next song in the queue",
        brief="Goes to the next song in the queue",
        aliases=['n']
    )
    async def next(self, ctx):
        if ctx.voice_client is None: # am I not in a channel?
            await ctx.reply("Meow? (How can I stop playing anything if I'm not in a channel?)")
            raise Exception("kiwikiwikiwi")
        if ctx.author.voice is None or ctx.voice_client.channel != ctx.author.voice.channel:
            await ctx.reply("MEOW! (You specifically need to be in a voice channel to request any sounds!)")
            raise Exception("kiwikiwikiwi")
        if ctx.voice_client.is_playing() == False:
            await ctx.reply("Meow (Im not playing anything)")
            raise Exception("kiwikiwikiwi")
        
        ctx.voice_client.stop()

    @commands.command(
        help="Stops what ever it is currently playing",
        brief="Stops what ever it is currently playing",
        aliases=['s']
    )
    async def stop(self, ctx):
        if ctx.voice_client is None: # am I not in a channel?
            await ctx.reply("Meow? (How can I stop playing anything if I'm not in a channel?)")
            raise Exception("kiwikiwikiwi")
        if ctx.author.voice is None or ctx.voice_client.channel != ctx.author.voice.channel:
            await ctx.reply("MEOW! (You specifically need to be in a voice channel to request any sounds!)")
            raise Exception("kiwikiwikiwi")
        if ctx.voice_client.is_playing() == False:
            await ctx.reply("Meow (Im not playing anything)")
            raise Exception("kiwikiwikiwi")
        
        self.queue.clear()
        ctx.voice_client.stop()

    @commands.command(
        help="Shows currently stored songs",
        brief="Shows currently stored songs",
        aliases=['ls']
    )
    async def listsongs(self, ctx, page: int = commands.parameter(default=1, description="Page number of list of sounds")):
        # Download the file
        db = SoundsDatabase(self.SQL_SERVER, self.SQL_DATABASE, self.SQL_USER, self.SQL_PASS)
        sounds, total_pages = db.get_all_sounds("SONG", page)

        embed=discord.Embed(title="Sounds", description=f"Page {page}/{total_pages}")
        for s in sounds:
            embed.add_field(name=s["name"] + " - `" + s["added_by"] + "`", value="\u200b", inline=False)
        await ctx.reply(embed=embed)

    @commands.command(
    help="Deletes a sound",
    brief="Deletes a sound"
    )
    async def delete(self, ctx, sound: str = commands.parameter(description="The name of the sound to delete")):
        db = SoundsDatabase(self.SQL_SERVER, self.SQL_DATABASE, self.SQL_USER, self.SQL_PASS)
        sound = await self.get_song_by_name(ctx, sound)
        if sound is None:
            await ctx.reply("Meow, meow (Sound does not exist, try using .listsounds to see all sounds)")
            raise Exception("kiwikiwikiwi")

        db.delete_sound(sound["id"])

        await ctx.reply(f"Sound `{sound['name']}` deleted!")

    async def get_deleted_song_by_name(self, ctx, url):
        db = SoundsDatabase(self.SQL_SERVER, self.SQL_DATABASE, self.SQL_USER, self.SQL_PASS)
        sounds = db.search_deleted_sound_by_name(url, "SONG")

        # Checks if we found it!
        if len(sounds) == 1:
            return sounds[0]

        s = "Meow... (I found multiple songs with this name, try to be more specific. Here is what I found:"
        for sound in sounds:
            s += f"\n- `{sound['name']}`"
        await ctx.reply(s)
        raise Exception("kiwikiwikiwi")
    @commands.command(
    help="Undelete a sound",
    brief="Undelete a sound"
    )
    async def undelete(self, ctx, sound: str = commands.parameter(description="The name of the sound to undelete")):
        db = SoundsDatabase(self.SQL_SERVER, self.SQL_DATABASE, self.SQL_USER, self.SQL_PASS)
        sound = await self.get_deleted_song_by_name(ctx, sound)
        if sound is None:
            await ctx.reply("Meow, meow (Sound does not exist, try using .listsounds to see all sounds)")
            raise Exception("kiwikiwikiwi")

        db.undelete_sound(sound["id"])

        await ctx.reply(f"Sound `{sound['name']}` undelete!")

    @commands.command(
        help="Shows details for a song",
        brief="Shows details for a sound",
        aliases=['d']
    )
    async def detail(self, ctx, sound: str = commands.parameter(description="The name of the sound to view details of")):
        db = SoundsDatabase(self.SQL_SERVER, self.SQL_DATABASE, self.SQL_USER, self.SQL_PASS)
        sound = await self.get_song_by_name(ctx, sound)
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