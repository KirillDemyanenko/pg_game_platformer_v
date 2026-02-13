import pygame
import sys
import os
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, DEFAULT_MAP
from game import Game


def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Pygame Platformer")
    clock = pygame.time.Clock()

    # Автоматическая загрузка карты из assets/maps/map.tmx
    game = Game()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_r:
                    # Перезагрузка текущей карты
                    game.reload_map()
                if event.key == pygame.K_F5:  # Исправлено: K_F5 вместо K_f5
                    # Принудительная перезагрузка из map.tmx
                    if os.path.exists(DEFAULT_MAP):
                        game.load_tmx_map(DEFAULT_MAP)
                    else:
                        game._create_demo_level()

        game.update()
        game.draw(screen, clock)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()