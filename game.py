import pygame
import pytmx
import os
from settings import (SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, DEFAULT_MAP,
                      PLAYER_ASSETS_DIR, MAPS_DIR, TILE_SCALE, CAMERA_SMOOTH)
from player import Player
from platform import Platform


class Game:
    def __init__(self, player_assets_path=None, map_path=None):
        self.player_assets_path = player_assets_path or PLAYER_ASSETS_DIR
        self.map_path = map_path or DEFAULT_MAP
        self.all_sprites = pygame.sprite.Group()
        self.platforms = pygame.sprite.Group()
        self.player = None
        self.camera_x = 0
        self.camera_y = 0  # Добавлена вертикальная позиция камеры
        self.level_width = 0
        self.level_height = 0
        self.tile_scale = TILE_SCALE

        self._load_map()

    def _load_map(self):
        if os.path.exists(self.map_path):
            try:
                self.load_tmx_map(self.map_path)
                return
            except Exception as e:
                print(f"Не удалось загрузить {self.map_path}: {e}")

        print("Создаётся демо-уровень")
        self._create_demo_level()

    def _create_demo_level(self):
        self.platforms.empty()
        self.all_sprites.empty()

        tile_size = int(64 * self.tile_scale)

        for i in range(0, 2000, tile_size):
            platform = Platform(i, 600, tile_size, tile_size, 'ground')
            self.platforms.add(platform)
            self.all_sprites.add(platform)

        platforms_data = [
            (300, 500, 128, 32), (500, 400, 128, 32),
            (800, 350, 64, 32), (1000, 450, 128, 32),
            (1300, 300, 192, 32), (1600, 400, 128, 32),
        ]

        for x, y, w, h in platforms_data:
            x, y = int(x * self.tile_scale), int(y * self.tile_scale)
            w, h = int(w * self.tile_scale), int(h * self.tile_scale)
            platform = Platform(x, y, w, h, 'stone')
            self.platforms.add(platform)
            self.all_sprites.add(platform)

        self.player = Player(100, 400, self.player_assets_path)
        self.player.tile_scale = self.tile_scale
        self.all_sprites.add(self.player)
        self.level_width = int(2000 * self.tile_scale)
        self.level_height = 720

    def load_tmx_map(self, filepath):
        tmx_data = pytmx.load_pygame(filepath)

        original_tile_width = tmx_data.tilewidth
        original_tile_height = tmx_data.tileheight

        scaled_tile_width = int(original_tile_width * self.tile_scale)
        scaled_tile_height = int(original_tile_height * self.tile_scale)

        self.level_width = tmx_data.width * scaled_tile_width
        self.level_height = tmx_data.height * scaled_tile_height

        self.platforms.empty()
        self.all_sprites.empty()

        for layer in tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                for x, y, gid in layer:
                    tile = tmx_data.get_tile_image_by_gid(gid)
                    if tile:
                        if self.tile_scale != 1.0:
                            new_width = int(tile.get_width() * self.tile_scale)
                            new_height = int(tile.get_height() * self.tile_scale)
                            tile = pygame.transform.scale(tile, (new_width, new_height))

                        platform = Platform(
                            x * scaled_tile_width,
                            y * scaled_tile_height,
                            scaled_tile_width,
                            scaled_tile_height
                        )
                        platform.set_image(tile)
                        self.platforms.add(platform)
                        self.all_sprites.add(platform)

        player_spawned = False
        for obj_layer in tmx_data.objectgroups:
            for obj in obj_layer:
                if obj.name == 'player':
                    spawn_x = int(obj.x * self.tile_scale)
                    spawn_y = int(obj.y * self.tile_scale)
                    self.player = Player(spawn_x, spawn_y, self.player_assets_path)
                    self.player.tile_scale = self.tile_scale
                    self.all_sprites.add(self.player)
                    player_spawned = True
                    break

        if not player_spawned:
            self.player = Player(self.level_width // 2, 100, self.player_assets_path)
            self.player.tile_scale = self.tile_scale
            self.all_sprites.add(self.player)

        print(f"Карта загружена: {self.level_width}x{self.level_height} (масштаб {self.tile_scale}x)")

    def reload_map(self):
        self._load_map()

    def update(self):
        self.player.update(self.platforms)

        # Горизонтальная камера
        target_x = self.player.rect.centerx - SCREEN_WIDTH // 2
        self.camera_x += (target_x - self.camera_x) * CAMERA_SMOOTH

        # Вертикальная камера
        target_y = self.player.rect.centery - SCREEN_HEIGHT // 2
        self.camera_y += (target_y - self.camera_y) * CAMERA_SMOOTH

        # Ограничение камеры границами уровня
        max_camera_x = max(0, self.level_width - SCREEN_WIDTH)
        max_camera_y = max(0, self.level_height - SCREEN_HEIGHT)

        self.camera_x = max(0, min(self.camera_x, max_camera_x))
        self.camera_y = max(0, min(self.camera_y, max_camera_y))

    def draw(self, surface, clock):
        # Фон (градиент)
        for y in range(SCREEN_HEIGHT):
            color_val = int(135 - y * 0.1)
            pygame.draw.line(surface, (color_val, 206, 235), (0, y), (SCREEN_WIDTH, y))

        # Облака (параллакс с учётом вертикали)
        for i in range(5):
            x = (i * 300 - int(self.camera_x * 0.3)) % (SCREEN_WIDTH + 200) - 100
            y = (50 + i * 30 - int(self.camera_y * 0.1)) % (SCREEN_HEIGHT + 100) - 50
            pygame.draw.ellipse(surface, (255, 255, 255), (x, y, 120, 40))

        # Платформы с учётом обеих координат камеры
        for sprite in self.all_sprites:
            if not isinstance(sprite, Player):
                surface.blit(sprite.image,
                             (sprite.rect.x - self.camera_x,
                              sprite.rect.y - self.camera_y))

        # Игрок
        self.player.draw(surface, self.camera_x, self.camera_y)

        # UI
        font = pygame.font.Font(None, 36)
        fps_text = font.render(f"FPS: {int(clock.get_fps())}", True, WHITE)
        pos_text = font.render(f"Pos: {int(self.player.rect.x)}, {int(self.player.rect.y)}", True, WHITE)
        state_text = font.render(f"State: {self.player.state}", True, WHITE)
        ammo_text = font.render(f"Projectiles: {len(self.player.projectiles)}", True, WHITE)
        scale_text = font.render(f"Scale: {self.tile_scale}x", True, WHITE)
        cam_text = font.render(f"Cam: {int(self.camera_x)}, {int(self.camera_y)}", True, WHITE)

        surface.blit(fps_text, (10, 10))
        surface.blit(pos_text, (10, 50))
        surface.blit(state_text, (10, 90))
        surface.blit(ammo_text, (10, 130))
        surface.blit(scale_text, (10, 170))
        surface.blit(cam_text, (10, 210))