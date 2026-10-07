import shutil
from typing import Callable


from . import games
from .accounts import Account
from .config import Config
from .types import GameContext
from .utils import cprint, cinput, clear_screen, display_topbar, get_theme


from textual.app import App, ComposeResult
from textual.geometry import Offset
from textual.strip import Strip
from textual.widgets import Footer, Header, Input, Static, Button
from textual.containers import Center, Horizontal, Vertical, ItemGrid


TITLE_ART = """
┌┬─┬┬─┬┐    ┌┬─┬┐    ┌┬─┬┐     ┌┬─┬┬─┬┐    ┌┐    ┌┬─┬┐    ┌┬─┬┐    ┌┐           ┌┬─┬┐    ┌┬─┬┐    ┌┬─┬┐    ┌┐    ┌┬─┬┐    ┌┬─┬┐
└┘ ││ └┘    │├ └┘    │├─┴┼┐    ││ ││ ││    ││    ││ ││    │├─┤│    ││           ││ └┘    │├─┤│    └┴┐└┘    ││    ││ ││    ││ ││
   ││       ││ ┌┐    ││  ││    ││ └┘ ││    ││    ││ ││    ││ ││    ││ ┌┐        ││ ┌┐    ││ ││    ┌┐└┬┐    ││    ││ ││    ││ ││
   └┘       └┴─┴┘    └┘  └┘    └┘    └┘    └┘    └┘ └┘    └┘ └┘    └┴─┴┘        └┴─┴┘    └┘ └┘    └┴─┴┘    └┘    └┘ └┘    └┴─┴┘
"""
NAME_PLACEHOLDER = "Enter Your Name"


CASINO_HEADER = """
┌──────────────────────────────────────┐
│   ♦ T E R M I N A L  C A S I N O ♦   │
└──────────────────────────────────────┘
"""


CASINO_HEADER_OPTIONS = {
    "header": CASINO_HEADER,
    "margin": 3,
}
ACCOUNT_STARTING_BALANCE = 100


ENTER_OR_QUIT_PROMPT = "[E]nter   [Q]uit: "
INVALID_CHOICE_PROMPT = "\nInvalid input. Please try again.\n"
GAME_CHOICE_PROMPT = "Please choose a game to play: "


# To add a new game, just add a handler function to GAME_HANDLERS


GAME_HANDLERS: dict[str, Callable[[GameContext], None]] = {
    "blackjack (U.S.)": games.blackjack.play_blackjack,
    "blackjack (E.U.)": games.blackjack.play_european_blackjack,
    "slots": games.slots.play_slots,
    "slots (Expanded)": games.slots.play_slots_expanded,
    "poker": games.poker.play_poker,
    "roulette": games.roulette.play_roulette,
    "uno": games.uno.play_uno,
    "european roulette": games.roulette.play_european_roulette,
}
ALL_GAMES = list(GAME_HANDLERS.keys())


def term_width() -> int:
    """Safe terminal width fallback."""
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 80




def prompt_with_refresh(
    render_fn: Callable[[], None],
    prompt: str,
    error_message: str,
    validator: Callable[[str], bool],
    transform: Callable[[str], str] = lambda s: s.strip(),
) -> str:
    """
    Repeatedly render screen, show last error (if any), ask for input and validate.
    On EOF/KeyboardInterrupt return 'q' so caller can decide how to exit.
    """
    last_error = ""
    while True:
        render_fn()
        if last_error:
            cprint(last_error)
        answer = transform(cinput(prompt).strip())
        if validator(answer):
            return answer
        last_error = error_message


class CenteredInput(Input):
    def _left_pad(self) -> int:
        width = self.scrollable_content_region.width
        return max(0, (width - self.content_width) // 2)


    def render_line(self, y: int) -> Strip:
        strip = super().render_line(y)
        pad = self._left_pad()
        if y != 0 or not pad:
            return strip
        length = strip.cell_length
        shifted = Strip.join([Strip.blank(pad, self.rich_style), strip])
        return shifted.crop(0, length)


    @property
    def cursor_screen_offset(self) -> Offset:
        base = super().cursor_screen_offset
        return Offset(base.x + self._left_pad(), base.y)


    def _cell_offset_to_index(self, offset: int) -> int:
        return super()._cell_offset_to_index(offset - self._left_pad())




class titleScreen(App):


    CSS_PATH = "styles.tcss"


    def compose(self) -> ComposeResult:
        with Vertical(id="homeScreen"):
            with Center():
                yield Static(TITLE_ART, id="title")
            with Center():
                yield CenteredInput(
                    placeholder=NAME_PLACEHOLDER,
                    type="text",
                    id="name-input",
                    max_length=20
                )


    def on_input_submitted(self, event: Input.Submitted) -> None:
        name = event.value.strip()
   
        if name:
            self.exit(name)


class GameMenu(App):


    CSS_PATH = "styles.tcss"


    def __init__(self, player_name: str, balance: float) -> None:
        super().__init__()
        self.player_name = player_name
        self.balance = balance


    def compose(self) -> ComposeResult:
        with Vertical(id="menu-container"):
            with Center():
                with Vertical(id="menu-panel"):
                    with Horizontal(id="status-bar"):
                        yield Static(f"Balance: ${self.balance:,}", id="balance")
                        yield Static(self.player_name, id="player-name")
                    with ItemGrid(id="game-grid"):
                        for i, name in enumerate(ALL_GAMES, start=1):
                            row, col = divmod(i - 1, 4)
                            tile = "tile-red" if (row + col) % 2 == 0 else "tile-white"
                            yield Button(name.title(), id=f"g{i}", classes=tile)
            with Center():
                yield Button("Exit", id="exit")


    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.exit(str(event.button.id))


def main_menu(ctx: GameContext) -> None:
    account = ctx.account


    app = GameMenu(
        player_name=getattr(account, "name", ACCOUNT_STARTING_BALANCE),
        balance=getattr(account, "balance", ACCOUNT_STARTING_BALANCE)
    )


    selection = app.run()


    if selection == "exit":
        return


    choice = int(selection[1:])


    selected_game = ALL_GAMES[choice - 1]


    handler = GAME_HANDLERS.get(selected_game)


    if handler:
        clear_screen()
        handler(ctx)    




def main():
    name = ""
    app = titleScreen()
    name = app.run()


    account = Account.generate(name, ACCOUNT_STARTING_BALANCE)
    config = Config.default()
    ctx = GameContext(account=account, config=config)


    # theme selection
    # clear_screen()
    # display_topbar(account=None, **CASINO_HEADER_OPTIONS)
    # get_theme()

    while True:
        app = GameMenu(
            player_name=name,
            balance=getattr(account, "balance", ACCOUNT_STARTING_BALANCE),
        )
        selection = app.run()


        if selection == "exit":
            return


        choice = int(selection[1:])


        selected_game = ALL_GAMES[choice - 1]


        handler = GAME_HANDLERS.get(selected_game)


        if handler:
            clear_screen()
            handler(ctx)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        clear_screen()
        display_topbar(account=None, **CASINO_HEADER_OPTIONS)
        cprint("\nGoodbye! (Interrupted)\n")
