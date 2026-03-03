import pygame as pg
from .setting import MAP_WIDTH, MAP_HEIGHT, MARGIN


class Camera:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.scroll = pg.Vector2(0, 0)
        self.dx = 0
        self.dy = 0
        self.speed = 25

    def update(self):
        """Scroll the camera based on mouse position near the edges of the screen"""
        mouse_pos = pg.mouse.get_pos()
        if mouse_pos[0] > self.width * 0.97:
            self.dx = -self.speed
        elif mouse_pos[0] < self.width * 0.03:
            self.dx = self.speed
        else:
            self.dx = 0
        if mouse_pos[1] > self.height * 0.97:
            self.dy = -self.speed
        elif mouse_pos[1] < self.height * 0.03:
            self.dy = self.speed
        else:
            self.dy = 0

        self.scroll.x += self.dx
        self.scroll.y += self.dy

        self._adjust_bound()

    def _adjust_bound(self):
        """Keep the camera within the bounds of the map"""
        center_offset = MAP_WIDTH / 2

        if self.scroll.x > MARGIN:
            self.scroll.x = MARGIN
        elif self.scroll.x < -(center_offset + MARGIN + self.width):
            self.scroll.x = -(center_offset + MARGIN + self.width)

        if self.scroll.y > MARGIN:
            self.scroll.y = MARGIN
        elif self.scroll.y < -(MAP_HEIGHT + MARGIN - self.height):
            self.scroll.y = -(MAP_HEIGHT + MARGIN - self.height)
