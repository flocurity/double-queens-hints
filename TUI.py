"""Visual scratchpad for terminal renderer experiments.

Intentionally contains rejected rendering variants.
Not production code.
A lot of copy paste - multiple imports intended
"""


from rich.console import Console
from rich.text import Text

console = Console()

# Petite grille de démonstration.
# Chaque lettre = une région.
regions = [
    "AAABBBCCC",
    "AAABBBBCC",
    "DAABBBCCC",
    "DAAAAEECF",
    "DGAAEEEFF",
    "DGGGGEFFF",
    "DDDGGEFFI",
    "HHHHHEEII",
    "HHEEEEIII",
]

# Q = queen, X = excluded, . = unknown
state = [
    ".........",
    "....X.X..",
    ".........",
    "XXX...X..",
    "XQX...X..",
    "XXXX.....",
    ".XQXXX...",
    ".XXXQXXX.",
    "...XXX...",
]

colors = {
    "A": "#b94a48",
    "B": "#3977b8",
    "C": "#4f914c",
    "D": "#c69b32",
    "E": "#8759a6",
    "F": "#d47a38",
    "G": "#795548",
    "H": "#4b9ca8",
    "I": "#777777",
}

symbols = {
    ".": " ",
    "X": "×",
    "Q": "♛",
}

console.print()

header = Text("        ")
for col in range(1, 10):
    header.append(f" {col} ")
console.print(header)

for row, (region_row, state_row) in enumerate(zip(regions, state), start=1):
    line = Text(f"Line {row:02d} ")

    for region, cell in zip(region_row, state_row):
        symbol = symbols[cell]

        line.append(
            f" {symbol} ",
            style=f"bold white on {colors[region]}",
        )

    console.print(line)

console.print()


console.print()

header = Text("        ")
for col in range(1, 10):
    header.append(f" {col} ")
console.print(header)

for row, (region_row, state_row) in enumerate(zip(regions, state), start=1):
    # Fine séparation horizontale au-dessus de chaque case.
    separator = Text("        ")
    for region in region_row:
        separator.append(
            "▔▔▔",
            style=f"#303030 on {colors[region]}",
        )

    # Pas de séparateur avant la première ligne.
    if row > 1:
        console.print(separator)

    line = Text(f"Line {row:02d} ")

    for region, cell in zip(region_row, state_row):
        line.append(
            f"▏{symbols[cell]} ",
            style=f"bold white on {colors[region]}",
        )

    console.print(line)


console.print()

header = Text("        ")
for col in range(1, 10):
    header.append(f" {col} ")
console.print(header)

for row, (region_row, state_row) in enumerate(zip(regions, state), start=1):
    if row > 1:
        console.print(Text("        " + " " * (len(region_row) * 4 - 1)))

    line = Text(f"Line {row:02d} ")

    for col, (region, cell) in enumerate(zip(region_row, state_row)):
        if col > 0:
            line.append(" ")

        line.append(
            f" {symbols[cell]} ",
            style=f"bold white on {colors[region]}",
        )

    console.print(line)


console.print()

header = Text("        ")
for col in range(1, 10):
    header.append(f" {col} ")
console.print(header)

for row, (region_row, state_row) in enumerate(zip(regions, state), start=1):
    if row > 1:
        separator = Text("        ")

        for col, region in enumerate(region_row):
            if col > 0:
                separator.append(" ")

            separator.append(
                "▔▔▔",
                style=f"#303030 on {colors[region]}",
            )

        console.print(separator)

    line = Text(f"Line {row:02d} ")

    for col, (region, cell) in enumerate(zip(region_row, state_row)):
        if col > 0:
            line.append(" ")

        line.append(
            f" {symbols[cell]} ",
            style=f"bold white on {colors[region]}",
        )

    console.print(line)


console.print()

header = Text("        ")
for col in range(1, 10):
    header.append(f" {col} ")
console.print(header)

for row, (region_row, state_row) in enumerate(zip(regions, state), start=1):
    if row > 1:
        separator = Text("        ")

        for region in region_row:
            separator.append(
                "▔▔▔",
                style=f"#2b2b2b on {colors[region]}",
            )

        console.print(separator)

    line = Text(f"Line {row:02d} ")

    for region, cell in zip(region_row, state_row):
        line.append(
            f"▏{symbols[cell]} ",
            style=f"bold white on {colors[region]}",
        )

    console.print(line)


console.print()
console.print()

