"""
Regenerate favicon and apple-touch-icon from website_logo.png

Run this script after updating website_logo.png:
    python generate_icons.py
"""

from pathlib import Path
from PIL import Image

LOGO_FILE = Path(__file__).parent / "website_logo.png"
STATIC_DIR = Path(__file__).parent / "static"


def main():
    if not LOGO_FILE.exists():
        print(f"ERROR: Logo file not found: {LOGO_FILE}")
        return

    # Open the logo
    img = Image.open(LOGO_FILE)
    print(f"Source: {LOGO_FILE} ({img.size[0]}x{img.size[1]})")

    # Convert to RGBA if needed
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    # Create apple-touch-icon (180x180)
    apple_icon = img.copy()
    apple_icon.thumbnail((180, 180), Image.LANCZOS)
    apple_canvas = Image.new("RGBA", (180, 180), (255, 255, 255, 0))
    x = (180 - apple_icon.width) // 2
    y = (180 - apple_icon.height) // 2
    apple_canvas.paste(apple_icon, (x, y), apple_icon)
    apple_canvas.save(STATIC_DIR / "apple-touch-icon.png", "PNG")
    print("Created static/apple-touch-icon.png (180x180)")

    # Create favicon (32x32)
    favicon = img.copy()
    favicon.thumbnail((32, 32), Image.LANCZOS)
    favicon_canvas = Image.new("RGBA", (32, 32), (255, 255, 255, 0))
    x = (32 - favicon.width) // 2
    y = (32 - favicon.height) // 2
    favicon_canvas.paste(favicon, (x, y), favicon)
    favicon_canvas.save(STATIC_DIR / "favicon.png", "PNG")
    favicon_canvas.save(STATIC_DIR / "favicon-32.png", "PNG")
    print("Created static/favicon.png (32x32)")
    print("Created static/favicon-32.png (32x32)")

    print("\nDone! Icons updated.")


if __name__ == "__main__":
    main()
