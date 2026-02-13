import pygame
from animation import AnimationManager
from settings import (NPC_BODY_COLOR, NPC_SKIN_COLOR, DIALOG_TRIGGER_DISTANCE,
                      DIALOG_TEXT_SPEED, DIALOG_BG, DIALOG_BORDER, DIALOG_TEXT,
                      WHITE, BLACK)


class NPC(pygame.sprite.Sprite):
    def __init__(self, x, y, assets_path=None, dialog_text=None):
        super().__init__()

        self.anim_manager = AnimationManager()
        self.assets_path = assets_path or "assets/npc"
        self._load_animations()

        self.image = self.anim_manager.get_current_frame()
        if not self.image:
            self.image = pygame.Surface((32, 48), pygame.SRCALPHA)

        self.rect = self.image.get_rect(topleft=(x, y))
        self._update_mask()

        # Диалог
        self.dialog_text = dialog_text or "Привет, путник! Я расскажу тебе историю этого мира..."
        self.dialog_shown = False
        self.dialog_active = False
        self.current_text = ""
        self.text_index = 0
        self.text_timer = 0
        self.dialog_finished = False

        # Облако диалога
        self.cloud_surface = None
        self.cloud_rect = None
        self.cloud_width = 400  # Увеличена ширина облака
        self.cloud_padding = 20  # Отступы внутри облака

    def _load_animations(self):
        """Загружает анимации NPC"""
        self.anim_manager.load_from_directory(self.assets_path, "idle", frame_duration=10, loop=True)

        if not self.anim_manager.animations:
            self._create_placeholder_animations()

        self.anim_manager.play("idle")

    def _create_placeholder_animations(self):
        """Создаёт заглушки если нет спрайтов"""
        frames = []
        for i in range(4):
            surface = pygame.Surface((32, 48), pygame.SRCALPHA)
            offset = i if i < 2 else 3 - i

            pygame.draw.ellipse(surface, NPC_BODY_COLOR, (4 + offset, 16, 24 - offset * 2, 32))
            pygame.draw.circle(surface, NPC_SKIN_COLOR, (16, 12), 10)
            pygame.draw.circle(surface, (50, 50, 50), (14, 10), 2)
            pygame.draw.circle(surface, (50, 50, 50), (20, 10), 2)
            frames.append(surface)

        self.anim_manager.add_animation("idle", frames, frame_duration=10, loop=True)

    def _update_mask(self):
        """Создаёт маску коллизии"""
        bbox = self.image.get_bounding_rect()
        if bbox.width > 0 and bbox.height > 0:
            trimmed = self.image.subsurface(bbox)
            self.mask = pygame.mask.from_surface(trimmed)
            self.mask_offset = (bbox.x, bbox.y)
        else:
            self.mask = pygame.mask.from_surface(self.image)
            self.mask_offset = (0, 0)

    def update(self, player):
        """Обновляет NPC и проверяет диалог"""
        distance = pygame.math.Vector2(
            self.rect.centerx - player.rect.centerx,
            self.rect.centery - player.rect.centery
        ).length()

        # Активация диалога при приближении (1 раз за игру)
        if distance < DIALOG_TRIGGER_DISTANCE and not self.dialog_shown and not self.dialog_active:
            self._start_dialog()

        # Обновление диалога
        if self.dialog_active:
            self._update_dialog()

        # Анимация
        self.anim_manager.update()
        current_frame = self.anim_manager.get_current_frame()
        if current_frame:
            self.image = current_frame
            self._update_mask()

    def _start_dialog(self):
        """Начинает диалог"""
        self.dialog_active = True
        self.current_text = ""
        self.text_index = 0
        self.text_timer = 0
        self.dialog_finished = False

    def _update_dialog(self):
        """Обновляет текст диалога (печатание)"""
        self.text_timer += 1

        if self.text_timer >= DIALOG_TEXT_SPEED and self.text_index < len(self.dialog_text):
            self.current_text += self.dialog_text[self.text_index]
            self.text_index += 1
            self.text_timer = 0
            self._render_cloud()

        if self.text_index >= len(self.dialog_text):
            self.dialog_finished = True

    def _render_cloud(self):
        """Рендерит облако диалога с автопереносом текста"""
        font = pygame.font.Font(None, 24)
        max_text_width = self.cloud_width - self.cloud_padding * 2

        # Разбиваем текст на строки с учётом ширины
        words = self.current_text.split(' ')
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + word + " "
            test_width = font.size(test_line)[0]

            if test_width <= max_text_width:
                current_line = test_line
            else:
                # Если слово не помещается вообще, разбиваем его
                if current_line == "":
                    # Длинное слово — разбиваем посимвольно
                    for char in word:
                        test_line = current_line + char
                        if font.size(test_line)[0] <= max_text_width:
                            current_line = test_line
                        else:
                            lines.append(current_line)
                            current_line = char
                    current_line += " "
                else:
                    lines.append(current_line)
                    current_line = word + " "

        lines.append(current_line)

        # Размеры облака
        line_height = font.get_height() + 2  # +2 для межстрочного интервала
        text_height = len(lines) * line_height
        cloud_height = max(60, text_height + self.cloud_padding * 2)

        # Создаём поверхность
        self.cloud_surface = pygame.Surface((self.cloud_width, cloud_height), pygame.SRCALPHA)

        # Фон (облако с закруглениями)
        corner_radius = 20
        pygame.draw.rect(self.cloud_surface, DIALOG_BG,
                         (0, 0, self.cloud_width, cloud_height),
                         border_radius=corner_radius)
        pygame.draw.rect(self.cloud_surface, DIALOG_BORDER,
                         (0, 0, self.cloud_width, cloud_height),
                         width=2, border_radius=corner_radius)

        # Хвостик облака (треугольник снизу)
        tail_width = 20
        tail_height = 15
        tail_x = self.cloud_width // 2 - tail_width // 2
        tail_y = cloud_height - 2

        points = [
            (tail_x, tail_y),
            (tail_x + tail_width // 2, tail_y + tail_height),
            (tail_x + tail_width, tail_y)
        ]
        pygame.draw.polygon(self.cloud_surface, DIALOG_BG, points)
        pygame.draw.polygon(self.cloud_surface, DIALOG_BORDER, points, 2)

        # Текст
        y_offset = self.cloud_padding
        for line in lines:
            text_surface = font.render(line.rstrip(), True, DIALOG_TEXT)
            self.cloud_surface.blit(text_surface, (self.cloud_padding, y_offset))
            y_offset += line_height

        # Позиция над NPC (центрируем)
        self.cloud_rect = self.cloud_surface.get_rect()
        self.cloud_rect.centerx = self.rect.centerx
        self.cloud_rect.bottom = self.rect.top - 10

    def close_dialog(self):
        """Закрывает диалог (вызывается при нажатии клавиши)"""
        if self.dialog_finished:
            self.dialog_active = False
            self.dialog_shown = True

    def is_blocking(self):
        """Возвращает True если NPC блокирует движение игрока"""
        return self.dialog_active and not self.dialog_finished

    def draw(self, surface, camera_x, camera_y=0):
        # Рисуем NPC
        surface.blit(self.image, (self.rect.x - camera_x, self.rect.y - camera_y))

        # Рисуем облако диалога
        if self.dialog_active and self.cloud_surface:
            # Проверяем что облако в пределах экрана
            if (self.cloud_rect.right - camera_x > 0 and
                    self.cloud_rect.left - camera_x < surface.get_width()):
                surface.blit(self.cloud_surface,
                             (self.cloud_rect.x - camera_x,
                              self.cloud_rect.y - camera_y))

        # Индикатор "!" если можно поговорить
        if not self.dialog_shown and not self.dialog_active:
            distance_indicator = pygame.Surface((20, 20), pygame.SRCALPHA)
            pygame.draw.circle(distance_indicator, (255, 255, 0), (10, 10), 8)
            pygame.draw.circle(distance_indicator, (0, 0, 0), (10, 10), 8, 2)
            font = pygame.font.Font(None, 20)
            text = font.render("!", True, (0, 0, 0))
            distance_indicator.blit(text, (7, 4))

            indicator_rect = distance_indicator.get_rect()
            indicator_rect.centerx = self.rect.centerx
            indicator_rect.bottom = self.rect.top - 5

            surface.blit(distance_indicator,
                         (indicator_rect.x - camera_x,
                          indicator_rect.y - camera_y))