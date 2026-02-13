import pygame
import pytmx
import os
from settings import (SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, DEFAULT_MAP,
                      PLAYER_ASSETS_DIR, MAPS_DIR, TILE_SCALE, CAMERA_SMOOTH,
                      NPC_ASSETS_DIR)
from player import Player
from platform import Platform
from npc import NPC


class Game:
    def __init__(self, player_assets_path=None, map_path=None):
        self.player_assets_path = player_assets_path or PLAYER_ASSETS_DIR
        self.map_path = map_path or DEFAULT_MAP
        self.all_sprites = pygame.sprite.Group()
        self.platforms = pygame.sprite.Group()
        self.npcs = pygame.sprite.Group()
        self.player = None
        self.camera_x = 0
        self.camera_y = 0
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
        """Создаёт демо-уровень с NPC в середине"""
        self.platforms.empty()
        self.all_sprites.empty()
        self.npcs.empty()

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

        # Игрок
        self.player = Player(100, 400, self.player_assets_path)
        self.all_sprites.add(self.player)

        # NPC в середине карты
        npc_x = 1000  # середина демо-уровня
        npc_y = 600 - 128  # на земле
        npc = NPC(npc_x, npc_y, NPC_ASSETS_DIR,
                  "Добро пожаловать в этот мир! Я уже много лет исследую эти земли. "
                  "На востоке есть древние руины, но путь туда опасен. "
                  "Берегись летучих мышей в пещерах!")
        self.npcs.add(npc)
        self.all_sprites.add(npc)

        self.level_width = int(2000 * self.tile_scale)
        self.level_height = 720

    def load_tmx_map(self, filepath):
        """Загрузка карты из Tiled с NPC в середине"""
        tmx_data = pytmx.load_pygame(filepath)

        original_tile_width = tmx_data.tilewidth
        original_tile_height = tmx_data.tileheight

        scaled_tile_width = int(original_tile_width * self.tile_scale)
        scaled_tile_height = int(original_tile_height * self.tile_scale)

        self.level_width = tmx_data.width * scaled_tile_width
        self.level_height = tmx_data.height * scaled_tile_height

        self.platforms.empty()
        self.all_sprites.empty()
        self.npcs.empty()

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
                    self.all_sprites.add(self.player)
                    player_spawned = True

        if not player_spawned:
            self.player = Player(100, 100, self.player_assets_path)
            self.all_sprites.add(self.player)

        # NPC в середине карты
        npc_x = self.level_width // 2
        npc_y = self.level_height - 200  # чуть выше низа
        npc = NPC(npc_x, npc_y, NPC_ASSETS_DIR,
                  "Приветствую тебя в этом загадочном мире! "
                  "Я старейшина этих мест. Давным-давно здесь процветала великая цивилизация, "
                  "но теперь остались лишь руины и воспоминания. "
                  "Ищи артефакты древних — они помогут тебе в пути!")
        self.npcs.add(npc)
        self.all_sprites.add(npc)

        print(f"Карта загружена: {self.level_width}x{self.level_height} (масштаб {self.tile_scale}x)")

    def reload_map(self):
        self._load_map()

    def update(self):
        # Обновляем NPC (проверка диалога)
        for npc in self.npcs:
            npc.update(self.player)

        # Проверяем блокировку движения
        blocked = any(npc.is_blocking() for npc in self.npcs)

        # Обновляем игрока только если не заблокирован
        if not blocked:
            self.player.update(self.platforms)
        else:
            # Игрок стоит, но можно пропустить диалог
            keys = pygame.key.get_pressed()
            if keys[pygame.K_SPACE] or keys[pygame.K_e] or keys[pygame.K_RETURN]:
                for npc in self.npcs:
                    if npc.dialog_active:
                        npc.close_dialog()

        # Камера
        target_x = self.player.rect.centerx - SCREEN_WIDTH // 2
        self.camera_x += (target_x - self.camera_x) * CAMERA_SMOOTH

        target_y = self.player.rect.centery - SCREEN_HEIGHT // 2
        self.camera_y += (target_y - self.camera_y) * CAMERA_SMOOTH

        max_camera_x = max(0, self.level_width - SCREEN_WIDTH)
        max_camera_y = max(0, self.level_height - SCREEN_HEIGHT)

        self.camera_x = max(0, min(self.camera_x, max_camera_x))
        self.camera_y = max(0, min(self.camera_y, max_camera_y))

    def draw(self, surface, clock):
        # Фон
        for y in range(SCREEN_HEIGHT):
            color_val = int(135 - y * 0.1)
            pygame.draw.line(surface, (color_val, 206, 235), (0, y), (SCREEN_WIDTH, y))

        # Облака
        for i in range(5):
            x = (i * 300 - int(self.camera_x * 0.3)) % (SCREEN_WIDTH + 200) - 100
            y = (50 + i * 30 - int(self.camera_y * 0.1)) % (SCREEN_HEIGHT + 100) - 50
            pygame.draw.ellipse(surface, (255, 255, 255), (x, y, 120, 40))

        # Платформы
        for sprite in self.all_sprites:
            if not isinstance(sprite, (Player, NPC)):
                surface.blit(sprite.image,
                             (sprite.rect.x - self.camera_x,
                              sprite.rect.y - self.camera_y))

        # NPC (рисуем перед игроком)
        for npc in self.npcs:
            npc.draw(surface, self.camera_x, self.camera_y)

        # Игрок
        self.player.draw(surface, self.camera_x, self.camera_y)

        # UI подсказка
        blocked = any(npc.is_blocking() for npc in self.npcs)
        if blocked:
            font = pygame.font.Font(None, 36)
            hint = font.render("Нажмите SPACE или E чтобы продолжить", True, WHITE)
            surface.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 50))

        # UI
        font = pygame.font.Font(None, 36)
        fps_text = font.render(f"FPS: {int(clock.get_fps())}", True, WHITE)
        pos_text = font.render(f"Pos: {int(self.player.rect.x)}, {int(self.player.rect.y)}", True, WHITE)
        state_text = font.render(f"State: {self.player.state}", True, WHITE)

        surface.blit(fps_text, (10, 10))
        surface.blit(pos_text, (10, 50))
        surface.blit(state_text, (10, 90))