import os
import ctypes
import tkinter as tk
from tkinter import font
from PIL import Image, ImageFilter, ImageEnhance

def load_font_and_get_name():
    return "Microsoft YaHei UI"

REAL_FONT_NAME = load_font_and_get_name()

def fmt_time(sec):
    return f"{int(sec//60)}:{int(sec%60):02}"

def process_background(pil_img, win_w, win_h):
    """生成全屏模糊背景图"""
    img_ratio = pil_img.width / pil_img.height
    win_ratio = win_w / win_h
    
    if img_ratio > win_ratio:
        new_h = win_h
        new_w = int(new_h * img_ratio)
    else:
        new_w = win_w
        new_h = int(new_w / img_ratio)
        
    bg_resized = pil_img.resize((new_w, new_h), Image.Resampling.BICUBIC)
    
    left = (new_w - win_w) / 2
    top = (new_h - win_h) / 2
    right = (new_w + win_w) / 2
    bottom = (new_h + win_h) / 2
    
    bg_cropped = bg_resized.crop((left, top, right, bottom))
    
    bg_blur = bg_cropped.filter(ImageFilter.GaussianBlur(radius=80))
    
    enhancer = ImageEnhance.Brightness(bg_blur)
    bg_final = enhancer.enhance(0.4)
    
    return bg_final
