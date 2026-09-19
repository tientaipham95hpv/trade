import os
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "logo.png")

if not os.path.exists(LOGO_PATH):
    LOGO_PATH = os.path.join(BASE_DIR, "web", "static", "logo.png")

print(f"Loading source logo from: {LOGO_PATH}")
src_img = Image.open(LOGO_PATH).convert("RGBA")
print(f"Source image size: {src_img.size}")

# 1. PC APP ICONS
pc_assets = os.path.join(BASE_DIR, "pc-app", "assets")
os.makedirs(pc_assets, exist_ok=True)

# 1.1 icon.png (512x512)
icon_png_path = os.path.join(pc_assets, "icon.png")
icon_512 = src_img.resize((512, 512), Image.Resampling.LANCZOS)
icon_512.save(icon_png_path, format="PNG")
print(f"Saved: {icon_png_path}")

# 1.2 icon.ico (Multi-size ICO)
icon_ico_path = os.path.join(pc_assets, "icon.ico")
ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
icon_512.save(icon_ico_path, format="ICO", sizes=ico_sizes)
print(f"Saved: {icon_ico_path}")

# 2. IOS APP ICONS (AppIcon.appiconset)
ios_icons_dir = os.path.join(BASE_DIR, "ios-app", "ios", "Runner", "Assets.xcassets", "AppIcon.appiconset")
os.makedirs(ios_icons_dir, exist_ok=True)

# List of all required iOS icons with their exact pixel sizes
ios_icon_specs = {
    "Icon-App-20x20@1x.png": 20,
    "Icon-App-20x20@2x.png": 40,
    "Icon-App-20x20@3x.png": 60,
    "Icon-App-29x29@1x.png": 29,
    "Icon-App-29x29@2x.png": 58,
    "Icon-App-29x29@3x.png": 87,
    "Icon-App-40x40@1x.png": 40,
    "Icon-App-40x40@2x.png": 80,
    "Icon-App-40x40@3x.png": 120,
    "Icon-App-60x60@2x.png": 120,
    "Icon-App-60x60@3x.png": 180,
    "Icon-App-76x76@1x.png": 76,
    "Icon-App-76x76@2x.png": 152,
    "Icon-App-83.5x83.5@2x.png": 167,
    "Icon-App-1024x1024@1x.png": 1024,
}

for filename, size in ios_icon_specs.items():
    target_path = os.path.join(ios_icons_dir, filename)
    # Apple App Store 1024x1024 marketing icon must NOT have alpha channel
    if size == 1024:
        resized = src_img.convert("RGB").resize((size, size), Image.Resampling.LANCZOS)
    else:
        resized = src_img.resize((size, size), Image.Resampling.LANCZOS)
    resized.save(target_path, format="PNG")
    print(f"Saved iOS Icon: {filename} ({size}x{size})")

# 3. IOS IN-APP ASSET (for Flutter UI)
flutter_assets = os.path.join(BASE_DIR, "ios-app", "assets")
os.makedirs(flutter_assets, exist_ok=True)
flutter_logo_path = os.path.join(flutter_assets, "logo.png")
icon_512.save(flutter_logo_path, format="PNG")
print(f"Saved Flutter Asset: {flutter_logo_path}")

# 4. IOS LAUNCH SCREEN IMAGES
launch_dir = os.path.join(BASE_DIR, "ios-app", "ios", "Runner", "Assets.xcassets", "LaunchImage.imageset")
os.makedirs(launch_dir, exist_ok=True)
launch_specs = {
    "LaunchImage.png": 180,
    "LaunchImage@2x.png": 360,
    "LaunchImage@3x.png": 540,
}
for filename, size in launch_specs.items():
    target_path = os.path.join(launch_dir, filename)
    resized = src_img.resize((size, size), Image.Resampling.LANCZOS)
    resized.save(target_path, format="PNG")
    print(f"Saved Launch Image: {filename} ({size}x{size})")

print("\n--- ALL ICONS AND LOGOS GENERATED SUCCESSFULLY ---")
