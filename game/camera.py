import pygame as pg
from .setting import MAP_WIDTH, MAP_HEIGHT, MARGIN

class Camera:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.scroll = pg.Vector2(0,0)
        self.dx = 0
        self.dy = 0
        self.speed = 25

    def update(self):
        mouse_pos = pg.mouse.get_pos()
        if mouse_pos[0] > self.width * .97:
            self.dx = -self.speed
        elif mouse_pos[0] < self.width * .03:
            self.dx = self.speed
        else:
            self.dx = 0
        if mouse_pos[1] > self.height * .97:
            self.dy = -self.speed
        elif mouse_pos[1] < self.height * .03:
            self.dy = self.speed
        else:
            self.dy = 0

        # update camera scroll
        self.scroll.x += self.dx
        self.scroll.y += self.dy

        # bound to the world
        # left bound
        # X Boundaries (Left and Right)


        if self.scroll.x > MARGIN:
            self.scroll.x = MARGIN
        elif self.scroll.x < -(MAP_WIDTH- self.width):
            self.scroll.x = -(MAP_WIDTH- self.width)

        # Y Boundaries (Top and Bottom)
        if self.scroll.y > MARGIN:
            self.scroll.y = MARGIN
        elif self.scroll.y < -(MAP_HEIGHT - self.height):
            self.scroll.y = -(MAP_HEIGHT - self.height)