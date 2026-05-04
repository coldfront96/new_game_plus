import pygame
import sys
import time
import random
import subprocess
import os

pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 1280, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Echoes of the Infinite - Boot Sequence")

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
font_manifesto = pygame.font.SysFont("courier", 24, bold=True)
font_title = pygame.font.SysFont("georgia", 80, bold=True)
font_button = pygame.font.SysFont("courier", 32)

class DustMote:
    def __init__(self):
        self.x = random.randint(WIDTH//2 - 250, WIDTH//2 + 250)
        self.y = random.randint(0, HEIGHT)
        self.speed_y = random.uniform(0.1, 0.6)
        self.speed_x = random.uniform(-0.2, 0.2)
        self.radius = random.uniform(0.8, 2.5)
        self.alpha = random.randint(50, 200)

    def update(self):
        self.y += self.speed_y
        self.x += self.speed_x
        self.alpha += random.randint(-10, 10)
        self.alpha = max(30, min(255, self.alpha))
        if self.y > HEIGHT:
            self.y = random.randint(-50, -10)
            self.x = random.randint(WIDTH//2 - 250, WIDTH//2 + 250)

    def draw(self, surface):
        temp_surface = pygame.Surface((int(self.radius*2), int(self.radius*2)), pygame.SRCALPHA)
        pygame.draw.circle(temp_surface, (255, 255, 255, self.alpha), (int(self.radius), int(self.radius)), self.radius)
        surface.blit(temp_surface, (int(self.x), int(self.y)))

motes = [DustMote() for _ in range(80)]

manifesto_text = (
    "This world has no invisible walls. It has no pre-written scripts.\n"
    "The engine responds only to the limits of your imagination.\n"
    "If you can dream it, the dice will let you attempt it.\n\n"
    "Welcome to your new reality."
)

def typewriter_effect(text, font, surface, x, y, speed=0.04):
    lines = text.split('\n')
    current_y = y
    for line in lines:
        rendered_text = ""
        for char in line:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
            rendered_text += char
            text_surface = font.render(rendered_text, True, WHITE)
            pygame.draw.rect(surface, BLACK, (x, current_y, WIDTH, 40))
            surface.blit(text_surface, (x, current_y))
            pygame.display.flip()
            time.sleep(speed)
        current_y += 35

def main_menu():
    try:
        bg_image = pygame.image.load("assets/bg.png").convert()
        bg_image = pygame.transform.scale(bg_image, (WIDTH, HEIGHT))
    except FileNotFoundError:
        print("SYSTEM WARNING: assets/bg.png not found. Falling back to black void.")
        bg_image = pygame.Surface((WIDTH, HEIGHT))
        bg_image.fill(BLACK)

    screen.fill(BLACK)
    pygame.display.flip()
    time.sleep(1)

    typewriter_effect(manifesto_text, font_manifesto, screen, 100, 200)
    time.sleep(3)

    screen.fill(BLACK)
    pygame.display.flip()
    time.sleep(1)

    try:
        # Changed to .ogg to respect your compression pipeline!
        pygame.mixer.music.load("assets/elven_duet.ogg")
        pygame.mixer.music.play(-1)
    except FileNotFoundError:
        print("SYSTEM WARNING: assets/elven_duet.ogg not found. Continuing in silence.")

    title_surface = font_title.render("ECHOES OF THE INFINITE", True, WHITE)
    button_surface = font_button.render("[ Press ENTER to Awaken ]", True, WHITE)

    title_rect = title_surface.get_rect(center=(WIDTH//2, HEIGHT//2 - 80))
    button_rect = button_surface.get_rect(center=(WIDTH//2, HEIGHT//2 + 120))

    clock = pygame.time.Clock()

    for alpha in range(0, 256, 2):
        screen.blit(bg_image, (0, 0))
        for mote in motes:
            mote.update()
            mote.draw(screen)

        title_surface.set_alpha(alpha)
        button_surface.set_alpha(alpha)
        screen.blit(title_surface, title_rect)
        screen.blit(button_surface, button_rect)
        pygame.display.flip()
        clock.tick(60)

    waiting_for_input = True
    while waiting_for_input:
        screen.blit(bg_image, (0, 0))
        for mote in motes:
            mote.update()
            mote.draw(screen)

        screen.blit(title_surface, title_rect)
        screen.blit(button_surface, button_rect)
        pygame.display.flip()
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    waiting_for_input = False

    pygame.mixer.music.stop()

    try:
        # Changed to .ogg here as well!
        iron_door = pygame.mixer.Sound("assets/iron_door.ogg")
        iron_door.play()
    except FileNotFoundError:
        print("SYSTEM WARNING: assets/iron_door.ogg not found.")

    screen.fill(WHITE)
    pygame.display.flip()
    time.sleep(0.15)

    screen.fill(BLACK)
    pygame.display.flip()
    time.sleep(1)

    print("TRANSITION TO TERMINAL ENGINE INITIALIZED...")
    pygame.quit()

    # Hand-off to the main terminal application
    subprocess.run([sys.executable, "-m", "new_game_plus"])
    sys.exit()

if __name__ == "__main__":
    main_menu()
