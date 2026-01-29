# main.py
import sys
import os
import re
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk 
import pygame
from PIL import Image, ImageTk
import math
import splash
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

        self.title("Music")
        self.geometry(f"{config.START_WIDTH}x{config.START_HEIGHT}")
        self.resizable(True, True)
        self.minsize(360, 600)
        self.configure(fg_color="#000000")

        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.on_drop)

        try: pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        except: pass

        icon_path = self.resource_path("app_icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

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
        
        # 歌词Canvas - 用于滚动歌词显示
        self.lyric_items = []
        self.lyric_scroll_offset = 0      # 当前滚动位置 (像素)
        self.target_scroll_offset = 0     # 目标滚动位置 (像素)
        

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

        # 启动动画循环
        self.animate_lyrics() 
        
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


    def resource_path(self, relative_path):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)

    def update_layout(self):
        w = self.winfo_width(); h = self.winfo_height()
        if w < 100: w = config.START_WIDTH; h = config.START_HEIGHT
        cx = w / 2
        
        # 1. 封面
        cover_y = h * 0.26
        self.canvas.coords(self.id_cover, cx, cover_y)
        
        # 2. 信息
        info_start_y = h * 0.49
        self.canvas.coords(self.id_title, cx, info_start_y)
        self.canvas.coords(self.id_artist, cx, info_start_y + 30)

        # 3. 歌词区域（直接在主Canvas上，调用绘制）
        self.draw_lyrics_on_canvas()
        
        # 4. 进度条
        prog_y = h * 0.73
        margin_x = 40
        self.prog_x_start = margin_x
        self.prog_x_end = w - margin_x
        self.prog_width = self.prog_x_end - self.prog_x_start
        
        self.canvas.coords(self.id_prog_bg, self.prog_x_start, prog_y, self.prog_x_end, prog_y)
        self.canvas.coords(self.id_prog_fg, self.prog_x_start, prog_y, self.prog_x_start, prog_y)
        self.canvas.coords(self.id_prog_hitbox, self.prog_x_start, prog_y, self.prog_x_end, prog_y)
        
        # 5. 时间
        time_y = prog_y + 20
        self.canvas.coords(self.id_time_curr, self.prog_x_start, time_y)
        self.canvas.coords(self.id_time_total, self.prog_x_end, time_y)
        
        # 6. 按钮
        btn_y = h * 0.82
        btn_spacing = 90
        self.canvas.coords(self.btn_objects["prev"]["id"], cx - btn_spacing, btn_y)
        self.canvas.coords(self.btn_objects["play"]["id"], cx, btn_y)
        self.canvas.coords(self.btn_objects["next"]["id"], cx + btn_spacing, btn_y)
        
        import_y = h - 35
        self.canvas.coords(self.btn_objects["import"]["id"], cx, import_y)

    def update_visuals(self, new_cover):
        if new_cover is None:
            new_cover = self.original_cover
        else:
            self.original_cover = new_cover

        w = self.winfo_width(); h = self.winfo_height()
        if w < 100: w = config.START_WIDTH; h = config.START_HEIGHT

        # 背景
        bg_img = utils.process_background(new_cover, w, h)
        self.tk_bg_ref = ImageTk.PhotoImage(bg_img)
        self.canvas.itemconfig(self.id_bg, image=self.tk_bg_ref)

        # 封面
        max_size = int(w * config.WIDTH_RATIO)
        max_h = int(h * config.ALBUM_HEIGHT_RATIO)
        size = min(max_size, max_h)
        cover_resized = new_cover.resize((size, size), Image.Resampling.LANCZOS)
        self.tk_cover_ref = ImageTk.PhotoImage(cover_resized)
        self.canvas.itemconfig(self.id_cover, image=self.tk_cover_ref)

        self.update_layout()

    def draw_lyrics_on_canvas(self):
        """在主Canvas上绘制歌词（Apple Music风格）"""
        # 清除旧的歌词对象
        for item_id in self.lyric_items:
            self.canvas.delete(item_id)
        self.lyric_items = []

        w = self.winfo_width(); h = self.winfo_height()
        if w < 100: w = config.START_WIDTH; h = config.START_HEIGHT
        cx = w / 2

        if not self.time_points:
            # 无歌词时显示音符
            lrc_y = h * 0.60
            item_id = self.canvas.create_text(
                cx, lrc_y, text="♪",
                font=(utils.REAL_FONT_NAME, 20),
                fill="#888888", anchor="center"
            )
            self.lyric_items.append(item_id)
            return

        # 歌词区域的中心Y坐标
        lrc_center_y = h * 0.63

        # 显示5行以实现平滑过渡：上上行、上一行、当前行、下一行、下下行
        for offset in [-2, -1, 0, 1, 2]:
            idx = self.active_lyric_index + offset
            if 0 <= idx < len(self.time_points):
                t = self.time_points[idx]
                text = self.lyrics_map[t]

                # Y坐标 = 中心 + 相对偏移 + 滚动动画偏移
                y_pos = lrc_center_y + (offset * config.LYRIC_LINE_HEIGHT) + self.lyric_scroll_offset

                # 只绘制中间可见的区域（动态调整，在滚动时扩大下方范围）
                visible_range = config.LYRIC_LINE_HEIGHT * 1.38
                if lrc_center_y - visible_range < y_pos < lrc_center_y + visible_range:
                    is_active = (idx == self.active_lyric_index)
                    color = "white" if is_active else "#888888"
                    size = config.LYRIC_FONT_SIZE if is_active else config.LYRIC_FONT_SIZE_SUB
                    weight = "bold" if is_active else "normal"

                    item_id = self.canvas.create_text(
                        cx, y_pos, text=text,
                        font=(utils.REAL_FONT_NAME, size, weight),
                        fill=color, anchor="center", width=w-80
                    )
                    self.lyric_items.append(item_id)



    def animate_lyrics(self):
        """每一帧平滑更新滚动位置"""
        # 计算当前位置与目标位置的差距
        diff = self.target_scroll_offset - self.lyric_scroll_offset
        
        # 如果差距大于 0.5 像素，则继续滑动
        if abs(diff) > 0.5:
            self.lyric_scroll_offset += diff * config.LYRIC_SMOOTHING
            self.draw_lyrics_on_canvas()
        
        # 保持 60FPS 循环
        self.after(config.LYRIC_REFRESH_RATE, self.animate_lyrics)

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
        
        # 重置滚动位置
        self.lyric_scroll_offset = 0
        self.target_scroll_offset = 0
        self.draw_lyrics_on_canvas()

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
                
                # 更新歌词
                if self.time_points:
                    new_idx = -1
                    for i, t in enumerate(self.time_points):
                        if t <= curr: new_idx = i
                        else: break
                    
                    if new_idx != -1 and new_idx != self.active_lyric_index:
                        self.active_lyric_index = new_idx
                        # 核心：更新目标滚动位置 = 当前索引 * 行高
                        self.lyric_scroll_offset = config.LYRIC_LINE_HEIGHT
                        self.target_scroll_offset = 0

                if not pygame.mixer.music.get_busy() and (self.total_duration - curr) < 1:
                    self.next_song()
            except: pass
        self.after(500, self.monitor)

if __name__ == "__main__":
    # 显示开屏页面
    splash_screen = splash.SplashScreen()
    splash_screen.show()
    
    # 启动主应用
    app = MusicPlayer()
    app.mainloop()


