"""Original, code-drawn office robots; no downloaded brand artwork."""
import tkinter as tk

NAMES = ['Mint', 'Sunny', 'Lilac', 'Sky', 'Rose', 'Lime', 'Peach', 'Slate', 'Pearl']
COLORS = ['#8dc9b1', '#e6bd69', '#b7a1d9', '#87bbd7', '#d5a0b7',
          '#abc77d', '#dfaa83', '#8e9cba', '#c9d7d1']


def robot_frame(index, row, frame, sub):
    image = tk.PhotoImage(width=24, height=26)
    color = COLORS[index % len(COLORS)]
    outline = '#354b59'
    bob = frame % 2 if row in (1, 2, 3) else 0
    def box(x, y, w, h, fill):
        image.put(fill, to=(x, y + bob, x + w, y + bob + h))
    box(11, 1, 2, 4, outline)
    box(10, 1, 4, 2, color)
    box(4, 5, 16, 11, outline)
    box(3, 7, 18, 7, outline)
    box(5, 6, 14, 9, color)
    box(6, 8, 12, 5, '#eaf2e5')
    eye_h = 1 if row == 0 and frame == 1 else 3
    box(8, 9, 2, eye_h, outline)
    box(14, 9, 2, eye_h, outline)
    box(7, 16, 10, 6, outline)
    box(8, 16, 8, 5, color)
    box(11, 17, 2, 2, '#f6e7ad')
    box(4, 17, 2, 4, color)
    box(18, 16 if row == 7 and frame % 2 else 17, 2, 4, color)
    box(7, 22, 4, 2 if frame % 2 else 3, outline)
    box(13, 22, 4, 3 if frame % 2 else 2, outline)
    if index % 3 == 1:
        box(3, 7, 2, 8, '#776b91')
        box(19, 7, 2, 8, '#776b91')
    elif index % 3 == 2:
        box(5, 5, 14, 2, '#f0d58a')
    return image.zoom(2 if sub else 3)
