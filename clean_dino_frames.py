from PIL import Image
import os

frames_dir = os.path.join(os.path.dirname(__file__), 'dino_frames')
frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith('.png')])

for fname in frame_files:
    path = os.path.join(frames_dir, fname)
    im = Image.open(path).convert('RGBA')
    datas = im.getdata()
    newData = []
    bg_color = datas[0]
    for item in datas:
        if item[:3] == bg_color[:3]:
            newData.append((255, 255, 255, 0))  # Transparent
        else:
            newData.append(item)
    im.putdata(newData)
    im.save(path)

print(f"Cleaned {len(frame_files)} frames in {frames_dir}")
