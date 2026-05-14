"""Demo for stochastic splash design options for RLM.

Companion to the splash-design discussion issue. Run:

    python demo_splash.py            # one example of every option
    python demo_splash.py --seed 42  # reproducible run
    python demo_splash.py --layered  # only the three layered tunings

Five options are presented:

    1. mask + random fill character    (same shape, one fill char varies)
    2. per-cell jitter                  (same shape, char varies per cell)
    3. pre-designed font pool           (pick from a small library of banners)
    4. pyfiglet with a random font      (requires `pip install pyfiglet`)
    5. glitch overlay                   (perturb cells from a clean render)

Plus a layered combination shown at three tunings.

Each call re-randomizes, so re-running shows new variations.
"""

import argparse
import random


# Hand-laid 6-row mask for "RLM". 'X' = filled, ' ' = background.
# Block geometry: R (6 cols) + 2-col gap + L (6 cols) + 2-col gap + M (7 cols) = 23 cols.
RLM_MASK = """\
XXXXX   X       X     X
X    X  X       XX   XX
XXXXX   X       X X X X
X  X    X       X  X  X
X   X   X       X     X
X    X  XXXXXX  X     X
"""


def _mask_grid() -> list[list[bool]]:
    return [[c == "X" for c in line] for line in RLM_MASK.strip("\n").splitlines()]


def _render(grid: list[list[bool]], fill: str, bg: str) -> str:
    return "\n".join("".join(fill if c else bg for c in row) for row in grid)


# ---------------------------------------------------------------------------
# Option 1: Mask + random fill character
# ---------------------------------------------------------------------------

_FILL_POOL = ["#", "█", "▓", "▒", "░", "▀", "■", "●", "*", "♟"]


def option_1_random_fill() -> str:
    fill = random.choice(_FILL_POOL)
    return _render(_mask_grid(), fill, " ")


# ---------------------------------------------------------------------------
# Option 2: Per-cell jitter
# ---------------------------------------------------------------------------

# Weighted by listing more copies of the dominant char.
_JITTER_FILL = ["█", "█", "█", "█", "█", "▓", "▒", "▀"]
_JITTER_BG = [" "] * 20 + [".", "·"]


def option_2_per_cell_jitter() -> str:
    grid = _mask_grid()
    rows = []
    for row in grid:
        rows.append("".join(
            random.choice(_JITTER_FILL) if cell else random.choice(_JITTER_BG)
            for cell in row
        ))
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# Option 3: Pre-designed font pool
# ---------------------------------------------------------------------------

_BANNERS = [
    # block letters
    r"""
 _____  _      __  __
|  __ \| |    |  \/  |
| |__) | |    | \  / |
|  _  /| |    | |\/| |
| | \ \| |____| |  | |
|_|  \_\______|_|  |_|
""",
    # solid heavy
    r"""
██████╗ ██╗     ███╗   ███╗
██╔══██╗██║     ████╗ ████║
██████╔╝██║     ██╔████╔██║
██╔══██╗██║     ██║╚██╔╝██║
██║  ██║███████╗██║ ╚═╝ ██║
╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝
""",
    # tile letters
    r"""
.------..------..------.
|R.--. ||L.--. ||M.--. |
| :(): || :/\: || (\/) |
| ()() || (__) || :\/: |
| '--'R|| '--'L|| '--'M|
`------'`------'`------'
""",
    # thin / pixel
    r"""
▄▀▀▀▄ █     █▄ ▄█
█▄▄▄▀ █     █ ▀ █
█  █  █     █   █
█   █ █▄▄▄  █   █
""",
]


def option_3_font_pool() -> str:
    return random.choice(_BANNERS).strip("\n")


# ---------------------------------------------------------------------------
# Option 4: Pyfiglet random font
# ---------------------------------------------------------------------------

_PYFIGLET_FONTS = [
    "banner", "big", "block", "bubble", "digital", "lean", "mini",
    "script", "shadow", "slant", "small", "smscript", "smshadow",
    "smslant", "speed", "standard",
]


