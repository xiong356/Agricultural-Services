"""
生成小程序底部 TabBar 图标（81x81 PNG）
normal: #9C9688（灰色）
selected: #7A8471（鼠尾草绿）
"""
import struct, zlib, os

DIR = r'D:\workbudy\农服平台\miniprogram\assets\icons'
os.makedirs(DIR, exist_ok=True)

def create_png(width, height, pixels):
    """pixels: list of (r, g, b, a) per row"""
    def chunk(ctype, data):
        c = ctype + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)

    raw = b''
    for y in range(height):
        raw += b'\x00'  # filter none
        for x in range(width):
            r, g, b, a = pixels[y * width + x]
            raw += struct.pack('BBBB', r, g, b, a)

    ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    header = b'\x89PNG\r\n\x1a\n'
    return header + chunk(b'IHDR', ihdr) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')

def icon_canvas(size=81):
    """返回 (size*size) 个透明像素列表"""
    return [(0, 0, 0, 0)] * (size * size)

def draw_rect(pixels, size, x, y, w, h, color):
    for dy in range(h):
        for dx in range(w):
            px, py = x + dx, y + dy
            if 0 <= px < size and 0 <= py < size:
                pixels[py * size + dx + x] = color

def draw_circle(pixels, size, cx, cy, r, color):
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r:
                px, py = cx + dx, cy + dy
                if 0 <= px < size and 0 <= py < size:
                    pixels[py * size + px] = color

def draw_line_h(pixels, size, x1, x2, y, thickness, color):
    for t in range(thickness):
        draw_rect(pixels, size, x1, y + t, x2 - x1, 1, color)

def draw_line_v(pixels, size, x, y1, y2, thickness, color):
    for t in range(thickness):
        draw_rect(pixels, size, x + t, y1, 1, y2 - y1, color)

# === 图标绘制函数 ===

def home_icon(color):
    """房屋: 三角形屋顶 + 矩形屋身 + 小门"""
    s = 81
    p = icon_canvas(s)
    c = color
    # roof triangle
    for y in range(10, 32):
        w = int((y - 10) * 1.8)
        x1 = 40 - w
        x2 = 40 + w
        for x in range(x1, x2 + 1):
            if 0 <= x < s:
                p[y * s + x] = c
    # body
    draw_rect(p, s, 16, 32, 49, 32, c)
    # door
    draw_rect(p, s, 34, 46, 14, 18, (0, 0, 0, 0))
    draw_rect(p, s, 34, 46, 14, 18, (0xc0, 0xc0, 0xc0, 0x40))
    return p

def disease_icon(color):
    """放大镜: 圆形 + 斜线手柄"""
    s = 81
    p = icon_canvas(s)
    c = color
    # lens circle (ring)
    draw_circle(p, s, 30, 30, 14, c)
    draw_circle(p, s, 30, 30, 10, (0, 0, 0, 0))
    # handle
    for t in range(5):
        for d in range(18):
            y = 44 + d
            x = 42 + int(d * 0.7) + t
            if 0 <= x < s and 0 <= y < s:
                p[y * s + x] = c
    return p

def alert_icon(color):
    """铃铛: 半圆 + 矩形 + 小球"""
    s = 81
    p = icon_canvas(s)
    c = color
    # bell top arc
    for y in range(15, 35):
        r = 14
        dy = y - 28
        if abs(dy) < r:
            hw = int((r * r - dy * dy) ** 0.5)
            x1, x2 = 40 - hw, 40 + hw
            for x in range(x1, x2 + 1):
                if 0 <= x < s:
                    p[y * s + x] = c
    # bell bottom
    draw_rect(p, s, 26, 32, 28, 8, c)
    # bell rim
    draw_rect(p, s, 23, 40, 34, 5, c)
    draw_rect(p, s, 26, 41, 28, 3, (0, 0, 0, 0))
    # clapper ball
    draw_circle(p, s, 40, 52, 5, c)
    return p

def plot_icon(color):
    """定位标记: 圆 + 水滴 + 中心点"""
    s = 81
    p = icon_canvas(s)
    c = color
    # pin shape (circle + triangle)
    draw_circle(p, s, 40, 24, 12, c)
    draw_circle(p, s, 40, 24, 9, (0, 0, 0, 0))
    # triangle point
    for y in range(36, 60):
        hw = max(0, int((60 - y) * 0.5))
        x1, x2 = 40 - hw, 40 + hw
        for x in range(x1, x2 + 1):
            if 0 <= x < s:
                p[y * s + x] = c
    return p

def profile_icon(color):
    """人物: 圆形头 + 半椭圆身体"""
    s = 81
    p = icon_canvas(s)
    c = color
    # head
    draw_circle(p, s, 40, 22, 10, c)
    # body arc
    for y in range(34, 65):
        hw = int((y - 24) * 0.65)
        x1, x2 = 40 - hw, 40 + hw
        for x in range(x1, x2 + 1):
            if 0 <= x < s:
                p[y * s + x] = c
    return p

# === 生成图标 ===
icons = {
    'home': home_icon,
    'disease': disease_icon,
    'alerts': alert_icon,
    'plots': plot_icon,
    'profile': profile_icon,
}

GRAY = (0x9C, 0x96, 0x88, 0xFF)   # #9C9688
GREEN = (0x7A, 0x84, 0x71, 0xFF)  # #7A8471

for name, draw_fn in icons.items():
    # normal (gray)
    png = create_png(81, 81, draw_fn(GRAY))
    path = os.path.join(DIR, f'{name}_normal.png')
    with open(path, 'wb') as f:
        f.write(png)
    print(f'OK: {path} ({len(png)} bytes)')

    # selected (green)
    png = create_png(81, 81, draw_fn(GREEN))
    path = os.path.join(DIR, f'{name}_selected.png')
    with open(path, 'wb') as f:
        f.write(png)
    print(f'OK: {path} ({len(png)} bytes)')

print('\nDone! 10 icons generated.')
