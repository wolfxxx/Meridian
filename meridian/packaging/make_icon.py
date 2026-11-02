"""Draw the Meridian app icon (packaging/meridian.ico) at all Windows icon sizes."""

from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent


def draw(size: int) -> Image.Image:
    s = 4  # supersample, then downscale for smooth edges
    n = size * s
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = int(n * 0.22)
    d.rounded_rectangle([0, 0, n - 1, n - 1], radius=r, fill=(14, 106, 140, 255))
    w = max(int(n * 0.075), s)
    pad = int(n * 0.2)
    box = [pad, pad, n - pad, n - pad]
    d.ellipse(box, outline=(255, 255, 255, 255), width=w)
    # the meridian: right half of an ellipse through the poles
    cx = n / 2
    rx = (n - 2 * pad) * 0.24
    d.arc([cx - rx, pad, cx + rx, n - pad], start=-90, end=90, fill=(255, 255, 255, 255), width=w)
    d.line([pad + w, n / 2, n - pad - w, n / 2], fill=(255, 255, 255, 110), width=max(w // 2, 1))
    return img.resize((size, size), Image.LANCZOS)


def main():
    sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    big = draw(256)
    big.save(HERE / "meridian.ico", sizes=[(x, x) for x in sizes], append_images=[draw(x) for x in sizes[:-1]])
    big.save(HERE / "meridian.png")
    print("wrote", HERE / "meridian.ico")


if __name__ == "__main__":
    main()
