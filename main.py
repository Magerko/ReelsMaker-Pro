import sys
import os
import ctypes
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
import logging

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from ui.main_window import VideoUnicApp
from utils.constants import APP_NAME, APP_VERSION
from utils.ffmpeg_utils import FFMPEG_PATH_EFFECTIVE
from utils.path_utils import resource_path, user_data_dir


def set_app_user_model_id(app_id):
    if sys.platform == 'win32':
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)


def setup_logging():
    # Лог рядом с программой не годится: в собранном виде это временная папка,
    # которая удаляется при выходе, а в Program Files запись запрещена - то
    # есть крэш-лог пропадал ровно тогда, когда он нужен.
    log_dir = user_data_dir()
    os.makedirs(log_dir, exist_ok=True)
    handlers = [logging.FileHandler(os.path.join(log_dir, 'app.log'),
                                    mode='w', encoding='utf-8')]
    # В оконной сборке стандартного вывода нет, и StreamHandler по нему падает.
    if sys.stdout is not None:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
        handlers=handlers,
        # ffmpeg_utils вызывает logging.info() ещё при импорте, определяя путь
        # к ffmpeg. Этот вызов сам настраивает корневой логгер, и без force
        # наша конфигурация просто игнорируется - лог создавался, но оставался
        # пустым.
        force=True
    )


def main():
    setup_logging()
    logging.info(f"{APP_NAME} {APP_VERSION} started.")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    icon_path = resource_path(os.path.join('resources', 'icon.png'))
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    set_app_user_model_id(f'Magerko.{APP_NAME}.{APP_VERSION}')

    if not FFMPEG_PATH_EFFECTIVE:
        logging.error("ffmpeg not found next to the application or on PATH.")

    w = VideoUnicApp()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
