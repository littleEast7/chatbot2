"""Package a frozen Linux application without bundling development profiles."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tarfile

VERSION = "0.2.0"
DEPENDENCIES = (
    "libc6 (>= 2.39), libstdc++6, libgcc-s1, libgl1, libegl1, "
    "libglib2.0-0t64, libfontconfig1, libfreetype6, libdbus-1-3, "
    "libx11-6, libx11-xcb1, libxext6, libxrender1, libxi6, libsm6, libice6, "
    "libxkbcommon0, libxkbcommon-x11-0, libxcb1, libxcb-cursor0, "
    "libxcb-icccm4, libxcb-util1, libxcb-image0, libxcb-keysyms1, "
    "libxcb-randr0, libxcb-render-util0, libxcb-shape0, libxcb-shm0, "
    "libxcb-sync1, libxcb-xfixes0, libxcb-xinerama0, libxcb-xkb1"
)


def write_file(path, text, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(mode)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--architecture", choices=("amd64", "arm64"), required=True)
    args = parser.parse_args()
    if not (args.bundle / "DeskBuddy").is_file() or not (args.bundle / "_internal").is_dir():
        parser.error("Expected a PyInstaller onedir bundle with its embedded runtime")
    args.output.mkdir(parents=True, exist_ok=True)
    stage = args.output / "package-root"
    if stage.exists():
        shutil.rmtree(stage)
    application = stage / "opt/deskbuddy"
    shutil.copytree(args.bundle, application, symlinks=True)
    installed_size = sum(path.stat().st_size for path in application.rglob("*")
                         if path.is_file() and not path.is_symlink()) // 1024
    write_file(stage / "DEBIAN/control", f"""Package: deskbuddy
Version: {VERSION}
Section: utils
Priority: optional
Architecture: {args.architecture}
Maintainer: DeskBuddy contributors <noreply@github.com>
Installed-Size: {installed_size}
Depends: {DEPENDENCIES}
Recommends: fonts-noto-cjk
Homepage: https://github.com/littleEast7/chatbot2
Description: Desktop companion with reminders and local network messaging
 Includes Python, Qt and application dependencies. No Python setup is required.
 Built for Ubuntu 24.04 Desktop.
""")
    write_file(stage / "usr/bin/deskbuddy", '#!/bin/sh\nexec /opt/deskbuddy/DeskBuddy "$@"\n', 0o755)
    write_file(stage / "usr/share/applications/deskbuddy.desktop", """[Desktop Entry]
Type=Application
Name=DeskBuddy
Comment=Desktop companion and reminders
Comment[zh_CN]=桌面陪伴、提醒与局域网聊天
Exec=/opt/deskbuddy/DeskBuddy
Icon=applications-utilities
Terminal=false
Categories=Utility;Network;
StartupNotify=true
""")
    readme = """DeskBuddy for Ubuntu 24.04 Desktop

The application includes its own Python and Qt runtime. Do not install Python.

Debian package: sudo apt install ./deskbuddy_0.2.0_ARCH.deb
Then launch DeskBuddy from the application menu, or run: deskbuddy
Uninstall: sudo apt remove deskbuddy

Portable archive: extract the full folder, then run ./DeskBuddy/DeskBuddy
Keep the _internal folder next to the executable.
The portable version needs standard desktop libraries; the .deb declares them.
Chinese text requires a CJK font (recommended package: fonts-noto-cjk).

Settings and rotating logs: ~/.local/share/DeskBuddy/
(or $XDG_DATA_HOME/DeskBuddy when XDG_DATA_HOME is set).
Use --port 9001 for a second instance.

amd64 is for Intel/AMD x86_64 computers.
arm64 is for ARM computers and Ubuntu ARM virtual machines on Apple silicon.
This Linux build cannot run directly on macOS. For macOS use DeskBuddy.app.
""".replace("ARCH", args.architecture)
    write_file(stage / "usr/share/doc/deskbuddy/README", readme)
    deb = args.output / f"deskbuddy_{VERSION}_{args.architecture}.deb"
    subprocess.run(["dpkg-deb", "--build", "--root-owner-group", str(stage), str(deb)], check=True)
    portable = args.output / f"DeskBuddy-Ubuntu-24.04-{args.architecture}.tar.gz"
    readme_path = args.output / "README-Ubuntu.txt"
    write_file(readme_path, readme)
    with tarfile.open(portable, "w:gz") as archive:
        archive.add(args.bundle, arcname="DeskBuddy")
        archive.add(readme_path, arcname="README-Ubuntu.txt")
    # Staging is disposable; only the .deb and portable archive are delivered.
    shutil.rmtree(stage)
    print(f"Ubuntu packages: {deb}\n{portable}")


if __name__ == "__main__":
    main()
