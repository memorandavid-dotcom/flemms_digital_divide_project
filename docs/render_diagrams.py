"""Render the Mermaid diagrams in docs/*.md to PNG files in docs/images/.

GitHub draws Mermaid diagrams automatically when you open the .md files; the
PNGs are for slides and the written report. Re-run after editing a diagram:

    python docs/render_diagrams.py

Needs Docker (uses the official Mermaid CLI image, so Node.js is not required).
"""
import re
import subprocess
from pathlib import Path

DOCS = Path(__file__).resolve().parent
IMAGES = DOCS / "images"
RENDERER = "minlag/mermaid-cli:12.0.0"
DIAGRAMS = {"architecture": "architecture.md", "data_flow": "data_flow.md", "erd": "erd.md"}
# Extra copies with a different layout direction: name -> (diagram, replacement first line)
VARIANTS = {"architecture_wide": ("architecture", "flowchart LR")}  # wide version for slides


def render(name: str, diagram: str) -> None:
    source = IMAGES / f"{name}.mmd"
    source.write_text(diagram, encoding="utf-8")
    try:
        subprocess.run(["docker", "run", "--rm", "-v", f"{IMAGES}:/data", RENDERER,
                        "-i", f"/data/{name}.mmd", "-o", f"/data/{name}.png",
                        "--backgroundColor", "white", "--scale", "3"], check=True)
    finally:
        source.unlink()
    print(f"Rendered docs/images/{name}.png")


def main() -> None:
    IMAGES.mkdir(exist_ok=True)
    diagrams = {}
    for name, markdown_file in DIAGRAMS.items():
        text = (DOCS / markdown_file).read_text(encoding="utf-8")
        diagrams[name] = re.search(r"```mermaid\n(.*?)```", text, re.DOTALL).group(1)
        render(name, diagrams[name])
    for name, (base, first_line) in VARIANTS.items():
        rest = diagrams[base].split("\n", 1)[1]
        render(name, first_line + "\n" + rest)


if __name__ == "__main__":
    main()
