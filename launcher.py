import pygame
import sys
import time
import random
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

def pygame_intro():
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

    # 5. THE INTERACTIVE DROP (The Abyssal Iron Vault)
    pygame.mixer.music.stop()

    try:
        iron_door = pygame.mixer.Sound("assets/iron_door.ogg")
        # Start the sound
        iron_door.play()

        # --- THE FIX: WAIT FOR THE ECHO ---
        # Get the length of the audio in seconds
        sound_length = iron_door.get_length()

        # Blinding White Flash
        screen.fill(WHITE)
        pygame.display.flip()
        time.sleep(0.15)

        # Back to black while the sound finishes
        screen.fill(BLACK)
        pygame.display.flip()

        # Wait for the remaining duration of the sound plus a tiny buffer for the echo
        time.sleep(sound_length - 0.15 + 0.5)

    except FileNotFoundError:
        print("SYSTEM WARNING: assets/iron_door.ogg not found.")


# ---------------------------------------------------------------------------
# Textual Main Menu
# ---------------------------------------------------------------------------

from typing import Optional, Tuple
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Button, Header, Footer, Static
from pathlib import Path

_REPO_ROOT = Path(__file__).parent
_PLAYER_JSON = _REPO_ROOT / "data" / "player.json"

# Difficulty definitions: name -> (pool_min, pool_max, permadeath)
_DIFFICULTIES = {
    "Easy":          (35, 45, False),
    "Medium":        (25, 35, False),
    "Hard":          (20, 30, False),
    "The Iron Path": (20, 30, True),
}


