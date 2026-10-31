"""Native pixel Clawd wardrobe and desk animations, shared by UI and previews."""
import math


# Keep the original six slots so existing sessions retain their wardrobe family.
VARIANTS = [
    ('헤드셋', '#d58c6e', '#91b7c5', '♫'),
    ('둥근 안경', '#d49c7c', '#d8bd80', '⌕'),
    ('리본', '#ce997e', '#d9a3bb', '✦'),
    ('캡', '#e2aa88', '#92bcdf', '▰'),
    ('스카프', '#bc8b78', '#bad194', '≈'),
    ('백팩', '#d99d86', '#b8ace2', '▣'),
    ('후드', '#cc927c', '#91b9a5', '⌘'),
    ('베레모', '#dfa689', '#bc9cc5', '✧'),
    ('연필', '#d59b84', '#e3bf6f', '✎'),
    ('수면모자', '#c58f7b', '#a6b1dc', '☾'),
    ('담요', '#e0aa91', '#b7c4a0', '▤'),
    ('머그잔', '#cb937d', '#dfa998', '☕'),
]


def draw_clawd(px, variant, now=0, walking=False, sleeping=False,
               state='idle', laptop=False):
    """Draw pixel rectangles through px(left, top, width, height, color)."""
    wardrobe, shade, accent, _ = VARIANTS[variant % len(VARIANTS)]
    dark = '#423c43'
    highlight = '#efbfa2'
    blink = not walking and int(now * 4) % 23 == 22
    eye_h = 1 if sleeping or blink else 2 if laptop else 3
    eye_y = 3 if sleeping or blink else 2 if laptop else 1
    # Hood/backpack sit behind the familiar crab silhouette.
    if variant == 5:
        px(7, 0, 5, 10, accent)
        px(10, 2, 2, 5, '#80709d')
    elif variant == 6:
        px(-9, -5, 18, 6, accent)
        px(-11, -2, 3, 8, accent)
        px(8, -2, 3, 8, accent)
    px(-8, -2, 16, 11, shade)
    px(-10, 0, 2, 7, shade)
    px(8, 0, 2, 7, shade)
    px(-6, -4, 12, 2, shade)
    px(-6, -3, 4, 1, highlight)
    px(-5, eye_y, 2, eye_h, dark)
    px(3, eye_y, 2, eye_h, dark)
    if state in ('needs_answer', 'needs_approval') and not sleeping:
        px(-1, 5, 2, 2, dark)
    elif state == 'done' and not sleeping:
        px(-2, 5, 1, 1, dark)
        px(-1, 6, 2, 1, dark)
        px(1, 5, 1, 1, dark)
    elif state == 'thinking' and not sleeping:
        px(-6, -1, 4, 1, dark)
        px(3, -2, 3, 1, dark)
    px(-12, 4, 3, 3, shade)
    px(9, 4, 3, 3, shade)
    for leg in (-7, -3, 2, 6):
        px(leg, 9, 2, 3 + (int(now * 8 + leg) % 2 if walking else 0), shade)
    if variant == 0:
        px(-9, -5, 18, 2, '#596879')
        px(-11, -3, 3, 8, accent)
        px(8, -3, 3, 8, accent)
        px(10, 3, 3, 1, '#596879')
    elif variant == 1:
        for left in (-7, 1):
            px(left, 0, 6, 1, dark)
            px(left, 4, 6, 1, dark)
            px(left, 1, 1, 3, dark)
            px(left + 5, 1, 1, 3, dark)
        px(-1, 2, 2, 1, dark)
    elif variant == 2:
        px(4, -6, 4, 4, accent)
        px(9, -7, 3, 5, accent)
        px(8, -5, 2, 2, '#b67995')
    elif variant == 3:
        px(-6, -7, 12, 4, accent)
        px(-8, -3, 19, 2, accent)
        px(1, -6, 2, 2, '#dce9e4')
    elif variant == 4:
        px(-8, 7, 16, 2, accent)
        px(4, 9, 3, 5, accent)
        px(4, 12, 3, 1, '#dae4bf')
    elif variant == 6:
        px(-8, 7, 16, 3, accent)
        px(-3, 7, 1, 3, '#edf0d8')
        px(3, 7, 1, 3, '#edf0d8')
    elif variant == 7:
        px(-5, -8, 11, 2, accent)
        px(-8, -6, 17, 3, accent)
        px(-6, -3, 13, 1, '#836a95')
        px(2, -10, 2, 2, '#e6c98d')
    elif variant == 8:
        px(5, -7, 2, 8, accent)
        px(5, -8, 2, 2, '#e2a3a0')
        px(5, 1, 2, 1, dark)
    elif variant == 9:
        px(-6, -6, 12, 3, accent)
        px(-3, -9, 9, 3, accent)
        px(2, -11, 6, 3, accent)
        px(7, -9, 3, 4, accent)
        px(8, -5, 3, 3, '#eee9d2')
        px(-7, -3, 15, 2, '#eee9d2')
    elif variant == 10:
        px(-9, 6, 18, 5, accent)
        px(-7, 7, 2, 4, '#dce2c4')
        px(1, 7, 2, 4, '#dce2c4')
        px(7, 7, 2, 6, accent)
    elif variant == 11 and not laptop:
        px(10, 5, 5, 5, '#f6e8cf')
        px(15, 6, 2, 3, accent)
        if not walking:
            px(11, 1 - int(now * 2) % 2, 1, 2, '#c4c9bd')
            px(14, -1 - int(now * 2) % 2, 1, 2, '#c4c9bd')
    if laptop:
        # Face stays visible above the screen; two wrists alternate typing.
        px(-11, 5, 22, 9, '#414c60')
        px(-10, 6, 20, 7, '#a6bcc7')
        px(-9, 7, 18, 5, '#263d4b')
        px(-7, 8, 4, 1, '#a0dabd')
        px(-2, 8, 7, 1, '#7faec8')
        px(-7, 10, 8, 1, '#88b7cc')
        if int(now * 3) % 2 == 0:
            px(3, 10, 1, 1, '#e8cf8d')
        px(-13, 14, 26, 2, '#708597')
        px(-4, 14, 8, 1, '#afc5ce')
        tap = int(now * 8) % 2
        px(-12, 11 + tap, 3, 2, highlight)
        px(9, 12 - tap, 3, 2, highlight)


def bounce(now, walking=False, laptop=False):
    return int(now * 8) % 2 * 2 if walking else math.sin(now * 3) * (0.25 if laptop else 1)
