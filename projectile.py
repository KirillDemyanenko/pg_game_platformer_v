import pygame
from settings import PROJECTILE_COLOR, PROJECTILE_SPEED, PROJECTILE_LIFETIME


class Projectile(pygame.sprite.Sprite):
    def __init__(self, x, y, direction_right):
        super().__init__()
        self.image = pygame.Surface((16, 8), pygame.SRCALPHA)
        self._draw_projectile()
        self.rect = self.image.get_rect(center=(x, y))
        self.velocity_x = PROJECTILE_SPEED if direction_right else -PROJECTILE_SPEED
        self.lifetime = PROJECTILE_LIFETIME

    def _draw_projectile(self):
        """Рисует снаряд (можно заменить на спрайт)"""
        pygame.draw.ellipse(self.image, PROJECTILE_COLOR, (0, 0, 16, 8))
        pygame.draw.ellipse(self.image, (255, 200, 0), (2, 2, 12, 4))

    def update(self, platforms):
        self.rect.x += self.velocity_x
        self.lifetime -= 1

        # Проверка столкновения с платформами
        hits = pygame.sprite.spritecollide(self, platforms, False)
        if hits or self.lifetime <= 0:
            self.kill()

    def draw(self, surface, camera_x, camera_y=0):
        surface.blit(self.image, (self.rect.x - camera_x, self.rect.y - camera_y))