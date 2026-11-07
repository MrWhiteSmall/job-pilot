"""Capture the dedicated Chrome window natively (PrintWindow) so we can see the real page."""
import ctypes
import ctypes.wintypes as wt
from pathlib import Path

OUT = Path(r'D:\DesktopCode\job-pilot\data\screenshots\chrome-status.png')

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
user32.SetProcessDPIAware()


class RECT(ctypes.Structure):
    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long),
                ('right', ctypes.c_long), ('bottom', ctypes.c_long)]


def find_window():
    handles = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        length = user32.GetWindowTextLengthW(hwnd)
        if length and user32.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value
            if 'BOSS' in title or 'zhipin' in title.lower() or '杭州招聘' in title:
                handles.append((hwnd, title))
        return True

    user32.EnumWindows(cb, 0)
    return handles


targets = find_window()
print('windows', targets)
if not targets:
    raise SystemExit('no BOSS window')
hwnd, title = targets[0]
rect = RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
width, height = rect.right - rect.left, rect.bottom - rect.top
print('size', width, height, title)
hdc = user32.GetWindowDC(hwnd)
memdc = gdi32.CreateCompatibleDC(hdc)
bitmap = gdi32.CreateCompatibleBitmap(hdc, width, height)
gdi32.SelectObject(memdc, bitmap)
user32.PrintWindow(hwnd, memdc, 2)

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [('biSize', wt.DWORD), ('biWidth', ctypes.c_long), ('biHeight', ctypes.c_long),
                ('biPlanes', wt.WORD), ('biBitCount', wt.WORD), ('biCompression', wt.DWORD),
                ('biSizeImage', wt.DWORD), ('biXPelsPerMeter', ctypes.c_long),
                ('biYPelsPerMeter', ctypes.c_long), ('biClrUsed', wt.DWORD), ('biClrImportant', wt.DWORD)]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [('bmiHeader', BITMAPINFOHEADER), ('bmiColors', wt.DWORD * 3)]


bmi = BITMAPINFO()
bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
bmi.bmiHeader.biWidth = width
bmi.bmiHeader.biHeight = -height
bmi.bmiHeader.biPlanes = 1
bmi.bmiHeader.biBitCount = 32
bmi.bmiHeader.biCompression = 0
buf = ctypes.create_string_buffer(width * height * 4)
gdi32.GetDIBits(memdc, bitmap, 0, height, buf, ctypes.byref(bmi), 0)

import struct
import zlib


def png(raw, w, h):
    rows = b''.join(b'\x00' + raw[y * w * 4:(y + 1) * w * 4].translate(bytes.maketrans(b'0123', b'3210')) for y in range(h))
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b''))


OUT.write_bytes(png(buf.raw, width, height))
print('saved', OUT)
