from PIL import Image
import os

gif_path = os.path.join(os.path.dirname(__file__), 'dino_runner-removebg-preview.gif')
frames_dir = os.path.join(os.path.dirname(__file__), 'dino_frames')
os.makedirs(frames_dir, exist_ok=True)

# Load GIF
im = Image.open(gif_path)
frame_count = im.n_frames

for i in range(frame_count):
    im.seek(i)
    frame = im.convert('RGBA')
    datas = frame.getdata()
    newData = []
    # Remove background (fuzzy match to top-left pixel)
    bg_color = datas[0]
    threshold = 32  # Increase for more aggressive removal
    def close(c1, c2):
        return sum(abs(a-b) for a, b in zip(c1[:3], c2[:3])) < threshold
    for item in datas:
        if close(item, bg_color):
            newData.append((255, 255, 255, 0))  # Transparent
        else:
            newData.append(item)
    frame.putdata(newData)
    frame.save(os.path.join(frames_dir, f'dino_frame_{i:02d}.png'))

print(f"Extracted {frame_count} frames to {frames_dir}")
