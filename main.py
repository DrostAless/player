# main.py
import sys
import os
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk 
import pygame
from PIL import Image, ImageTk
import math

import config
import utils
import metadata
import assets 

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
except ImportError:
    root = tk.Tk(); root.withdraw()
    messagebox.showerror("Error", "pip install tkinterdnd2")
    sys.exit(1)

# 字体配置
BASE_SIZE_MAIN = 24
BASE_SIZE_SUB = 14
BASE_SIZE_BTN_BIG = 55 
BASE_SIZE_BTN_SMALL = 30
BASE_SIZE_IMPORT = 12

class MusicPlayer(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)

        self.title("Music Pro")
        self.geometry(f"{config.START_WIDTH}x{config.START_HEIGHT}")
        self.resizable(True, True)
        self.minsize(360, 600)
        self.configure(fg_color="#000000")

        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.on_drop)

        try: pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        except: pass

        # State
        self.playlist = []
        self.current_index = 0
        self.is_playing = False
        self.is_dragging = False
        self.total_duration = 1 
        self.seek_offset = 0
        self.original_cover = metadata.get_default_cover()
        self.tiny_cover = self.original_cover.resize((50, 50)) 
        self.lyrics_map = {}
        self.time_points = []
        self.active_lyric_index = -1
        self.resize_timer = None
        self.tk_bg_ref = None
        self.tk_cover_ref = None

        self.refs = {
            "bg": None, "cover": None, 
            "btn_play": None, "btn_pause": None,
            "btn_prev": None, "btn_next": None, "btn_import": None
        }

        # Canvas
        self.canvas = tk.Canvas(self, bg="#000000", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.btn_objects = {} 
        self.prog_x_start = 0
        self.prog_x_end = 0
        self.prog_width = 1

        self.id_bg = self.canvas.create_image(0, 0, anchor="nw")
        self.id_cover = self.canvas.create_image(0, 0, anchor="center")
        
        # 文本
        f_main = (utils.REAL_FONT_NAME, BASE_SIZE_MAIN, "bold")
        f_sub = (utils.REAL_FONT_NAME, BASE_SIZE_SUB)
        self.id_title = self.canvas.create_text(0, 0, text="Ready", font=f_main, fill="white", anchor="center")
        self.id_artist = self.canvas.create_text(0, 0, text="Drag & Drop music", font=f_sub, fill="#DDDDDD", anchor="center")
        
        # 歌词
        f_lrc_m = (utils.REAL_FONT_NAME, 15, "bold")
        f_lrc_s = (utils.REAL_FONT_NAME, 12)
        self.id_lrc_prev = self.canvas.create_text(0, 0, text="", font=f_lrc_s, fill="#888888", anchor="center")
        self.id_lrc_curr = self.canvas.create_text(0, 0, text="♪", font=f_lrc_m, fill="#DDDDDD", anchor="center")
        self.id_lrc_next = self.canvas.create_text(0, 0, text="", font=f_lrc_s, fill="#888888", anchor="center")
        
        # 时间
        f_time = (utils.REAL_FONT_NAME, 11)
        self.id_time_curr = self.canvas.create_text(0, 0, text="0:00", font=f_time, fill="#DDDDDD", anchor="w")
        self.id_time_total = self.canvas.create_text(0, 0, text="-0:00", font=f_time, fill="#DDDDDD", anchor="e")
        
        # 进度条
        self.id_prog_bg = self.canvas.create_line(0, 0, 0, 0, fill="#555555", width=4, capstyle="round")
        self.id_prog_fg = self.canvas.create_line(0, 0, 0, 0, fill="white", width=4, capstyle="round")
        self.id_prog_hitbox = self.canvas.create_line(0, 0, 0, 0, fill="", width=20) 

        self.load_icon_assets()

        self.create_img_btn("prev", self.refs["btn_prev"], self.prev_song)
        self.create_img_btn("play", self.refs["btn_play"], self.toggle_play) 
        self.create_img_btn("next", self.refs["btn_next"], self.next_song)
        self.create_img_btn("import", self.refs["btn_import"], self.load_files)

        self.canvas.tag_bind(self.id_prog_hitbox, "<Button-1>", self.on_prog_click)
        self.canvas.tag_bind(self.id_prog_hitbox, "<B1-Motion>", self.on_prog_drag)
        self.canvas.tag_bind(self.id_prog_hitbox, "<ButtonRelease-1>", self.on_prog_release)
        self.canvas.tag_bind(self.id_prog_hitbox, "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
        self.canvas.tag_bind(self.id_prog_hitbox, "<Leave>", lambda e: self.canvas.config(cursor=""))

        self.bind("<Configure>", self.on_resize)
        
        self.update_visuals(self.original_cover)
        self.monitor()

    def load_icon_assets(self):
        self.refs["btn_play"] = assets.get_icon_tk("play", 55)
        self.refs["btn_pause"] = assets.get_icon_tk("pause", 55)
        self.refs["btn_prev"] = assets.get_icon_tk("prev", 35)
        self.refs["btn_next"] = assets.get_icon_tk("next", 35)
        self.refs["btn_import"] = assets.get_icon_tk("import", 30)

    def create_img_btn(self, name, tk_img, cmd):
        item_id = self.canvas.create_image(0, 0, image=tk_img, anchor="center")
        self.btn_objects[name] = {"id": item_id, "cmd": cmd}
        self.canvas.tag_bind(item_id, "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
        self.canvas.tag_bind(item_id, "<Leave>", lambda e: self.canvas.config(cursor=""))
        self.canvas.tag_bind(item_id, "<Button-1>", lambda e, n=name: self.on_btn_press(n))
        self.canvas.tag_bind(item_id, "<ButtonRelease-1>", lambda e, n=name: self.on_btn_release(n))

    def on_btn_press(self, name):
        self.canvas.move(self.btn_objects[name]["id"], 0, 1)

    def on_btn_release(self, name):
        self.canvas.move(self.btn_objects[name]["id"], 0, -1)
        if self.btn_objects[name]["cmd"]:
            self.btn_objects[name]["cmd"]()

    # --- 🟢 布局更新 (Layout Tweaks) ---
    def update_layout(self):
        w = self.winfo_width(); h = self.winfo_height()
        if w < 100: w = config.START_WIDTH; h = config.START_HEIGHT
        cx = w / 2
        
        # 1. 封面 (保持不动)
        cover_y = h * 0.26
        self.canvas.coords(self.id_cover, cx, cover_y)
        
        # 2. 信息 (保持不动)
        info_start_y = h * 0.49
        self.canvas.coords(self.id_title, cx, info_start_y)
        self.canvas.coords(self.id_artist, cx, info_start_y + 30)
        
        # 3. 🟢 歌词下移 (+20px)
        # 之前是 +80，现在 +100，离歌手名远一点
        lrc_start_y = h * 0.63
        self.canvas.coords(self.id_lrc_prev, cx, lrc_start_y - 30)
        self.canvas.coords(self.id_lrc_curr, cx, lrc_start_y)
        self.canvas.coords(self.id_lrc_next, cx, lrc_start_y + 30)
        
        # 4. 🟢 进度条上移 (-20px)
        # 之前是 h-140，现在 h-160
        prog_y = h * 0.73
        margin_x = 40
        self.prog_x_start = margin_x
        self.prog_x_end = w - margin_x
        self.prog_width = self.prog_x_end - self.prog_x_start
        
        self.canvas.coords(self.id_prog_bg, self.prog_x_start, prog_y, self.prog_x_end, prog_y)
        self.canvas.coords(self.id_prog_hitbox, self.prog_x_start, prog_y, self.prog_x_end, prog_y)
        
        self.canvas.coords(self.id_time_curr, margin_x, prog_y + 15)
        self.canvas.coords(self.id_time_total, w - margin_x, prog_y + 15)
        
        # 5. 🟢 按钮上移 (-20px)
        # 之前是 h-70，现在 h-90 (跟随进度条)
        btn_y = h * 0.81
        gap = 70
        self.canvas.coords(self.btn_objects["play"]["id"], cx, btn_y)
        self.canvas.coords(self.btn_objects["prev"]["id"], cx - gap, btn_y)
        self.canvas.coords(self.btn_objects["next"]["id"], cx + gap, btn_y)
        
        # Import 按钮位置微调
        self.canvas.coords(self.btn_objects["import"]["id"], cx, h - 30)

    def update_visuals(self, pil_img=None):
        w = self.winfo_width(); h = self.winfo_height()
        if w < 100: w = config.START_WIDTH; h = config.START_HEIGHT

        if pil_img:
            self.original_cover = pil_img
            self.tiny_cover = pil_img.resize((40, 40), Image.Resampling.BILINEAR)
        
        bg_img = utils.process_background(self.tiny_cover, w, h)
        self.tk_bg_ref = ImageTk.PhotoImage(bg_img) 
        self.canvas.itemconfig(self.id_bg, image=self.tk_bg_ref)
        
        target_size = int(min(w * 0.7, h * 0.4))
        cover_resized = self.original_cover.resize((target_size, target_size), Image.Resampling.BICUBIC)
        self.tk_cover_ref = ImageTk.PhotoImage(cover_resized)
        self.canvas.itemconfig(self.id_cover, image=self.tk_cover_ref)
        
        self.update_layout()

    def on_resize(self, event):
        if event.widget == self:
            if self.resize_timer: self.after_cancel(self.resize_timer)
            self.resize_timer = self.after(50, lambda: self.update_visuals(None))

    def on_prog_click(self, event):
        self.update_drag_pos(event.x)
        self.is_dragging = True
        
    def on_prog_drag(self, event):
        self.update_drag_pos(event.x)
        
    def on_prog_release(self, event):
        if self.playlist and self.total_duration > 0:
            try:
                ratio = (event.x - self.prog_x_start) / self.prog_width
                ratio = max(0, min(1, ratio))
                target = ratio * self.total_duration
                pygame.mixer.music.play(start=target)
                self.seek_offset = target
                self.is_playing = True
                self.canvas.itemconfig(self.btn_objects["play"]["id"], image=self.refs["btn_pause"])
            except: pass
        self.is_dragging = False

    def update_drag_pos(self, mouse_x):
        x = max(self.prog_x_start, min(mouse_x, self.prog_x_end))
        y = self.canvas.coords(self.id_prog_bg)[1]
        self.canvas.coords(self.id_prog_fg, self.prog_x_start, y, x, y)

    def on_drop(self, event):
        raw = event.data
        if raw.startswith('{') and raw.endswith('}'): raw = raw[1:-1]
        valid = []
        if os.path.exists(raw): valid.append(raw)
        else:
            for p in re.findall(r'\{.*?\}|\S+', raw):
                if os.path.exists(p.strip('{}')): valid.append(p.strip('{}'))
        valid = [f for f in valid if f.lower().endswith(('.mp3', '.wav', '.flac', '.m4a'))]
        if valid:
            self.playlist.extend(valid)
            if len(self.playlist) == len(valid): self.current_index = 0; self.play_index(0)

    def load_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Audio", "*.mp3 *.wav *.flac *.m4a")])
        if files:
            self.playlist.extend(list(files))
            if len(self.playlist) == len(files): self.current_index = 0; self.play_index(0)

    def play_index(self, index):
        if not self.playlist: return
        try: pygame.mixer.music.unload()
        except: pass
        self.current_index = index
        path = self.playlist[index]
        
        t, a, d, c = metadata.get_track_info(path)
        self.canvas.itemconfig(self.id_title, text=t)
        self.canvas.itemconfig(self.id_artist, text=a)
        
        self.total_duration = d
        self.seek_offset = 0
        
        self.lyrics_map, self.time_points = metadata.get_lyrics(path)
        self.active_lyric_index = -1
        self.canvas.itemconfig(self.id_lrc_prev, text="")
        self.canvas.itemconfig(self.id_lrc_curr, text="♪")
        self.canvas.itemconfig(self.id_lrc_next, text="")

        self.update_visuals(c)

        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            self.is_playing = True
            self.canvas.itemconfig(self.btn_objects["play"]["id"], image=self.refs["btn_pause"])
            self.monitor()
        except: pass

    def toggle_play(self):
        if not self.playlist: return
        if self.is_playing:
            pygame.mixer.music.pause(); self.is_playing = False; self.canvas.itemconfig(self.btn_objects["play"]["id"], image=self.refs["btn_play"])
        else:
            pygame.mixer.music.unpause(); self.is_playing = True; self.canvas.itemconfig(self.btn_objects["play"]["id"], image=self.refs["btn_pause"])

    def prev_song(self):
        if self.playlist:
            self.play_index((self.current_index - 1) % len(self.playlist))

    def next_song(self):
        if self.playlist:
            self.play_index((self.current_index + 1) % len(self.playlist))

    def monitor(self):
        if self.is_playing and not self.is_dragging:
            try:
                raw = pygame.mixer.music.get_pos()
                if raw == -1: raw = 0
                curr = (raw / 1000) + self.seek_offset
                if curr < 0: curr = 0
                if curr > self.total_duration: curr = self.total_duration
                
                if self.total_duration > 0:
                    ratio = curr / self.total_duration
                    curr_x = self.prog_x_start + (self.prog_width * ratio)
                    y = self.canvas.coords(self.id_prog_bg)[1]
                    self.canvas.coords(self.id_prog_fg, self.prog_x_start, y, curr_x, y)
                
                self.canvas.itemconfig(self.id_time_curr, text=utils.fmt_time(curr))
                rem = max(0, self.total_duration - curr)
                self.canvas.itemconfig(self.id_time_total, text=f"-{utils.fmt_time(rem)}")
                
                if self.time_points:
                    new_idx = -1
                    for i, t in enumerate(self.time_points):
                        if t <= curr: new_idx = i
                        else: break
                    if new_idx != -1 and new_idx != self.active_lyric_index:
                        self.active_lyric_index = new_idx
                        prev = self.lyrics_map[self.time_points[new_idx-1]] if new_idx > 0 else ""
                        curr_txt = self.lyrics_map[self.time_points[new_idx]]
                        next_txt = self.lyrics_map[self.time_points[new_idx+1]] if new_idx + 1 < len(self.time_points) else ""
                        
                        self.canvas.itemconfig(self.id_lrc_prev, text=prev)
                        self.canvas.itemconfig(self.id_lrc_curr, text=curr_txt)
                        self.canvas.itemconfig(self.id_lrc_next, text=next_txt)

                if not pygame.mixer.music.get_busy() and (self.total_duration - curr) < 1:
                    self.next_song()
            except: pass
        self.after(500, self.monitor)

if __name__ == "__main__":
    app = MusicPlayer()
    app.mainloop()
