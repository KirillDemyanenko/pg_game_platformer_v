import pygame
import math
import random
from settings import (PLAYER_SPEED, PLAYER_JUMP_POWER, GRAVITY,
                      PLAYER_FRICTION, MAX_FALL_SPEED, PROJECTILE_COOLDOWN,
                      USE_MASK_COLLISION)
from particle import Particle
from animation import AnimationManager
from projectile import Projectile


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, assets_path=None):
        super().__init__()

        # Анимации
        self.anim_manager = AnimationManager()
        self.assets_path = assets_path or "assets/player"
        self._load_animations()

        self.image = self.anim_manager.get_current_frame()
        if not self.image:
            self.image = pygame.Surface((32, 48), pygame.SRCALPHA)

        self.rect = self.image.get_rect(topleft=(x, y))

        # Маски для каждого кадра анимации (кэш)
        self.mask_cache = {}
        self.narrow_mask_cache = {}
        self._update_masks()

        # Хитбокс для коллизий без маски
        self.hitbox = pygame.Rect(0, 0, 30, 64)
        self.hitbox.center = self.rect.center

        self.width = self.rect.width
        self.height = self.rect.height

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
        """Загружает все анимации"""
        self.anim_manager.load_from_directory(self.assets_path, "idle", frame_duration=5, loop=True)
        self.anim_manager.load_from_directory(self.assets_path, "run", frame_duration=5, loop=True)
        self.anim_manager.load_from_directory(self.assets_path, "jump", frame_duration=5, loop=False)
        self.anim_manager.load_from_directory(self.assets_path, "attack", frame_duration=3, loop=False)

        if not self.anim_manager.animations:
            self._create_placeholder_animations()

        self.anim_manager.play("idle")

    def _create_placeholder_animations(self):
        """Создаёт заглушки если нет спрайтов"""
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
                surface = pygame.Surface((48 if name == "attack" else 32, 48), pygame.SRCALPHA)
                offset = i if i < 2 else 3 - i
                width = 32

                if name == "attack":
                    if i < 6:
                        weapon_extend = i * 4
                    else:
                        weapon_extend = (11 - i) * 4
                    width = 32 + weapon_extend
                    pygame.draw.rect(surface, (150, 150, 150), (20, 20, 10 + weapon_extend, 8))

                pygame.draw.ellipse(surface, color, (4 + offset, 16, width - 8 - offset * 2, 32))
                pygame.draw.circle(surface, (255, 220, 177), (16, 12), 10)
                frames.append(surface)

            loop = name not in ["attack", "jump"]
            self.anim_manager.add_animation(name, frames, frame_duration=3, loop=loop)

    def _get_image_key(self, image):
        """Создаёт уникальный ключ для кэширования маски"""
        return id(image)

    def _create_narrow_mask(self, image):
        """Создаёт узкую маску 30px шириной для X коллизий"""
        bbox = image.get_bounding_rect()

        if bbox.width <= 0 or bbox.height <= 0:
            return pygame.mask.from_surface(image), 0, 0

        body_width = min(30, bbox.width)
        body_height = bbox.height

        center_x = bbox.x + bbox.width // 2
        left = center_x - body_width // 2
        top = bbox.y

        left = max(bbox.x, left)
        if left + body_width > bbox.x + bbox.width:
            body_width = bbox.x + bbox.width - left

        if body_width <= 0 or body_height <= 0:
            return pygame.mask.from_surface(image), 0, 0

        narrow_rect = pygame.Rect(left, top, body_width, body_height)
        narrow_surface = image.subsurface(narrow_rect)
        narrow_mask = pygame.mask.from_surface(narrow_surface)

        return narrow_mask, left, top

    def _update_masks(self):
        """Создаёт или берёт из кэша маски для текущего изображения"""
        image_key = self._get_image_key(self.image)

        # Полная маска (для Y коллизий)
        if image_key not in self.mask_cache:
            bbox = self.image.get_bounding_rect()

            if bbox.width > 0 and bbox.height > 0:
                trimmed = self.image.subsurface(bbox)
                mask = pygame.mask.from_surface(trimmed)
                offset_x = bbox.x
                offset_y = bbox.y
            else:
                mask = pygame.mask.from_surface(self.image)
                offset_x = 0
                offset_y = 0

            self.mask_cache[image_key] = (mask, offset_x, offset_y)

        self.mask, self.mask_offset_x, self.mask_offset_y = self.mask_cache[image_key]

        # Узкая маска 30px (для X коллизий)
        if image_key not in self.narrow_mask_cache:
            narrow_mask, narrow_offset_x, narrow_offset_y = self._create_narrow_mask(self.image)
            self.narrow_mask_cache[image_key] = (narrow_mask, narrow_offset_x, narrow_offset_y)

        self.narrow_mask, self.narrow_offset_x, self.narrow_offset_y = self.narrow_mask_cache[image_key]

    def _update_hitbox(self):
        """Обновляет хитбокс относительно rect"""
        self.hitbox.centerx = self.rect.centerx
        self.hitbox.bottom = self.rect.bottom - 10

    def update(self, platforms):
        keys = pygame.key.get_pressed()

        # Атака по нажатию
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        if (keys[pygame.K_j] or keys[pygame.K_z] or keys[pygame.K_LCTRL]) and not self.is_attacking:
            if self.attack_cooldown <= 0:
                self._start_attack()

        # Управление движением (нельзя двигаться во время атаки)
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

        # Проверяем окончание анимации атаки
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

        # Определение состояния
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

        # Гравитация (всегда применяем если не на земле)
        if not self.on_ground:
            self.velocity_y += self.gravity

        # Применение скорости с проверкой коллизий
        self._move_with_collision(platforms)

        # Обновление анимации
        old_image = self.image
        self.anim_manager.update()
        current_frame = self.anim_manager.get_current_frame()
        if current_frame:
            self.image = current_frame
            if self.image != old_image:
                self._update_masks()

        # Выстрел в середине анимации
        if self.is_attacking and not self.attack_triggered:
            current_anim = self.anim_manager.current_animation
            if current_anim and current_anim.current_frame == 3:
                self._fire_projectile()
                self.attack_triggered = True

        # Обновление снарядов
        self.projectiles.update(platforms)

        # Обновление частиц
        for p in self.particles[:]:
            if not p.update():
                self.particles.remove(p)

        self.velocity_y = min(self.velocity_y, MAX_FALL_SPEED)

    def _start_attack(self):
        """Начинает анимацию атаки"""
        self.is_attacking = True
        self.attack_triggered = False
        self.attack_cooldown = PROJECTILE_COOLDOWN
        self.velocity_x = 0
        self.anim_manager.play("attack", force_restart=True)

    def _fire_projectile(self):
        """Создаёт снаряд"""
        spawn_y = self.rect.bottom - 32
        offset_x = 20 if self.facing_right else -20

        projectile = Projectile(
            self.rect.centerx + offset_x,
            spawn_y,
            self.facing_right
        )
        self.projectiles.add(projectile)

        self._create_shoot_particles()

    def _move_with_collision(self, platforms):
        """Движение с проверкой коллизий"""
        self._update_hitbox()

        # Движение по X (узкая маска 30px)
        if self.velocity_x != 0:
            self.rect.x += self.velocity_x
            self._update_hitbox()
            if USE_MASK_COLLISION:
                self._check_collision_mask_narrow(platforms)
            else:
                self._check_collision_hitbox(platforms, 'x')

        # Движение по Y
        # Сначала применяем гравитацию/скорость
        self.rect.y += self.velocity_y
        self._update_hitbox()

        # Проверяем коллизию с платформами
        self.on_ground = False
        if USE_MASK_COLLISION:
            self._check_collision_mask_full(platforms)
        else:
            self._check_collision_hitbox(platforms, 'y')

    def _check_collision_mask_narrow(self, platforms):
        """Проверка горизонтальных коллизий с УЗКОЙ маской (30px)"""
        for platform in platforms:
            if not self.rect.colliderect(platform.rect):
                continue

            offset = (
                platform.rect.x - self.rect.x - self.narrow_offset_x,
                platform.rect.y - self.rect.y - self.narrow_offset_y
            )

            if platform.mask.overlap(self.narrow_mask, offset):
                if self.velocity_x > 0:
                    self.rect.right = platform.rect.left
                elif self.velocity_x < 0:
                    self.rect.left = platform.rect.right
                self.velocity_x = 0
                self._update_hitbox()
                return

    def _check_collision_mask_full(self, platforms):
        """Проверка вертикальных коллизий с ПОЛНОЙ маской"""
        for platform in platforms:
            if not self.rect.colliderect(platform.rect):
                continue

            offset = (
                platform.rect.x - self.rect.x - self.mask_offset_x,
                platform.rect.y - self.rect.y - self.mask_offset_y
            )

            if platform.mask.overlap(self.mask, offset):
                if self.velocity_y >= 0:  # Падаем или стоим
                    # Ставим точно на платформу без буфера
                    self.rect.bottom = platform.rect.top
                    self.velocity_y = 0
                    self.on_ground = True
                elif self.velocity_y < 0:  # Прыгаем вверх
                    self.rect.top = platform.rect.bottom
                    self.velocity_y = 0
                self._update_hitbox()
                return

    def _check_collision_hitbox(self, platforms, direction):
        """Проверка коллизий с использованием хитбокса 30px"""
        for platform in platforms:
            if not self.hitbox.colliderect(platform.rect):
                continue

            if direction == 'x':
                if self.velocity_x > 0:
                    self.rect.right = platform.rect.left
                elif self.velocity_x < 0:
                    self.rect.left = platform.rect.right
                self.velocity_x = 0
                self._update_hitbox()
                return

            elif direction == 'y':
                if self.velocity_y >= 0:  # Падаем или стоим
                    self.rect.bottom = platform.rect.top
                    self.velocity_y = 0
                    self.on_ground = True
                elif self.velocity_y < 0:  # Прыгаем вверх
                    self.rect.top = platform.rect.bottom
                    self.velocity_y = 0
                self._update_hitbox()
                return

    def _create_shoot_particles(self):
        """Создаёт частицы при выстреле"""
        offset_x = 25 if self.facing_right else -25
        spawn_y = self.rect.bottom - 32

        for _ in range(3):
            vx = (random.uniform(1, 3) if self.facing_right else random.uniform(-3, -1))
            vy = random.uniform(-1, 1)
            color = (255, 255, 100)
            self.particles.append(Particle(
                self.rect.centerx + offset_x,
                spawn_y,
                color,
                (vx, vy),
                10
            ))

    def _create_dust_particles(self):
        for _ in range(5):
            vx = random.uniform(-2, 2)
            vy = random.uniform(-1, -3)
            color = (200, 200, 200)
            self.particles.append(Particle(
                self.rect.centerx,
                self.rect.bottom,
                color,
                (vx, vy),
                20
            ))

    def draw(self, surface, camera_x, camera_y=0):
        img = self.image if self.facing_right else pygame.transform.flip(self.image, True, False)
        surface.blit(img, (self.rect.x - camera_x, self.rect.y - camera_y))

        for projectile in self.projectiles:
            projectile.draw(surface, camera_x, camera_y)

        for p in self.particles:
            p.draw(surface, camera_x, camera_y)