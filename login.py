from pytube import YouTube
import pytube
yt = YouTube(r"https://youtu.be/ncFJSYzSy-w", use_oauth=True, allow_oauth_cache=True) 
video = yt.streams.get_audio_only()
video_id = pytube.extract.video_id(r"https://youtu.be/ncFJSYzSy-w")
mp4_name = f"{video_id}.mp4"
video.download("./", mp4_name)