for separator_char in ("▏", "╎", "┊"):
    console.print(f"\n[bold]{separator_char!r}[/bold]")

    header = Text("        ")
    for col in range(1, 10):
        header.append(f" {col} ")
    console.print(header)

    for row, (region_row, state_row) in enumerate(
        zip(regions, state),
        start=1,
    ):
        line = Text(f"Line {row:02d} ")

        for region, cell in zip(region_row, state_row):
            bg = colors[region]

            line.append(
                separator_char,
                style=f"#303030 on {bg}",
            )
            line.append(
                f"{symbols[cell]} ",
                style=f"bold white on {bg}",
            )

        console.print(line)


console.print()

from rich.console import Console
from rich.text import Text

console = Console()

separator_color = "#303030"

header = Text("        ")
for col in range(1, 10):
    header.append(f" {col} ")
console.print(header)

for row, (region_row, state_row) in enumerate(
    zip(regions, state),
    start=1,
):
    # Fine frontière horizontale.
    if row > 1:
        border = Text("        ")

        for region in region_row:
            bg = colors[region]
            border.append(
                "▔▔▔",
                style=f"{separator_color} on {bg}",
            )

        console.print(border)

    line = Text(f"Line {row:02d} ")

    for region, cell in zip(region_row, state_row):
        bg = colors[region]

        # Fine frontière verticale.
        line.append(
            "▏",
            style=f"{separator_color} on {bg}",
        )

        # Contenu.
        line.append(
            "▏",
            style=f"{separator_color} on {bg}",
        )

        cell_text = Text(
            f"{symbols[cell]} ",
            style=f"bold white on {bg}",
        )

        cell_text.stylize(f"underline {separator_color}")

        line.append(cell_text)

    console.print(line)

########

from rich.console import Console
from rich.text import Text

console = Console()

separator_color = "#303030"

header = Text("        ")
for col in range(1, 10):
    header.append(f" {col} ")
console.print(header)

for row, (region_row, state_row) in enumerate(
    zip(regions, state),
    start=1,
):
    # Ligne horizontale fine entre deux rangées.
    if row > 1:
        separator = Text("        ")

        for region in region_row:
            bg = colors[region]

        separator.append(
            "▁▁▁",
            style=f"{separator_color} on {bg}",
        )

        console.print(separator)

    line = Text(f"Line {row:02d} ")

    for region, cell in zip(region_row, state_row):
        bg = colors[region]

        # Séparateur vertical fin.
        line.append(
            "▏",
            style=f"{separator_color} on {bg}",
        )

        # Contenu de la case.
        line.append(
            f"{symbols[cell]} ",
            style=f"bold white on {bg}",
        )

    console.print(line)


###########

#########""

from rich.console import Console
from rich.text import Text

console = Console()

separator_color = "#303030"


def darken(hex_color: str, factor: float = 0.93) -> str:
    """Darken a #RRGGBB color while preserving its hue."""
    hex_color = hex_color.lstrip("#")

    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    r = round(r * factor)
    g = round(g * factor)
    b = round(b * factor)

    return f"#{r:02x}{g:02x}{b:02x}"


header = Text("        ")
for col in range(1, 10):
    header.append(f" {col} ")
console.print(header)

for row, (region_row, state_row) in enumerate(
    zip(regions, state),
    start=1,
):
    line = Text(f"Line {row:02d} ")

    for region, cell in zip(region_row, state_row):
        base_color = colors[region]

        # Alternate very subtly between rows.
        bg = (
            base_color
            if row % 2 == 1
            else darken(base_color, 0.93)
        )

        # Fine vertical cell boundary.
        line.append(
            "▏",
            style=f"#303030 on {bg}",
        )

        # Cell contents.
        line.append(
            f"{symbols[cell]} ",
            style=f"bold white on {bg}",
        )

    console.print(line)



    ######

console.print('finaaaaal')

from rich.console import Console
from rich.text import Text

console = Console()


def darken(hex_color: str, factor: float = 0.93) -> str:
    """Darken a #RRGGBB color while preserving its hue."""
    hex_color = hex_color.lstrip("#")

    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    r = round(r * factor)
    g = round(g * factor)
    b = round(b * factor)

    return f"#{r:02x}{g:02x}{b:02x}"


header = Text("        ")
for col in range(1, 10):
    header.append(f" {col} ")
console.print(header)

for row, (region_row, state_row) in enumerate(
    zip(regions, state),
    start=1,
):
    line = Text(f"Line {row:02d} ")

    for col, (region, cell) in enumerate(
        zip(region_row, state_row),
        start=1,
    ):
        base_color = colors[region]

        # Checkerboard:
        # ■ □ ■ □ ■
        # □ ■ □ ■ □
        dark = (row + col) % 2 == 0

        bg = darken(base_color, 0.93) if dark else base_color

        # No separator at all.
        line.append(
            f" {symbols[cell]} ",
            style=f"bold white on {bg}",
        )

    console.print(line)