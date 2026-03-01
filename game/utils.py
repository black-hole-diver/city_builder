import pygame as pg

_font_cache = {}


def draw_text(screen, text, size, color, pos):
    if size not in _font_cache:
        _font_cache[size] = pg.font.SysFont(None, size)
    font = _font_cache[size]
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(topleft=pos)

    screen.blit(text_surface, text_rect)
