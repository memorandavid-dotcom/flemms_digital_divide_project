"""Export the draw.io diagrams in docs/diagrams/ to PNG files in docs/images/.

The .drawio files are the editable sources. Open one at app.diagrams.net
(File > Open from > Device), edit it, save it back to docs/diagrams/, then
refresh the PNGs used by the docs, the README and the slides:

    python docs/render_diagrams.py

Needs Docker (uses the drawio-export image, so draw.io does not need to be installed).
"""
import shutil
import subprocess
from pathlib import Path

DOCS = Path(__file__).resolve().parent
DIAGRAMS = DOCS / "diagrams"
IMAGES = DOCS / "images"
# Pinned by digest (drawio-exporter 1.6.0) so every export looks the same
EXPORTER = "rlespinasse/drawio-export@sha256:2c133c2bbb42ba97fb3c8aca83fd62be3927fef8c7caeba2673d4092b7f6c578"


def main() -> None:
    IMAGES.mkdir(exist_ok=True)
    export = DIAGRAMS / "export"  # the exporter writes here; emptied after each run
    try:
        subprocess.run(["docker", "run", "--rm", "-v", f"{DIAGRAMS}:/data", EXPORTER,
                        "--format", "png", "--scale", "2", "--border", "20", "--remove-page-suffix"], check=True)
        for png in sorted(export.glob("*.png")):
            png.replace(IMAGES / png.name)
            print(f"Exported docs/images/{png.name}")
    finally:
        shutil.rmtree(export, ignore_errors=True)


if __name__ == "__main__":
    main()
