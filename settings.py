import pygame
import os

pygame.init()

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Масштаб тайлов
TILE_SCALE = 3.0

# Настройки камеры
CAMERA_SMOOTH = 0.1

# Настройки коллизии
USE_MASK_COLLISION = True

# Настройки диалога
DIALOG_TRIGGER_DISTANCE = 100  # пикселей для активации диалога
DIALOG_TEXT_SPEED = 2  # символов за кадр

# Цвета
SKY_BLUE = (135, 206, 235)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GROUND_COLOR = (139, 69, 19)
GRASS_COLOR = (34, 139, 34)
STONE_COLOR = (128, 128, 128)
PLAYER_BODY_COLOR = (100, 200, 255)
PLAYER_SKIN_COLOR = (255, 220, 177)
NPC_BODY_COLOR = (255, 200, 100)
NPC_SKIN_COLOR = (255, 220, 177)
PROJECTILE_COLOR = (255, 255, 0)
DIALOG_BG = (255, 255, 255)
DIALOG_BORDER = (100, 100, 100)
DIALOG_TEXT = (0, 0, 0)

# Физика
GRAVITY = 0.6
PLAYER_SPEED = 5
PLAYER_JUMP_POWER = -12
PLAYER_FRICTION = 0.8
MAX_FALL_SPEED = 15

# Атака
PROJECTILE_SPEED = 10
PROJECTILE_COOLDOWN = 15
PROJECTILE_LIFETIME = 120

# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
MAPS_DIR = os.path.join(ASSETS_DIR, "maps")
DEFAULT_MAP = os.path.join(MAPS_DIR, "map.tmx")
PLAYER_ASSETS_DIR = os.path.join(ASSETS_DIR, "player")
NPC_ASSETS_DIR = os.path.join(ASSETS_DIR, "npc")