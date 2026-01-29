# assets.py
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageTk

def get_icon(name, size):
    """
    使用 PIL 动态绘制高清抗锯齿图标
    """
    factor = 4
    actual_size = size * factor
    # 背景完全透明
    img = Image.new("RGBA", (actual_size, actual_size), (0, 0, 0, 0))
    
    draw = ImageDraw.Draw(img)
    cx, cy = actual_size / 2, actual_size / 2
    
    if name == "play":
        # 纯白三角形 (Play)
        # 尺寸比例：高是画布的 60%
        tri_h = actual_size * 0.6 
        tri_w = tri_h * 0.866
        # 视觉修正：三角形重心偏左，稍微向右移一点点
        offset_x = tri_w * 0.1 
        
        draw.polygon([
            (cx - tri_w/2 + offset_x, cy - tri_h/2),
            (cx - tri_w/2 + offset_x, cy + tri_h/2),
            (cx + tri_w/2 + offset_x, cy)
        ], fill="white") # 🟢 改为白色
        
    elif name == "pause":
        # 纯白竖条 (Pause)
        bar_w = actual_size * 0.12 # 稍微加粗
        bar_h = actual_size * 0.55 # 高度适中
        gap = actual_size * 0.1    # 间距
        
        draw.rectangle((cx - gap - bar_w, cy - bar_h/2, cx - gap, cy + bar_h/2), fill="white") # 🟢 改为白色
        draw.rectangle((cx + gap, cy - bar_h/2, cx + gap + bar_w, cy + bar_h/2), fill="white") # 🟢 改为白色

    elif name == "prev":
        # 倒三角
        tri_w = actual_size * 0.5
        tri_h = actual_size * 0.5
        draw.polygon([
            (cx + tri_w/2, cy - tri_h/2),
            (cx + tri_w/2, cy + tri_h/2),
            (cx - tri_w/2, cy)
        ], fill="white")
        # 竖线
        line_w = actual_size * 0.08
        draw.rectangle((cx - tri_w/2 - line_w - (actual_size*0.02), cy - tri_h/2, cx - tri_w/2 - (actual_size*0.02), cy + tri_h/2), fill="white")

    elif name == "next":
        # 三角
        tri_w = actual_size * 0.5
        tri_h = actual_size * 0.5
        draw.polygon([
            (cx - tri_w/2, cy - tri_h/2),
            (cx - tri_w/2, cy + tri_h/2),
            (cx + tri_w/2, cy)
        ], fill="white")
        # 竖线
        line_w = actual_size * 0.08
        draw.rectangle((cx + tri_w/2 + (actual_size*0.02), cy - tri_h/2, cx + tri_w/2 + line_w + (actual_size*0.02), cy + tri_h/2), fill="white")
    elif name == "import":
        # 线条稍微调细一点 (4倍因子)，防止糊成一团
        stroke = int(2 * factor)
        
        # 1. 绘制底部的“托盘” (U字型)
        # 左右边距 20%，底部边距 25%
        u_left = actual_size * 0.2
        u_right = actual_size * 0.8
        u_top = actual_size * 0.45
        u_bottom = actual_size * 0.75
        
        # 画三条线组成 U (左竖 -> 底横 -> 右竖)
        draw.line([
            (u_left, u_top), 
            (u_left, u_bottom), 
            (u_right, u_bottom), 
            (u_right, u_top)
        ], fill="white", width=stroke, joint="curve")
        
        # 2. 绘制向下箭头
        arrow_top = actual_size * 0.2
        arrow_tip = actual_size * 0.6 # 箭头尖端深入托盘一点点
        
        # 竖杆
        draw.line((cx, arrow_top, cx, arrow_tip), fill="white", width=stroke)
        
        # 箭头头部 (V字)
        wing_size = actual_size * 0.15
        # 左翼
        draw.line((cx, arrow_tip, cx - wing_size, arrow_tip - wing_size), fill="white", width=stroke)
        # 右翼
        draw.line((cx, arrow_tip, cx + wing_size, arrow_tip - wing_size), fill="white", width=stroke)


    # 统一高质量缩放
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    return img

def get_icon_tk(name, size):
    """返回 ImageTk 对象"""
    return ImageTk.PhotoImage(get_icon(name, size))
