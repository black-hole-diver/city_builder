import pygame as pg

_font_cache = {}


def draw_text(screen, text, size, color, pos):
    if size not in _font_cache:
        _font_cache[size] = pg.font.SysFont(None, size)
    font = _font_cache[size]
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(topleft=pos)

    screen.blit(text_surface, text_rect)

def get_line(x1, y1, x2, y2):
        """Bresenham's Line Algorithm for Line of Sight and intersection check"""
        points = []
        dx, dy = abs(x2 - x1), abs(y2 - y1)
        x, y = int(x1), int(y1)
        sx = -1 if x1 > x2 else 1
        sy = -1 if y1 > y2 else 1
        if dx > dy:
            err = dx / 2.0
            while x != int(x2):
                points.append((x, y))
                err -= dy
                if err < 0:
                    y += sy
                    err += dx
                x += sx
        else:
            err = dy / 2.0
            while y != int(y2):
                points.append((x, y))
                err -= dx
                if err < 0:
                    x += sx
                    err += dy
                y += sy
        points.append((x, y))
        return points