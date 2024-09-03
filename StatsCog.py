import discord
from discord.ext import commands
from repos import SoundsDatabase, RequestDatabase
from datetime import datetime
import asyncio
import os

class Stats(commands.Cog):
    def __init__(self, bot, SQL_SERVER, SQL_DATABASE, SQL_USER, SQL_PASS, MP3_DIR) -> None:
        self.bot = bot
        self.SQL_SERVER = SQL_SERVER
        self.SQL_DATABASE = SQL_DATABASE
        self.SQL_USER = SQL_USER
        self.SQL_PASS = SQL_PASS
        self.MP3_DIR = MP3_DIR

    @commands.command(
        help="Shows general statistics for the bot.",
        brief="Shows general statistics for the bot!"
    )
    async def stats(self, ctx):

        db = SoundsDatabase(self.SQL_SERVER, self.SQL_DATABASE, self.SQL_USER, self.SQL_PASS)
        sounds = db.get_all_sounds("SONG")
        db = RequestDatabase(self.SQL_SERVER, self.SQL_DATABASE, self.SQL_USER, self.SQL_PASS)
        requests = db.get_all_request()
        
        num_songs = len(sounds)
        num_request = len(requests)
        size = 0
        length = 0
        user_dict_add = {}
        for song in sounds:
            size += song["size"]
            length += song["length"]
            if song["added_by"] not in user_dict_add:
                user_dict_add[song["added_by"]] = 1
            else:
                user_dict_add[song["added_by"]] += 1
        sorted_add_keys = sorted(user_dict_add, key=user_dict_add.get, reverse=True)

        total_playtime = 0
        db = SoundsDatabase(self.SQL_SERVER, self.SQL_DATABASE, self.SQL_USER, self.SQL_PASS)
        user_dict_req = {}
        songs_dict = {}
        for req in requests:
            song = db.get_sound_by_id(req["id"], type="SONG")
            total_playtime += song["length"]
            if req["requested_by"] not in user_dict_req:
                user_dict_req[req["requested_by"]] = 1
            else:
                user_dict_req[req["requested_by"]] += 1
            print(song)
            if song["name"] not in songs_dict:
                songs_dict[song["name"]] = 1
            else:
                songs_dict[song["name"]] += 1
        sorted_req_keys = sorted(user_dict_req, key=user_dict_req.get, reverse=True)
        sorted_song_keys = sorted(songs_dict, key=songs_dict.get, reverse=True)[:10] # only get the first 10

        embed=discord.Embed(title="KiwiBot Stats")
        embed.add_field(name="Number of songs", value=num_songs, inline=False)
        embed.add_field(name="Number of requests", value=num_request, inline=False)
        embed.add_field(name="Total storage", value=str(size * 1e-6) + " MB", inline=False)
        embed.add_field(name="Total length of songs", value=str(length / 3600) + " hours", inline=False)
        embed.add_field(name="Total playtime", value=str(total_playtime / 3600) + " hours", inline=False)
        embed.add_field(name="User that added the most songs", value="\n".join([f"{key} | {user_dict_add[key]}" for key in sorted_add_keys]), inline=False)
        embed.add_field(name="User that requested the most songs", value="\n".join([f"{key} | {user_dict_req[key]}" for key in sorted_req_keys]), inline=False)
        embed.add_field(name="Most played songs", value="\n".join([f"{key} | {songs_dict[key]}" for key in sorted_song_keys]), inline=False)
        await ctx.reply(embed=embed)