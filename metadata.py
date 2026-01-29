# metadata.py
import os
import io
import re
from PIL import Image
from mutagen.mp3 import MP3, EasyMP3 
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.id3 import ID3, APIC
from mutagen import File as MutagenFile

try:
    from tinytag import TinyTag
except ImportError:
    TinyTag = None

def get_default_cover():
    return Image.new('RGB', (800, 800), color='#222222')

def get_track_info(path):
    # 默认值
    title = os.path.basename(path) # 默认用文件名
    if "." in title: title = title.rsplit(".", 1)[0] # 去掉后缀
    
    artist = "Unknown Artist"
    duration = 0
    cover = get_default_cover()

    # --- 🟢 阶段 1: 读取时长 (保持之前的修复) ---
    try:
        if path.lower().endswith('.mp3'):
            audio = MP3(path)
            duration = audio.info.length
        elif path.lower().endswith('.flac'):
            audio = FLAC(path)
            duration = audio.info.length
        elif path.lower().endswith('.m4a'):
            audio = MP4(path)
            duration = audio.info.length
        else:
            audio = MutagenFile(path)
            if audio and audio.info: duration = audio.info.length
    except: pass

    # 异常时长修正
    file_size = os.path.getsize(path)
    if duration <= 0 or (duration > 600 and file_size < 10*1024*1024):
        duration = (file_size * 8) / 128000 

    # --- 🟢 阶段 2: 增强版标签读取 (优先 Mutagen EasyID3) ---
    # 这种方式对中文支持最好，且能自动处理 ID3v1/v2
    try:
        if path.lower().endswith('.mp3'):
            # EasyMP3 封装了常用的标签读取
            tags = EasyMP3(path)
            if 'title' in tags and tags['title']: 
                title = tags['title'][0]
            if 'artist' in tags and tags['artist']: 
                artist = tags['artist'][0]
        
        elif path.lower().endswith('.flac'):
            audio = FLAC(path)
            if 'title' in audio: title = audio['title'][0]
            if 'artist' in audio: artist = audio['artist'][0]
            
        elif path.lower().endswith('.m4a'):
            audio = MP4(path)
            # m4a 的键名比较特殊
            if '\xa9nam' in audio: title = audio['\xa9nam'][0] # title
            if '\xa9ART' in audio: artist = audio['\xa9ART'][0] # artist
            
        else:
            # 如果上面都失败，尝试 TinyTag
            if TinyTag:
                t = TinyTag.get(path)
                if t.title: title = t.title
                if t.artist: artist = t.artist

    except Exception as e:
        print(f"Tag Read Error: {e}")
        # 如果读取出错，保持默认文件名

    # --- 阶段 3: 读取封面 (保持不变) ---
    try:
        f = MutagenFile(path)
        pil = None
        if f.tags and isinstance(f.tags, ID3):
            for k, v in f.tags.items():
                if k.startswith("APIC"):
                    pil = Image.open(io.BytesIO(v.data))
                    break
        elif hasattr(f, 'pictures') and f.pictures:
            pil = Image.open(io.BytesIO(f.pictures[0].data))
        elif f.tags and 'covr' in f.tags:
            pil = Image.open(io.BytesIO(f.tags['covr'][0]))
        
        if pil: cover = pil.convert("RGB")
    except: pass

    return title, artist, duration, cover

def parse_lrc_content(lrc_text):
    lyrics = {}
    times = []
    lines = lrc_text.splitlines()
    for line in lines:
        matches = re.findall(r'\[(\d+):(\d+\.?\d*)\]', line)
        text = re.sub(r'\[.*?\]', '', line).strip()
        if matches and text:
            for m in matches:
                min_v, sec_v = int(m[0]), float(m[1])
                time_key = min_v * 60 + sec_v
                lyrics[time_key] = text
                times.append(time_key)
    times.sort()
    return lyrics, times

def get_lyrics(audio_path):
    lrc_text = None
    try:
        audio = MutagenFile(audio_path)
        if audio.tags and isinstance(audio.tags, ID3):
            for key in audio.tags.keys():
                if key.startswith("USLT"):
                    lrc_text = str(audio.tags[key])
                    break
        elif hasattr(audio, 'tags') and 'LYRICS' in audio.tags:
            lrc_text = audio.tags['LYRICS'][0]
    except: pass

    if not lrc_text:
        base = os.path.splitext(audio_path)[0]
        lrc_path = base + ".lrc"
        if os.path.exists(lrc_path):
            try:
                with open(lrc_path, 'r', encoding='utf-8') as f:
                    lrc_text = f.read()
            except: pass

    if lrc_text:
        return parse_lrc_content(lrc_text)
    return {}, []
