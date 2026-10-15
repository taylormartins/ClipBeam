"""Generate professional icons for ClipBeam."""
from PIL import Image, ImageDraw

def create_icon(size=256):
    img = Image.new('RGBA', (size, size), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    scale = size / 64.0

    def s(val):
        return int(val * scale)

    # Gradient background circle / rounded squircle
    draw.rounded_rectangle(
        [s(4), s(4), s(60), s(60)],
        radius=s(14),
        fill=(15, 23, 42, 255),       # Dark slate blue
        outline=(56, 189, 248, 255),  # Electric Sky Blue
        width=max(1, s(2))
    )

    # Clipboard board
    draw.rounded_rectangle(
        [s(16), s(14), s(48), s(54)],
        radius=s(5),
        fill=(30, 41, 59, 255),
        outline=(148, 163, 184, 255),
        width=max(1, s(1))
    )

    # Clipboard paper inside
    draw.rounded_rectangle(
        [s(20), s(20), s(44), s(50)],
        radius=s(3),
        fill=(248, 250, 252, 255)
    )

    # Clip at top
    draw.rounded_rectangle(
        [s(24), s(11), s(40), s(18)],
        radius=s(3),
        fill=(14, 165, 233, 255),
        outline=(2, 132, 199, 255),
        width=max(1, s(1))
    )

    # Document text lines
    draw.line([s(24), s(26), s(40), s(26)], fill=(148, 163, 184, 255), width=max(1, s(2)))
    draw.line([s(24), s(32), s(36), s(32)], fill=(148, 163, 184, 255), width=max(1, s(2)))
    draw.line([s(24), s(38), s(39), s(38)], fill=(148, 163, 184, 255), width=max(1, s(2)))

    # Lightning bolt / beam signal overlaid on bottom right
    bolt_coords = [
        (s(38), s(24)),
        (s(48), s(24)),
        (s(42), s(36)),
        (s(52), s(36)),
        (s(34), s(56)),
        (s(39), s(42)),
        (s(32), s(42)),
    ]
    # Bolt glow/shadow
    draw.polygon(bolt_coords, fill=(245, 158, 11, 255))
    draw.line(bolt_coords + [bolt_coords[0]], fill=(251, 191, 36, 255), width=max(1, s(1)))

    return img

if __name__ == '__main__':
    img_256 = create_icon(256)
    img_256.save('clipbeam.png', format='PNG')
    
    # Save multi-size ICO
    icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    images = [create_icon(s) for s, _ in icon_sizes]
    images[0].save('clipbeam.ico', format='ICO', sizes=icon_sizes, append_images=images[1:])
    print("clipbeam.ico and clipbeam.png generated successfully!")
