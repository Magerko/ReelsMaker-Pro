import sys
import os
import ctypes
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
import logging

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from ui.main_window import VideoUnicApp
from utils.constants import APP_NAME, APP_VERSION, FFMPEG_EXE_PATH


def set_app_user_model_id(app_id):
    if sys.platform == 'win32':
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)


def main():
    log_file_path = os.path.join(project_root, 'crash_log.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path, mode='w', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.info("Application started.")

    if sys.platform.startswith('win'):
        try:
            os.system("chcp 65001")
            os.environ["PYTHONIOENCODING"] = "utf-8"
        except Exception as e:
            logging.warning(f"Warning: Failed to set console encoding: {e}")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    myappid = f'mycompany.{APP_NAME}.{APP_VERSION}'
    set_app_user_model_id(myappid)

    if sys.platform.startswith('win') and not os.path.exists(FFMPEG_EXE_PATH):
        logging.error(f"Error: ffmpeg.exe not found at {FFMPEG_EXE_PATH}")
        logging.error("Please ensure FFmpeg is in the specified path or in your system's PATH.")

    w = VideoUnicApp()

    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
