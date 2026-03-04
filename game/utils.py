import sys

import pygame as pg
import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(asctime)s - %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler("citybuilder.log", mode="w"),  # 1. Writes to the file
        logging.StreamHandler(sys.stdout),  # 2. Writes to the Terminal
    ],
)
logger = logging.getLogger("CityBuilder")

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


@staticmethod
def format_isometric_asset(image, is_flat=False, grid_w=1, grid_h=1):
    bounding_rect = image.get_bounding_rect()
    if bounding_rect.width == 0 or bounding_rect.height == 0:
        return image  # Failsafe for empty images

    cropped = image.subsurface(bounding_rect).copy()

    if is_flat:
        # In your engine, a 1x1 tile footprint is exactly 128x64.
        # A 2x2 tile footprint is exactly 256x128.
        target_w = (grid_w + grid_h) * 64
        target_h = (grid_w + grid_h) * 32
        return pg.transform.smoothscale(cropped, (target_w, target_h))

    # For tall 3D buildings, we ONLY crop the padding to fix depth sorting.
    # We do not squash them, or they would look like flat pancakes!
    return cropped


@staticmethod
def load_images():
    from .setting import (
        AXE_URL,
        VIP_URL,
        TREE_URL,
        RESZONE_URL1,
        INDZONE_URL1,
        SERZONE_URL1,
        STADIUM_URL,
        UNIVERSITY_URL,
        SCHOOL_URL,
        HAMMER_URL,
        FIRE_STATION_URL,
        POLICE_URL,
        POWERPLANT_URL,
        ROAD_URL,
        POWERLINE_URL,
        BUILDING_SPECS,
    )

    raw_images = {
        "Axe": pg.image.load(AXE_URL).convert_alpha(),
        "Hammer": pg.image.load(HAMMER_URL).convert_alpha(),
        "VIP": pg.image.load(VIP_URL).convert_alpha(),
        "Tree": pg.image.load(TREE_URL).convert_alpha(),
        "ResZone": pg.image.load(RESZONE_URL1).convert_alpha(),
        "IndZone": pg.image.load(INDZONE_URL1).convert_alpha(),
        "SerZone": pg.image.load(SERZONE_URL1).convert_alpha(),
        "Stadium": pg.image.load(STADIUM_URL).convert_alpha(),
        "University": pg.image.load(UNIVERSITY_URL).convert_alpha(),
        "School": pg.image.load(SCHOOL_URL).convert_alpha(),
        "FireStation": pg.image.load(FIRE_STATION_URL).convert_alpha(),
        "Police": pg.image.load(POLICE_URL).convert_alpha(),
        "PowerPlant": pg.image.load(POWERPLANT_URL).convert_alpha(),
        "Road": pg.image.load(ROAD_URL).convert_alpha(),
        "PowerLine": pg.image.load(POWERLINE_URL).convert_alpha(),
    }
    formatted_images = {}
    for name, img in raw_images.items():
        if name in ["Axe", "Hammer", "VIP"]:
            formatted_images[name] = img
            continue
        is_flat_zone = name in ["ResZone", "IndZone", "SerZone"]
        w, h = BUILDING_SPECS.get(name, (1, 1))
        formatted_images[name] = format_isometric_asset(
            img, is_flat=is_flat_zone, grid_w=w, grid_h=h
        )
    return formatted_images


@staticmethod
def scale_image(image, w=None, h=None):
    # Pythonic way to check for None
    if w is None and h is None:
        return image

    if h is None:
        scale = w / image.get_width()
        h = scale * image.get_height()
    elif w is None:
        scale = h / image.get_height()
        w = scale * image.get_width()

    # smoothscale generally yields better visual results than standard scale
    return pg.transform.smoothscale(image, (int(w), int(h)))
