import pygame
import random


class Particle:
    def __init__(self, x, y, color, velocity, lifetime):
        self.x = x
        self.y = y
        self.color = color
        self.vx, self.vy = velocity
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.size = random.randint(3, 6)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.3  # гравитация частиц
        self.lifetime -= 1
        self.size = max(1, self.size - 0.1)
        return self.lifetime > 0

    def draw(self, surface, camera_x, camera_y=0):
        pygame.draw.circle(surface, self.color,
                          (int(self.x - camera_x), int(self.y - camera_y)),
                          int(self.size))