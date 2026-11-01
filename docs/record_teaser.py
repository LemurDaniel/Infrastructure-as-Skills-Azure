#!/usr/bin/env python3
"""Records docs/teaser.html as the GIF the README shows.

    python docs/record_teaser.py [--out docs/teaser.gif] [--fps 10]
    python docs/record_teaser.py --page docs/teaser-unclick.html --out docs/teaser-unclick.gif

Any page on the same stage records the same way: it has #frame, the #record mode and
window.__seek(t). --end is when its last scene ends.

The page is opened in its #record mode (CSS transitions off, every fade computed from the
clock), seeked frame by frame through window.__seek(t) and screenshotted, so each frame is
exact at its time and the GIF never depends on how fast the machine renders. All frames
share one palette sampled across the scenes, so colours do not flicker between frames.

Uses the installed Microsoft Edge (Playwright's msedge channel); no browser download.
Needs Playwright and Pillow, not PyYAML: pip install playwright pillow. On Windows a venv
under a long path fails to install Playwright (MAX_PATH); put it under a short one.

Exit 0 written, 2 not written.
"""
import argparse
import io
import sys
from pathlib import Path

try:
    from PIL import Image
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright and Pillow are required: pip install playwright pillow")
    sys.exit(2)

HERE = Path(__file__).resolve().parent
PAGE = HERE / "teaser.html"
END = 33.9               # the last scene ends at 34 s and fades out after it
SIZE = (960, 540)
LAST_FRAME_MS = 2500     # hold the install line before the loop restarts


def grab(page_path, end, fps):
    frames = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(page_path.resolve().as_uri() + "#record")
        page.evaluate("document.fonts.ready")
        page.wait_for_load_state("networkidle")
        frame = page.locator("#frame")
        for i in range(int(end * fps) + 1):
            page.evaluate(f"window.__seek({i / fps})")
            shot = Image.open(io.BytesIO(frame.screenshot())).convert("RGB")
            frames.append(shot.resize(SIZE, Image.LANCZOS))
        browser.close()
    return frames


def write_gif(frames, fps, out):
    w, h = SIZE
    sample = Image.new("RGB", (w, h * 8))
    for k in range(8):
        sample.paste(frames[int(k * (len(frames) - 1) / 7)], (0, h * k))
    palette = sample.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    gif = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    durations = [1000 // fps] * len(gif)
    durations[-1] = LAST_FRAME_MS
    gif[0].save(out, save_all=True, append_images=gif[1:], duration=durations, loop=0, disposal=1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--page", type=Path, default=PAGE)
    ap.add_argument("--out", type=Path, default=HERE / "teaser.gif")
    ap.add_argument("--end", type=float, default=END)
    ap.add_argument("--fps", type=int, default=10)
    args = ap.parse_args()

    frames = grab(args.page, args.end, args.fps)
    write_gif(frames, args.fps, args.out)
    print(f"{args.out}: {len(frames)} frames, {args.out.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