class DifficultySelectorScreen(App[Optional[Tuple[str, int, bool]]]):
    """Modal Textual app for choosing difficulty and rolling the stat pool."""

    TITLE = "ASHEN CROSSROADS  ·  Choose Your Trial"

    CSS = """
    Screen {
        background: #0d0d0d;
        align: center middle;
    }
    #diff-container {
        width: 60;
        border: solid #3d2b15;
        padding: 1 2;
    }
    #diff-title {
        height: 1;
        background: #1c0f00;
        color: #c89b5f;
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    #diff-subtitle {
        color: #7a5a30;
        margin-bottom: 1;
        text-align: center;
    }
    .diff-btn {
        width: 100%;
        margin-bottom: 1;
        background: #1c0800;
        color: #e8d5a0;
        border: solid #3d2b15;
    }
    .diff-btn:hover {
        background: #3d2b15;
        color: #c89b5f;
    }
    #btn-iron-path {
        color: #ff6b6b;
        border: solid #8b0000;
    }
    #btn-iron-path:hover {
        background: #8b0000;
        color: #fff;
    }
    #btn-back {
        width: 100%;
        background: #0a0a0a;
        color: #7a5a30;
        border: solid #3d2b15;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Vertical(id="diff-container"):
            yield Static("⚔  SELECT YOUR TRIAL", id="diff-title")
            yield Static(
                "Your chosen trial determines the size of your Awakening Pool.",
                id="diff-subtitle",
            )
            yield Button("☀  Easy          [Pool: 35–45]", id="btn-easy",      classes="diff-btn")
            yield Button("⚖  Medium        [Pool: 25–35]", id="btn-medium",    classes="diff-btn")
            yield Button("💀 Hard          [Pool: 20–30]", id="btn-hard",       classes="diff-btn")
            yield Button("🩸 The Iron Path [Pool: 20–30 + Permadeath]", id="btn-iron-path", classes="diff-btn")
            yield Button("← Back",                        id="btn-back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-back":
            self.exit(result=None)
            return
        difficulty_map = {
            "btn-easy":      "Easy",
            "btn-medium":    "Medium",
            "btn-hard":      "Hard",
            "btn-iron-path": "The Iron Path",
        }
        if btn_id in difficulty_map:
            diff_name = difficulty_map[btn_id]
            pool_min, pool_max, permadeath = _DIFFICULTIES[diff_name]
            pool_size = random.randint(pool_min, pool_max)
            self.exit(result=(diff_name, pool_size, permadeath))


class MainMenuApp(App[Optional[Tuple[str, int, bool]]]):
    """Textual Main Menu — entry point after the Pygame intro sequence."""

    TITLE = "ASHEN CROSSROADS  ·  Main Menu"

    CSS = """
    Screen {
        background: #0d0d0d;
        align: center middle;
    }
    #menu-container {
        width: 50;
        border: solid #3d2b15;
        padding: 1 2;
    }
    #menu-title {
        height: 1;
        background: #1c0f00;
        color: #c89b5f;
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    .menu-btn {
        width: 100%;
        margin-bottom: 1;
        background: #1c0800;
        color: #e8d5a0;
        border: solid #3d2b15;
    }
    .menu-btn:hover {
        background: #3d2b15;
        color: #c89b5f;
    }
    .menu-btn:disabled {
        color: #3d2b15;
        background: #0a0a0a;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Vertical(id="menu-container"):
            yield Static("⚡  ECHOES OF THE INFINITE", id="menu-title")
            continue_disabled = not _PLAYER_JSON.exists()
            yield Button(
                "▶  Continue",
                id="btn-continue",
                classes="menu-btn",
                disabled=continue_disabled,
            )
            yield Button("✦  New Game",   id="btn-new-game", classes="menu-btn")
            yield Button("⚙  Settings",   id="btn-settings", classes="menu-btn", disabled=True)
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-continue":
            # Signal caller to continue with existing player
            self.exit(result=("__continue__", 0, False))
        elif btn_id == "btn-new-game":
            # Launch difficulty selector as a nested Textual app
            diff_app = DifficultySelectorScreen()
            result = diff_app.run()
            if result is not None:
                self.exit(result=result)
            # else: user pressed Back, stay on main menu (do nothing)
        elif btn_id == "btn-settings":
            pass  # Placeholder — settings not yet implemented


if __name__ == "__main__":
    pygame_intro()

    # Tear down Pygame before handing off to the terminal-based UI.
    pygame.quit()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    # ── Textual Main Menu ────────────────────────────────────────────────────
    menu = MainMenuApp()
    menu_result = menu.run()

    if menu_result is None:
        # User closed the menu without making a selection — exit cleanly.
        sys.exit(0)

    difficulty_name, pool_size, permadeath = menu_result

    if difficulty_name == "__continue__":
        # Load existing save and drop into the game (forge skipped).
        from rich.console import Console
        Console().print("\n[bold #c89b5f]▶  Resuming your chronicle…[/bold #c89b5f]\n")
        sys.exit(0)

    # ── Character Forge (New Game path) ─────────────────────────────────────
    from src.game.character_forge import CharacterForgeApp
    from rich.console import Console

    forge = CharacterForgeApp(
        difficulty=difficulty_name,
        pool_size=pool_size,
        permadeath=permadeath,
    )
    result = forge.run()

    console = Console()
    if result is not None:
        console.print(
            f"\n[bold #c89b5f]⚡  {result['name']} awakens from the Ashen Crossroads.[/bold #c89b5f]"
        )
        console.print(
            f"   [dim]{result['race']} {result['char_class']}  ·  "
            f"HP {result['hit_points']}  ·  "
            f"AC {result['armor_class']}  ·  "
            f"BAB +{result['base_attack_bonus']}[/dim]"
        )
        console.print(
            f"   [dim]Difficulty: {result.get('difficulty', 'Unknown')}  ·  "
            f"Pool: {result.get('starting_pool', '?')}  ·  "
            f"Permadeath: {result.get('permadeath_status', False)}[/dim]"
        )
        console.print("   [dim]Saved → data/player.json[/dim]\n")
    else:
        console.print("\n[dim]Character Forge closed without saving.[/dim]\n")
