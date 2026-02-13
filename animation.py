import pygame
import os
from pathlib import Path


class Animation:
    def __init__(self, frames, frame_duration=5, loop=True):
        self.frames = frames  # список изображений
        self.frame_duration = frame_duration  # кадров на один спрайт
        self.loop = loop
        self.current_frame = 0
        self.timer = 0
        self.finished = False

    def update(self):
        if self.finished and not self.loop:
            return

        self.timer += 1
        if self.timer >= self.frame_duration:
            self.timer = 0
            self.current_frame += 1

            if self.current_frame >= len(self.frames):
                if self.loop:
                    self.current_frame = 0
                else:
                    self.current_frame = len(self.frames) - 1
                    self.finished = True

    def get_current_frame(self):
        return self.frames[self.current_frame]

    def reset(self):
        self.current_frame = 0
        self.timer = 0
        self.finished = False


class AnimationManager:
    def __init__(self):
        self.animations = {}
        self.current_animation = None
        self.current_name = ""

    def add_animation(self, name, frames, frame_duration=5, loop=True):
        self.animations[name] = Animation(frames, frame_duration, loop)

    def play(self, name, force_restart=False):
        if name == self.current_name and not force_restart:
            return

        if name in self.animations:
            self.current_name = name
            self.current_animation = self.animations[name]
            self.current_animation.reset()

    def update(self):
        if self.current_animation:
            self.current_animation.update()

    def get_current_frame(self):
        if self.current_animation:
            return self.current_animation.get_current_frame()
        return None

    def load_from_directory(self, base_path, animation_name, frame_duration=5, loop=True):
        """Загружает анимацию из папки с изображениями"""
        frames = []
        path = Path(base_path) / animation_name

        if not path.exists():
            print(f"Папка не найдена: {path}")
            return

        # Сортируем файлы по имени
        files = sorted([f for f in path.iterdir() if f.suffix in ['.png', '.jpg', '.bmp']])

        for file in files:
            try:
                image = pygame.image.load(str(file)).convert_alpha()
                frames.append(image)
            except pygame.error as e:
                print(f"Ошибка загрузки {file}: {e}")

        if frames:
            self.add_animation(animation_name, frames, frame_duration, loop)
            print(f"Загружена анимация '{animation_name}': {len(frames)} кадров")
        else:
            print(f"Нет изображений в {path}")