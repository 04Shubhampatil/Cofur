from pathlib import Path
from PIL import Image, ImageEnhance

root = Path(__file__).resolve().parents[1]
source = root / "assets/images/gemini-generated-image-es8-qpwes8-qpwes8-q1.png"
output = root / "assets/images/cofur-ai-hero-motion.webp"
image = Image.open(source).convert("RGB")
target = (1440, 800)
frames = []

for index in range(72):
    phase = index if index <= 36 else 72 - index
    zoom = 1.0 + (phase / 36) * 0.045
    scale = max(target[0] / image.width, target[1] / image.height) * zoom
    resized = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
    left = (resized.width - target[0]) // 2 + round((phase / 36) * 10)
    top = (resized.height - target[1]) // 2 - round((phase / 36) * 5)
    frame = resized.crop((left, top, left + target[0], top + target[1]))
    frame = ImageEnhance.Brightness(frame).enhance(0.98 + (phase / 36) * 0.02)
    frames.append(frame)

frames[0].save(output, save_all=True, append_images=frames[1:], duration=90, loop=0, quality=78, method=4)
print(output)
