# pyright: standard
# i know this is a mess of ai code and my messy code bujt i just wanted something to easily zip the project :D
import zipfile
import json
from pathlib import Path

def get_ignored_patterns():
    # Explicitly exclude metadata, our release folder, and this script itself
    ignores = {".gitignore", ".git", "pack.py", "releases"}
    gitignore = Path(".gitignore")
    if gitignore.exists():
        for line in gitignore.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and not line == "version.txt":
                ignores.add(line.rstrip("/"))
    return ignores

def bump_version() -> str:
    vj_file = Path("version.json")
    current_version = [0, 0, 0]
    if vj_file.exists():
        current_version = json.loads(vj_file.read_text())

    user_input: str = ""
    while True:
        user_input = input(
            f"Current version: {current_version}\n"
            "To bump the version, type x, y, or z (vX.Y.Z)\n"
            "To override the version, type the full version number\n"
            "To start packing, type `pack`\n\n"
            "Command: "
        ).strip().lower()
        if user_input == "x":
            current_version[0] += 1
            current_version[1] = 0
            current_version[2] = 0
        elif user_input == "y":
            current_version[1] += 1
            current_version[2] = 0
        elif user_input == "z":
            current_version[2] += 1
        elif user_input.startswith("v"):
            input_split = user_input.removeprefix("v").split(".")
            if len(input_split) != 3:
                print("Invalid format! Format must be vX.Y.Z")
                continue
            try:
                current_version = [
                    int(input_split[0]),
                    int(input_split[1]),
                    int(input_split[2])
                ]
            except ValueError as e:
                print("Not valid numbers!asdsdf")
        elif user_input == "pack":
            break
    vj_file.write_text(json.dumps(current_version))
    return f"v{current_version[0]}.{current_version[1]}.{current_version[2]}"

def pack_project():
    version = bump_version()
    ignores = get_ignored_patterns()

    # Ensure the releases directory exists
    releases_dir = Path("releases")
    releases_dir.mkdir(exist_ok=True)

    zip_path = releases_dir / f"MPMP-{version}.zip"
    subdir_name = f"MPMP-{version}"
    version_file = Path("version.txt")

    # 1. Temporarily create the version.txt file
    print(f"Generating version.txt (v{version})...")
    version_file.write_text(version)

    try:
        # 2. Build the zip archive
        print(f"Creating archive: {zip_path}")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in Path(".").rglob("*"):
                if file_path.is_file():
                    # Skip any files or folders in the ignore list
                    if any(part in ignores for part in file_path.parts):
                        continue

                    # Nest everything inside a main folder to prevent zip-bombs
                    archive_name = Path(subdir_name) / file_path
                    zipf.write(file_path, arcname=archive_name)
                    print(f"  Added: {archive_name}")

        print(f"\n🎉 Successfully packed v{version} into {zip_path}!")

    finally:
        # 3. Clean up version.txt so it doesn't clutter local workspace
        if version_file.exists():
            version_file.unlink()
            print("Cleaned up temporary version.txt.")

if __name__ == "__main__":
    pack_project()