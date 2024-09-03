import pyodbc
import requests
import os
import math
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
import random

class RequestDatabase:
    def __init__(self, server, database, username, password):
        self.conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
    
    def add_request(self, id, requested_by, date_requested):
        cursor = self.conn.execute(
            "INSERT INTO requests (id, requested_by, date_requested) VALUES (?, ?, ?)",
            id, requested_by, date_requested
        )
        self.conn.commit()

    def get_all_request(self):
        cursor = self.conn.execute(
            "SELECT id, requested_by, date_requested FROM requests"
        )
        rows = cursor.fetchall()
        rs = []
        for row in rows:
            r = {
                'id': row[0],
                'requested_by': row[1],
                'date_requested': row[2],
            }
            rs.append(r)
        return rs


class SoundsDatabase:
    def __init__(self, server, database, username, password):
        self.conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)

    def download_sound_file(self, name, url, save_path):
        response = requests.get(url)
        mp3_path = os.path.join(save_path, name)
        with open(mp3_path, "wb") as f:
            f.write(response.content)
        length, size = self.get_mp3_size_and_length(mp3_path)
        return mp3_path, length, size
        
    def get_mp3_size_and_length(self, mp3_path):
        audio = MP3(mp3_path)
        return audio.info.length, os.path.getsize(mp3_path)
    
    def get_mp4_size_and_length(self, mp4_path):
        audio = MP4(mp4_path)
        return audio.info.length, os.path.getsize(mp4_path)

    def add_sound(self, name, emoji, date_added, mp3_path, added_by, type, size, length, volume=1):
        self.conn.execute('''
            INSERT INTO sounds (name, emoji, date_added, mp3, added_by, type, size, length, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, emoji, date_added, mp3_path, added_by, type, size, length, volume))
        self.conn.commit()

    def delete_sound(self, id):
        self.conn.execute('''
            UPDATE sounds SET is_deleted = 1 WHERE [id] = ?
        ''', (id))
        self.conn.commit()

    def undelete_sound(self, id):
        self.conn.execute('''
            UPDATE sounds SET is_deleted = 0 WHERE [id] = ?
        ''', (id))
        self.conn.commit()

    def get_sound_by_name(self, name, type):
        cursor = self.conn.execute('SELECT * FROM sounds WHERE LOWER([name]) = LOWER(?) AND [type] = ?  AND is_deleted = 0', (name,type))
        row = cursor.fetchone()
        if row is None:
            return None
        return {
            'id': row[1],
            'name': row[0],
            'emoji': row[2],
            'date_added': row[3],
            'mp3': row[4],
            'added_by': row[5],
            'type': row[6],
            'size': row[7],
            'length': row[8],
            'volume': row[9]
        }
    
    def get_sound_by_id(self, id, type):
        cursor = self.conn.execute('SELECT * FROM sounds WHERE id = ? AND [type] = ?  AND is_deleted = 0', (id,type))
        row = cursor.fetchone()
        if row is None:
            return None
        return {
            'id': row[1],
            'name': row[0],
            'emoji': row[2],
            'date_added': row[3],
            'mp3': row[4],
            'added_by': row[5],
            'type': row[6],
            'size': row[7],
            'length': row[8],
            'volume': row[9]
        }
    
    def search_sound_by_name(self, name, type):
        name = f'%{name}%' # wildcard!
        cursor = self.conn.execute("SELECT * FROM sounds WHERE LOWER([name]) LIKE LOWER(?) AND [type] = ? AND is_deleted = 0", (name,type))
        rows = cursor.fetchall()
        sounds = []
        for row in rows:
            sound = {
                'id': row[1],
                'name': row[0],
                'emoji': row[2],
                'date_added': row[3],
                'mp3': row[4],
                'added_by': row[5],
                'type': row[6],
                'size': row[7],
                'length': row[8],
                'volume': row[9]
            }
            sounds.append(sound)
        return sounds
    
    def search_deleted_sound_by_name(self, name, type):
        name = f'%{name}%' # wildcard!
        cursor = self.conn.execute("SELECT * FROM sounds WHERE LOWER([name]) LIKE LOWER(?) AND [type] = ? AND is_deleted = 1", (name,type))
        rows = cursor.fetchall()
        sounds = []
        for row in rows:
            sound = {
                'id': row[1],
                'name': row[0],
                'emoji': row[2],
                'date_added': row[3],
                'mp3': row[4],
                'added_by': row[5],
                'type': row[6],
                'size': row[7],
                'length': row[8],
                'volume': row[9]
            }
            sounds.append(sound)
        return sounds

    def get_all_sounds(self, type, page_number = None):
        
        if page_number is not None:
            cursor = self.conn.execute("SELECT COUNT(*) FROM sounds")
            total_rows = cursor.fetchone()[0]
            total_pages = math.ceil(total_rows / 20)

            offset = (page_number-1)*20
            cursor = self.conn.execute('SELECT * FROM sounds WHERE [type] = ? AND is_deleted = 0 ORDER BY id OFFSET ? ROWS FETCH NEXT ? ROWS ONLY', (type, offset, 20))
        else:
            cursor = self.conn.execute('SELECT * FROM sounds WHERE [type] = ? AND is_deleted = 0', (type))
        rows = cursor.fetchall()
        sounds = []
        for row in rows:
            sound = {
                'id': row[1],
                'name': row[0],
                'emoji': row[2],
                'date_added': row[3],
                'mp3': row[4],
                'added_by': row[5],
                'type': row[6],
                'size': row[7],
                'length': row[8],
                'volume': row[9]
            }
            sounds.append(sound)
        if page_number is not None:
            return sounds, total_pages
        return sounds

    def update_sound(self, sound_id, name=None, emoji=None, date_added=None, mp3_path=None, added_by=None, type=None, size=None, length=None, volume=None):
        update_query = 'UPDATE sounds SET'
        update_values = []
        if name is not None:
            update_query += ' name = ?,'
            update_values.append(name)
        if emoji is not None:
            update_query += ' emoji = ?,'
            update_values.append(emoji)
        if date_added is not None:
            update_query += ' date_added = ?,'
            update_values.append(date_added)
        if mp3_path is not None:
            update_query += ' mp3 = ?,'
            update_values.append(mp3_path)
        if added_by is not None:
            update_query += ' added_by = ?,'
            update_values.append(added_by)
        if type is not None:
            update_query += ' type = ?,'
            update_values.append(type)
        if size is not None:
            update_query += ' size = ?,'
            update_values.append(size)
        if length is not None:
            update_query += ' length = ?,'
            update_values.append(length)
        if volume is not None:
            update_query += ' volume = ?,'
            update_values.append(volume)
        # Remove the trailing comma
        update_query = update_query[:-1]
        update_query += ' WHERE id = ?'
        update_values.append(sound_id)
        self.conn.execute(update_query, update_values)
        self.conn.commit()

    def get_random_sound(self, type):
        cursor = self.conn.execute('SELECT COUNT(*) FROM sounds WHERE [type] = ? AND is_deleted = 0', (type,))
        total_rows = cursor.fetchone()[0]
        
        if total_rows == 0:
            return None
        
        random_offset = random.randint(0, total_rows - 1)
        cursor = self.conn.execute('SELECT * FROM sounds WHERE [type] = ? AND is_deleted = 0 ORDER BY NEWID() OFFSET ? ROWS FETCH NEXT 1 ROWS ONLY', (type, random_offset))
        row = cursor.fetchone()
        
        sound = {
            'id': row[1],
            'name': row[0],
            'emoji': row[2],
            'date_added': row[3],
            'mp3': row[4],
            'added_by': row[5],
            'type': row[6],
            'size': row[7],
            'length': row[8],
            'volume': row[9]
        }
        
        return sound