import pygame
import random
from settings import GROUND_COLOR, GRASS_COLOR, STONE_COLOR, USE_MASK_COLLISION


class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, tile_type='ground'):
        super().__init__()
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        self._draw_tile(width, height, tile_type)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.tile_type = tile_type

        # Создаём маску для точной коллизии
        if USE_MASK_COLLISION:
            self.mask = pygame.mask.from_surface(self.image)

    def _draw_tile(self, w, h, tile_type):
        """Процедурная графика для платформ"""
        if tile_type == 'ground':
            self.image.fill(GROUND_COLOR)
            pygame.draw.rect(self.image, GRASS_COLOR, (0, 0, w, 8))
            for i in range(0, w, 16):
                for j in range(8, h, 16):
                    pygame.draw.rect(self.image, (160, 82, 45), (i, j, 4, 4))
        elif tile_type == 'stone':
            self.image.fill(STONE_COLOR)
            for i in range(0, w, 8):
                for j in range(0, h, 8):
                    if random.random() > 0.5:
                        pygame.draw.rect(self.image, (150, 150, 150), (i, j, 4, 4))
        else:
            self.image.fill((100, 100, 100))

    def set_image(self, image):
        """Установка изображения из TMX с обновлением rect и маски"""
        old_topleft = self.rect.topleft  # Сохраняем позицию
        self.image = image
        # Обновляем rect под новый размер изображения
        self.rect = self.image.get_rect(topleft=old_topleft)

        # Обновляем маску при смене изображения
        if USE_MASK_COLLISION:
            self.mask = pygame.mask.from_surface(self.image)