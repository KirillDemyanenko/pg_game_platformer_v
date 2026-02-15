import pygame
import math
import random
from settings import (PLAYER_SPEED, PLAYER_JUMP_POWER, GRAVITY,
                      PLAYER_FRICTION, MAX_FALL_SPEED, PROJECTILE_COOLDOWN,
                      USE_MASK_COLLISION, PLAYER_SIZE, TILE_SIZE)
from particle import Particle
from animation import AnimationManager
from projectile import Projectile


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, assets_path=None):
        super().__init__()

        # Размер игрока равен размеру тайла
        self.size = PLAYER_SIZE  # 128x128 пикселей

        # Анимации
        self.anim_manager = AnimationManager()
        self.assets_path = assets_path or "assets/player"
        self._load_animations()

        self.image = self.anim_manager.get_current_frame()
        if not self.image:
            self.image = pygame.Surface((self.size, self.size), pygame.SRCALPHA)

        self.rect = self.image.get_rect(topleft=(x, y))

        # Физика
        self.velocity_x = 0
        self.velocity_y = 0
        self.speed = PLAYER_SPEED
        self.jump_power = PLAYER_JUMP_POWER
        self.gravity = GRAVITY
        self.friction = PLAYER_FRICTION

        # Состояния
        self.on_ground = False
        self.facing_right = True
        self.state = "idle"

        # Атака
        self.projectiles = pygame.sprite.Group()
        self.attack_cooldown = 0
        self.is_attacking = False
        self.attack_triggered = False

        # Частицы
        self.particles = []

    def _load_animations(self):
        """Загружает все анимации размером с тайл"""
        # ИСПРАВЛЕНО: увеличен frame_duration для более плавной анимации
        # Было: 5, Стало: 12 (idle), 10 (run), 8 (jump), 5 (attack)
        self.anim_manager.load_from_directory(self.assets_path, "idle", frame_duration=12, loop=True)
        self.anim_manager.load_from_directory(self.assets_path, "run", frame_duration=10, loop=True)
        self.anim_manager.load_from_directory(self.assets_path, "jump", frame_duration=8, loop=False)
        self.anim_manager.load_from_directory(self.assets_path, "attack", frame_duration=5, loop=False)

        self._scale_animations()

        if not self.anim_manager.animations:
            self._create_placeholder_animations()

        self.anim_manager.play("idle")

    def _scale_animations(self):
        """Масштабирует все анимации до размера тайла"""
        for anim_name, animation in self.anim_manager.animations.items():
            scaled_frames = []
            for frame in animation.frames:
                if frame.get_size() != (self.size, self.size):
                    scaled_frame = pygame.transform.scale(frame, (self.size, self.size))
                    scaled_frames.append(scaled_frame)
                else:
                    scaled_frames.append(frame)
            animation.frames = scaled_frames

    def _create_placeholder_animations(self):
        """Создаёт заглушки размером с тайл (128x128)"""
        colors = {
            "idle": (100, 200, 255),
            "run": (100, 255, 100),
            "jump": (255, 200, 100),
            "attack": (255, 100, 100)
        }

        for name, color in colors.items():
            frames = []
            frame_count = 12 if name == "attack" else 4
            for i in range(frame_count):
                surface = pygame.Surface((self.size, self.size), pygame.SRCALPHA)

                body_width = 64
                body_height = 96
                body_x = (self.size - body_width) // 2
                body_y = self.size - body_height - 8

                offset = i if i < 2 else 3 - i
                if name == "attack":
                    if i < 6:
                        weapon_extend = i * 8
                    else:
                        weapon_extend = (11 - i) * 8
                    pygame.draw.rect(surface, (150, 150, 150),
                                     (body_x + body_width - 10, body_y + 30, 20 + weapon_extend, 12))

                pygame.draw.ellipse(surface, color,
                                    (body_x + offset, body_y, body_width - offset * 2, body_height))
                pygame.draw.circle(surface, (255, 220, 177),
                                   (self.size // 2, body_y - 10), 20)
                pygame.draw.circle(surface, (50, 50, 50), (self.size // 2 - 6, body_y - 15), 3)
                pygame.draw.circle(surface, (50, 50, 50), (self.size // 2 + 6, body_y - 15), 3)

                frames.append(surface)

            loop = name not in ["attack", "jump"]
            # ИСПРАВЛЕНО: увеличен frame_duration для placeholder анимаций
            self.anim_manager.add_animation(name, frames, frame_duration=12, loop=loop)

    def update(self, platforms):
        keys = pygame.key.get_pressed()

        # Атака
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        if (keys[pygame.K_j] or keys[pygame.K_z] or keys[pygame.K_LCTRL]) and not self.is_attacking:
            if self.attack_cooldown <= 0:
                self._start_attack()

        # Движение
        if not self.is_attacking:
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                self.facing_right = False
                self.velocity_x = -self.speed
            elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                self.facing_right = True
                self.velocity_x = self.speed
            else:
                self.velocity_x *= self.friction
        else:
            self.velocity_x = 0

        # Окончание атаки
        if self.is_attacking:
            current_anim = self.anim_manager.current_animation
            if current_anim and current_anim.finished:
                self.is_attacking = False
                self.attack_triggered = False
                if not self.on_ground:
                    self.anim_manager.play("jump")
                elif abs(self.velocity_x) > 0.5:
                    self.anim_manager.play("run")
                else:
                    self.anim_manager.play("idle")

        # Состояние
        if self.is_attacking:
            new_state = "attack"
        elif not self.on_ground:
            new_state = "jump"
        elif abs(self.velocity_x) > 0.5:
            new_state = "run"
        else:
            new_state = "idle"

        if new_state != self.state:
            self.state = new_state
            if new_state == "attack":
                self.anim_manager.play("attack", force_restart=True)
            elif not self.is_attacking:
                self.anim_manager.play(new_state)

        # Прыжок
        if not self.is_attacking and (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]) and self.on_ground:
            self.velocity_y = self.jump_power
            self.on_ground = False
            self._create_dust_particles()
            self.anim_manager.play("jump", force_restart=True)

        # Гравитация
        if not self.on_ground:
            self.velocity_y += self.gravity

        # Коллизии
        self._move_with_collision(platforms)

        # Анимация
        self.anim_manager.update()
        current_frame = self.anim_manager.get_current_frame()
        if current_frame:
            self.image = current_frame

        # Выстрел
        if self.is_attacking and not self.attack_triggered:
            current_anim = self.anim_manager.current_animation
            if current_anim and current_anim.current_frame == 3:
                self._fire_projectile()
                self.attack_triggered = True

        # Снаряды и частицы
        self.projectiles.update(platforms)
        for p in self.particles[:]:
            if not p.update():
                self.particles.remove(p)

        self.velocity_y = min(self.velocity_y, MAX_FALL_SPEED)

    def _start_attack(self):
        self.is_attacking = True
        self.attack_triggered = False
        self.attack_cooldown = PROJECTILE_COOLDOWN
        self.velocity_x = 0
        self.anim_manager.play("attack", force_restart=True)

    def _fire_projectile(self):
        spawn_y = self.rect.centery
        offset_x = self.size // 2 + 10 if self.facing_right else -(self.size // 2 + 10)
        projectile = Projectile(self.rect.centerx + offset_x, spawn_y, self.facing_right)
        self.projectiles.add(projectile)
        self._create_shoot_particles()

    def _create_dust_particles(self):
        for _ in range(5):
            vx = random.uniform(-2, 2)
            vy = random.uniform(-1, -3)
            self.particles.append(Particle(self.rect.centerx, self.rect.bottom, (200, 200, 180), (vx, vy), 20))

    def _create_shoot_particles(self):
        for _ in range(3):
            vx = random.uniform(2, 5) if self.facing_right else random.uniform(-5, -2)
            vy = random.uniform(-1, 1)
            self.particles.append(Particle(self.rect.centerx, self.rect.centery, (255, 200, 0), (vx, vy), 15))

    def _move_with_collision(self, platforms):
        # Движение по X
        if self.velocity_x != 0:
            self.rect.x += self.velocity_x
            self._check_collision(platforms, 'x')

        # Движение по Y
        self.rect.y += self.velocity_y

        # Сбрасываем on_ground перед проверкой
        was_on_ground = self.on_ground
        self.on_ground = False

        self._check_collision(platforms, 'y')

    def _check_collision(self, platforms, direction):
        """Упрощённая проверка коллизий с использованием rect"""
        for platform in platforms:
            if not self.rect.colliderect(platform.rect):
                continue

            if direction == 'x':
                # Коллизия по X - просто отталкиваем
                if self.velocity_x > 0:
                    self.rect.right = platform.rect.left
                elif self.velocity_x < 0:
                    self.rect.left = platform.rect.right
                self.velocity_x = 0
                return

            elif direction == 'y':
                if self.velocity_y > 0:  # Падаем
                    # Проверяем, что мы действительно над платформой
                    if self.rect.bottom <= platform.rect.centery:
                        self.rect.bottom = platform.rect.top
                        self.velocity_y = 0
                        self.on_ground = True
                        return
                elif self.velocity_y < 0:  # Летим вверх
                    # Проверяем, что мы действительно под платформой
                    if self.rect.top >= platform.rect.centery:
                        self.rect.top = platform.rect.bottom
                        self.velocity_y = 0
                        return

    def draw(self, surface, camera_x, camera_y=0):
        # Отражаем спрайт если смотрим влево
        if not self.facing_right:
            flipped_image = pygame.transform.flip(self.image, True, False)
            surface.blit(flipped_image, (self.rect.x - camera_x, self.rect.y - camera_y))
        else:
            surface.blit(self.image, (self.rect.x - camera_x, self.rect.y - camera_y))

        for projectile in self.projectiles:
            projectile.draw(surface, camera_x, camera_y)

        for particle in self.particles:
            particle.draw(surface, camera_x, camera_y)