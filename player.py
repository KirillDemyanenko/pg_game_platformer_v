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

        # Создаём маску из обрезанного изображения
        self._update_mask()

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
        self.attack_triggered = False  # чтобы выстрел был один за анимацию

        # Частицы
        self.particles = []

        # Для стабильности коллизий
        self.ground_buffer = 2

    def _load_animations(self):
        """Загружает все анимации"""
        self.anim_manager.load_from_directory(self.assets_path, "idle", frame_duration=5, loop=True)
        self.anim_manager.load_from_directory(self.assets_path, "run", frame_duration=5, loop=True)
        self.anim_manager.load_from_directory(self.assets_path, "jump", frame_duration=5, loop=False)
        # Атака: 12 кадров, каждый по 3 тика = 36 кадров total (0.6 сек при 60fps)
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
            # Для атаки 12 кадров как в реальной анимации
            frame_count = 12 if name == "attack" else 4
            for i in range(frame_count):
                surface = pygame.Surface((48 if name == "attack" else 32, 48), pygame.SRCALPHA)
                offset = i if i < 2 else 3 - i
                width = 32

                if name == "attack":
                    # Анимация атаки: выдвигаем "оружие" постепенно и убираем
                    if i < 6:
                        weapon_extend = i * 4  # 0, 4, 8, 12, 16, 20
                    else:
                        weapon_extend = (11 - i) * 4  # 20, 16, 12, 8, 4, 0
                    width = 32 + weapon_extend
                    pygame.draw.rect(surface, (150, 150, 150), (20, 20, 10 + weapon_extend, 8))

                pygame.draw.ellipse(surface, color, (4 + offset, 16, width - 8 - offset * 2, 32))
                pygame.draw.circle(surface, (255, 220, 177), (16, 12), 10)
                frames.append(surface)

            loop = name not in ["attack", "jump"]
            self.anim_manager.add_animation(name, frames, frame_duration=3, loop=loop)

    def _update_mask(self):
        """Создаёт маску из обрезанного изображения"""
        bbox = self.image.get_bounding_rect()

        if bbox.width > 0 and bbox.height > 0:
            trimmed = self.image.subsurface(bbox)
            self.mask = pygame.mask.from_surface(trimmed)
            self.mask_offset = (bbox.x, bbox.y)
        else:
            self.mask = pygame.mask.from_surface(self.image)
            self.mask_offset = (0, 0)

    def update(self, platforms):
        keys = pygame.key.get_pressed()

        # Управление движением (можно двигаться во время атаки, но не менять направление)
        moving = False
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            if not self.is_attacking:  # Нельзя менять направление во время атаки
                self.facing_right = False
            self.velocity_x = -self.speed
            moving = True
        elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            if not self.is_attacking:
                self.facing_right = True
            self.velocity_x = self.speed
            moving = True
        else:
            self.velocity_x *= self.friction

        # Атака по нажатию
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        if (keys[pygame.K_j] or keys[pygame.K_z] or keys[pygame.K_LCTRL]) and not self.is_attacking:
            if self.attack_cooldown <= 0:
                self._start_attack()

        # Проверяем окончание анимации атаки
        if self.is_attacking:
            current_anim = self.anim_manager.current_animation
            if current_anim and current_anim.finished:
                self.is_attacking = False
                self.attack_triggered = False
                # Возвращаемся к подходящей анимации
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

        # Меняем анимацию только если не атакуем или это принудительная смена
        if new_state != self.state:
            self.state = new_state
            if new_state == "attack":
                self.anim_manager.play("attack", force_restart=True)
            elif not self.is_attacking:  # Не переключаемся если атакуем
                self.anim_manager.play(new_state)

        # Прыжок (нельзя во время атаки)
        if not self.is_attacking and (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]) and self.on_ground:
            self.velocity_y = self.jump_power
            self.on_ground = False
            self._create_dust_particles()
            self.anim_manager.play("jump", force_restart=True)

        # Гравитация
        if not self.on_ground or self.velocity_y < 0:
            self.velocity_y += self.gravity

        # Применение скорости с проверкой коллизий
        self._move_with_collision(platforms)

        # Обновление анимации
        self.anim_manager.update()
        current_frame = self.anim_manager.get_current_frame()
        if current_frame:
            self.image = current_frame
            self._update_mask()

        # Выстрел происходит в середине анимации атаки (кадр 3-4)
        if self.is_attacking and not self.attack_triggered:
            current_anim = self.anim_manager.current_animation
            if current_anim and current_anim.current_frame == 3:  # середина анимации
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
        """Движение с проверкой коллизий по маске"""
        # Движение по X
        if self.velocity_x != 0:
            self.rect.x += self.velocity_x
            if USE_MASK_COLLISION:
                self._check_collision_mask(platforms, 'x')
            else:
                self._check_collision_rect(platforms, 'x')

        # Движение по Y
        if self.velocity_y != 0 or not self.on_ground:
            self.rect.y += self.velocity_y
            was_on_ground = self.on_ground
            self.on_ground = False

            if USE_MASK_COLLISION:
                self._check_collision_mask(platforms, 'y')
            else:
                self._check_collision_rect(platforms, 'y')

            if not was_on_ground and self.on_ground:
                self.rect.y -= self.ground_buffer

    def _check_collision_mask(self, platforms, direction):
        """Проверка коллизий с использованием масок"""
        for platform in platforms:
            if not self.rect.colliderect(platform.rect):
                continue

            offset = (
                platform.rect.x - self.rect.x - self.mask_offset[0],
                platform.rect.y - self.rect.y - self.mask_offset[1]
            )

            if platform.mask.overlap(self.mask, offset):
                if direction == 'x':
                    if self.velocity_x > 0:
                        self.rect.right = platform.rect.left
                    elif self.velocity_x < 0:
                        self.rect.left = platform.rect.right
                    self.velocity_x = 0
                    return

                elif direction == 'y':
                    if self.velocity_y > 0:
                        self.rect.bottom = platform.rect.top + self.ground_buffer
                        self.velocity_y = 0
                        self.on_ground = True
                    elif self.velocity_y < 0:
                        self.rect.top = platform.rect.bottom
                        self.velocity_y = 0
                    return

    def _check_collision_rect(self, platforms, direction):
        """Проверка коллизий прямоугольниками (fallback)"""
        hits = pygame.sprite.spritecollide(self, platforms, False)
        for platform in hits:
            if direction == 'x':
                if self.velocity_x > 0:
                    self.rect.right = platform.rect.left
                elif self.velocity_x < 0:
                    self.rect.left = platform.rect.right
                self.velocity_x = 0
            elif direction == 'y':
                if self.velocity_y > 0:
                    self.rect.bottom = platform.rect.top
                    self.velocity_y = 0
                    self.on_ground = True
                elif self.velocity_y < 0:
                    self.rect.top = platform.rect.bottom
                    self.velocity_y = 0

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