import os
import mimetypes
from typing import List
from .constants import VIDEO_EXTENSIONS, GIF_EXTENSIONS, VALID_INPUT_EXTENSIONS

mimetypes.init()


def is_video_file(path: str) -> bool:
    if not os.path.isfile(path):
        return False
    ext = os.path.splitext(path)[1].lower()
    if ext in VIDEO_EXTENSIONS:
        return True
    try:
        mime_type, _ = mimetypes.guess_type(path)
        return mime_type is not None and mime_type.startswith("video")
    except Exception as e:
        print(f"Warning: Could not guess mime type for {path}: {e}")
        return False


def is_gif_file(path: str) -> bool:
    if not os.path.isfile(path):
        return False
    ext = os.path.splitext(path)[1].lower()
    return ext in GIF_EXTENSIONS


def find_videos_in_folder(folder: str, include_gifs: bool = False) -> List[str]:
    found = []
    if include_gifs:
        valid_extensions = VIDEO_EXTENSIONS + GIF_EXTENSIONS
    else:
        valid_extensions = VIDEO_EXTENSIONS

    if not os.path.isdir(folder):
        print(f"Error: Folder not found: {folder}")
        return found

    try:
        for root, dirs, files in os.walk(folder):
            for name in files:
                fp = os.path.join(root, name)
                ext = os.path.splitext(name)[1].lower()
                if ext in valid_extensions:
                    try:
                        if os.access(fp, os.R_OK):
                            found.append(fp)
                        else:
                            print(f"Warning: No read access to file: {fp}")
                    except Exception as e:
                        print(f"Warning: Could not access file {fp}: {e}")

    except Exception as e:
        print(f"Error walking directory {folder}: {e}")

    return found
