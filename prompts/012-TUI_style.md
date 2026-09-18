Update the debug/TUI board renderer to replace the current region emoji representation with colored cell backgrounds.



This is a \*\*presentation-only refactor\*\*. Do not change the Board model, RegionIds, deductions, hint/proof rendering, solver behavior, ranking, or any reasoning logic. Region colors must remain purely cosmetic.



Use the implementation below as the visual target:



- each cell is exactly 3 terminal columns wide;
- the cell background color represents its region;
- unknown cells have no glyph;
- excluded cells display \`×\`;
- queens display \`♛\`;
- use a subtle checkerboard variation of each region's background color to make individual cell boundaries readable without explicit separators;
- preserve the region hue: alternate between the base region color and a slightly darkened version (\`factor=0.93\`) according to \`(row + column) % 2\`;
- do \*\*not\*\* add vertical or horizontal separator characters;
- preserve row/column labels and existing compact dimension formatting conventions;
- keep deterministic region-to-color assignment;
- adapt/update renderer tests for the new presentation, but do not weaken tests of semantic board state.



Prefer integrating this cleanly into the existing renderer/palette abstractions rather than copying the prototype literally if the current architecture provides a better place for the color transformation.



Run the relevant renderer tests and the full test suite afterward. Do not commit or tag unless explicitly requested.



Here is the tested prototype:







from rich.console import Console

from rich.text import Text



console = Console()



def darken(hex\\\_color: str, factor: float = 0.93) -> str:

"""Darken a #RRGGBB color while preserving its hue."""

hex\\\_color = hex\\\_color.lstrip("#")
```python
r = int(hex_color[0:2], 16)
g = int(hex_color[2:4], 16)
b = int(hex_color[4:6], 16)

r = round(r * factor)
g = round(g * factor)
b = round(b * factor)

return f"#{r:02x}{g:02x}{b:02x}"
```



header = Text("        ")

for col in range(1, 10):

header.append(f" {col} ")

console.print(header)



for row, (region\\\_row, state\\\_row) in enumerate(

zip(regions, state),

start=1,

):

line = Text(f"Line {row:02d} ")
```python
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
```



### one small fix after
remplace la queen "♛" par un "Q" majuscule et gras, en gardant le changement de couleur en fonction du fond que tu as deja mis en place