def option_4_pyfiglet() -> str:
    try:
        import pyfiglet
    except ImportError:
        return "(pyfiglet not installed — `pip install pyfiglet` to see this option)"
    font = random.choice(_PYFIGLET_FONTS)
    return f"[font: {font}]\n" + pyfiglet.figlet_format("RLM", font=font).rstrip()


# ---------------------------------------------------------------------------
# Option 5: Glitch overlay
# ---------------------------------------------------------------------------

def option_5_glitch(base: str | None = None, p: float = 0.10) -> str:
    if base is None:
        base = _render(_mask_grid(), "█", " ")
    out_chars = []
    for c in base:
        if c == "\n":
            out_chars.append(c)
        elif c != " " and random.random() < p:
            out_chars.append(random.choice(["▒", "░", " ", "·"]))
        elif c == " " and random.random() < p * 0.4:
            out_chars.append(random.choice(["·", "."]))
        else:
            out_chars.append(c)
    return "".join(out_chars)


# ---------------------------------------------------------------------------
# Layered combination
# ---------------------------------------------------------------------------

def layered(
    jitter_density: float = 0.30,
    drop_density: float = 0.06,
    bg_noise: float = 0.06,
) -> str:
    """Layer per-cell jitter + glitch drops + faint background noise over a
    pre-designed banner base.

    Each call randomly picks one banner from the pre-designed pool (Option 3)
    and then perturbs it cell-by-cell. Original banner characters are kept
    most of the time, so each font's character is preserved; jittered cells
    are swapped to lighter block glyphs.

    jitter_density: probability a filled cell is swapped to a lighter glyph.
    drop_density:   probability a filled cell is dropped to space.
    bg_noise:       probability a background space shows a faint mark.
    """
    base = random.choice(_BANNERS).strip("\n")
    out: list[str] = []
    for c in base:
        if c == "\n":
            out.append(c)
        elif c == " ":
            out.append(random.choice(["·", ".", "•"]) if random.random() < bg_noise else " ")
        else:
            r = random.random()
            if r < drop_density:
                out.append(" ")
            elif r < drop_density + jitter_density:
                out.append(random.choice(["▓", "▒", "░"]))
            else:
                out.append(c)
    return "".join(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

N_SAMPLES = 5


def _hr(title: str) -> str:
    return f"\n{'=' * 60}\n{title}\n{'=' * 60}\n"


def _print_samples(title: str, fn, n: int = N_SAMPLES) -> None:
    """Print n variations of fn() under a single section header."""
    print(_hr(title))
    for i in range(1, n + 1):
        print(f"-- sample {i}/{n} --")
        print(fn())
        print()


def print_all_options() -> None:
    _print_samples("Option 1: mask + random fill character", option_1_random_fill)
    _print_samples("Option 2: per-cell jitter", option_2_per_cell_jitter)
    _print_samples("Option 3: pre-designed font pool", option_3_font_pool)
    _print_samples("Option 4: pyfiglet with a random font", option_4_pyfiglet)
    _print_samples("Option 5: glitch overlay", option_5_glitch)


def print_layered_tunings() -> None:
    tunings = [
        ("subtle", dict(jitter_density=0.10, drop_density=0.0, bg_noise=0.02)),
        ("medium", dict(jitter_density=0.30, drop_density=0.06, bg_noise=0.06)),
        ("heavy", dict(jitter_density=0.40, drop_density=0.10, bg_noise=0.10)),
    ]
    print(_hr("Layered (base = pre-designed banner), three tunings"))
    for name, params in tunings:
        params_str = ", ".join(f"{k.split('_')[0]}={v}" for k, v in params.items())
        print(f"### {name}  ({params_str}) ###")
        for i in range(1, N_SAMPLES + 1):
            print(f"-- sample {i}/{N_SAMPLES} --")
            print(layered(**params))
            print()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--seed", type=int, default=None, help="seed RNG for reproducible output")
    p.add_argument("--layered", action="store_true", help="only show the layered tunings")
    args = p.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    if args.layered:
        print_layered_tunings()
    else:
        print_all_options()
        print_layered_tunings()


if __name__ == "__main__":
    main()
