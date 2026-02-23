class Building:
    def __init__(self, pos, image, name):
        # .convert_alpha() speeds up rendering for transparent images
        self.image = image
        self.name = name
        self.rect = self.image.get_rect(topleft=pos)
        self.counter = 0

    def update(self):
        self.counter += 1


class Lumbermill(Building):
    def __init__(self, pos, image):
        super().__init__(pos, image, "Lumbermill")


class Stonemasonry(Building):
    def __init__(self, pos, image):
        super().__init__(pos, image, "Stonemasonry")