import os
import sys
import random
import tempfile
import uuid
import shutil
import logging

from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QThread
from PyQt5.QtGui import QColor, QFont, QFontMetrics, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QAbstractItemView, QFileDialog, QSpinBox,
    QLineEdit, QMessageBox, QProgressBar, QComboBox,
    QGroupBox, QRadioButton, QButtonGroup, QCheckBox, QSplitter, QListWidgetItem,
    QTabWidget, QMenu, QFrame, QScrollArea, QInputDialog, QPlainTextEdit, QSlider, QApplication, QDialog
)
import qtawesome as qta

from workers.worker import Worker
from utils.file_utils import is_video_file, find_videos_in_folder
from utils.constants import (
    FILTERS, FILTER_GROUPS, OVERLAY_POSITIONS, REELS_FORMAT_NAME, OUTPUT_FORMATS, CODECS,
    SPLIT_LAYOUTS, SPLIT_POSITIONS, SPLIT_CONTENT_TOP, SCENARIOS,
    WHISPER_MODELS, WHISPER_LANGUAGES, APP_NAME, APP_VERSION
)
from utils.ffmpeg_utils import (generate_preview, get_video_duration, detect_crop_dimensions,
                                list_filler_presets, detect_available_codecs)
from utils.path_utils import resource_path
from utils import links
from ui.subtitle_preview_dialog import SubtitlePreviewDialog


class CodecProbeWorker(QThread):
    """Выясняет, какие видеокодировщики доступны на этой машине."""
    finished_signal = pyqtSignal(dict)

    def run(self):
        try:
            self.finished_signal.emit(detect_available_codecs(CODECS))
        except Exception as e:
            logging.getLogger(__name__).warning(f"Codec probe failed: {e}")
            self.finished_signal.emit({})


class PreviewWorker(QThread):
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        try:
            generate_preview(**self.params)
            self.finished_signal.emit(self.params['out_path'])
        except Exception as e:
            self.error_signal.emit(str(e))


class DropListWidget(QListWidget):
    files_dropped = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(False)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setContextMenuPolicy(Qt.CustomContextMenu)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            added_files = False
            for url in event.mimeData().urls():
                fp = url.toLocalFile()
                if os.path.isdir(fp):
                    vids = find_videos_in_folder(fp)
                    for v in vids:
                        if is_video_file(v) and not self.is_already_added(v):
                            it = QListWidgetItem(v)
                            it.setData(Qt.UserRole, v)
                            self.addItem(it)
                            added_files = True
                else:
                    if (is_video_file(fp) or fp.lower().endswith('.gif')) and not self.is_already_added(fp):
                        it = QListWidgetItem(fp)
                        it.setData(Qt.UserRole, fp)
                        self.addItem(it)
                        added_files = True
            if added_files:
                self.files_dropped.emit()
        else:
            event.ignore()

    def is_already_added(self, file_path):
        for i in range(self.count()):
            if self.item(i).data(Qt.UserRole) == file_path:
                return True
        return False


class SettingsDialog(QDialog):
    def __init__(self, parent=None, current_settings=None):
        super().__init__(parent)
        self.current_settings = current_settings or {}
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Настройки")
        self.setFixedSize(450, 280)
        self.setObjectName("settings_dialog")

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # FFmpeg path
        ffmpeg_group = QGroupBox("FFmpeg")
        ffmpeg_layout = QHBoxLayout(ffmpeg_group)
        self.ffmpeg_path_edit = QLineEdit()
        self.ffmpeg_path_edit.setPlaceholderText("Путь к ffmpeg.exe (необязательно)")
        self.ffmpeg_path_edit.setText(self.current_settings.get('ffmpeg_path', ''))
        browse_btn = QPushButton("Обзор")
        browse_btn.clicked.connect(self.browse_ffmpeg)
        ffmpeg_layout.addWidget(self.ffmpeg_path_edit)
        ffmpeg_layout.addWidget(browse_btn)
        layout.addWidget(ffmpeg_group)

        # Metadata checkbox
        self.strip_meta_checkbox = QCheckBox("Очистить метаданные при обработке")
        self.strip_meta_checkbox.setChecked(self.current_settings.get('strip_metadata', True))
        layout.addWidget(self.strip_meta_checkbox)

        # Theme selector
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Тема оформления:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        self.theme_combo.setCurrentText(self.current_settings.get('theme', 'Dark'))
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        layout.addLayout(theme_layout)

        layout.addStretch()

        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton("Сохранить")
        ok_btn.setObjectName("ok_button")
        ok_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(ok_btn)
        layout.addLayout(buttons_layout)

    def browse_ffmpeg(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите ffmpeg.exe", "", "Executable Files (*.exe)")
        if path:
            self.ffmpeg_path_edit.setText(path)

    def get_settings(self):
        return {
            'ffmpeg_path': self.ffmpeg_path_edit.text(),
            'strip_metadata': self.strip_meta_checkbox.isChecked(),
            'theme': self.theme_combo.currentText()
        }


class ProcessingWidgetContent(QWidget):

    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.preview_thread = None
        self.processing_thread = None
        self.last_output_path = None
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)

        left_widget = QWidget()
        self.left_panel = QVBoxLayout(left_widget)
        self.left_panel.setSpacing(12)

        right_widget = QWidget()
        self.right_panel = QVBoxLayout(right_widget)
        self.right_panel.setSpacing(12)

        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.setSizes([350, 750])

        # Add buttons
        add_buttons_layout = QHBoxLayout()
        btn_add = QPushButton("Добавить видео")
        btn_folder = QPushButton("Добавить папку")
        btn_clear = QPushButton("Очистить")
        add_buttons_layout.addWidget(btn_add)
        add_buttons_layout.addWidget(btn_folder)
        add_buttons_layout.addWidget(btn_clear)
        self.left_panel.addLayout(add_buttons_layout)

        # Video list
        self.video_list_widget = DropListWidget(parent=self)
        self.video_list_widget.customContextMenuRequested.connect(self.on_list_menu)
        self.left_panel.addWidget(self.video_list_widget)

        dnd_label = QLabel("Перетащите файлы или папки сюда")
        dnd_label.setObjectName("dnd_label")
        dnd_label.setAlignment(Qt.AlignCenter)
        self.left_panel.addWidget(dnd_label)

        # Tabs
        tab_widget = QTabWidget()
        # Ширину вкладки Qt считает по шрифту виджета, а рисует полужирным из
        # стилей — на «Трансформации» разница в три пикселя срезала левый край
        # первой буквы. Ставим тот же вес и виджету.
        tab_font = tab_widget.tabBar().font()
        tab_font.setWeight(QFont.DemiBold)
        tab_widget.tabBar().setFont(tab_font)
        self.right_panel.addWidget(tab_widget)

        main_tab = QWidget()
        transform_tab = QWidget()
        effects_tab = QWidget()
        audio_tab = QWidget()

        # Каждая вкладка внутри прокрутки: настроек много, а экраны бывают
        # 1366x768 — без неё нижние группы просто не помещались бы в окно.
        def add_scrollable_tab(page, title):
            area = QScrollArea()
            area.setWidgetResizable(True)
            area.setFrameShape(QFrame.NoFrame)
            area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            area.setWidget(page)
            tab_widget.addTab(area, title)

        add_scrollable_tab(main_tab, "Меню")
        add_scrollable_tab(transform_tab, "Трансформация")
        # Вкладка «Наложение» убрана: разделение экрана и субтитры переехали на
        # первую, а баннер — к трансформациям.
        add_scrollable_tab(audio_tab, "Аудио")

        main_tab_layout = QVBoxLayout(main_tab)
        transform_tab_layout = QVBoxLayout(transform_tab)
        effects_tab_layout = QVBoxLayout(effects_tab)
        audio_tab_layout = QVBoxLayout(audio_tab)

        # === MAIN TAB ===
        # Одиннадцать групп настроек одинаковой важности пугают новичка.
        # Обязательное остаётся на виду, остальное открывается по требованию.
        density_row = QHBoxLayout()
        density_row.setSpacing(16)

        density_row.addWidget(QLabel("Сценарий:"))
        self.scenario_combo = QComboBox()
        for name in SCENARIOS:
            self.scenario_combo.addItem(name)
        self.scenario_combo.setToolTip(
            "Готовый набор значений под площадку. Дальше можно ничего не трогать.")
        density_row.addWidget(self.scenario_combo, 1)

        main_tab_layout.addLayout(density_row)

        self.output_format_group = QGroupBox("Формат и кодирование")
        ofg_layout = QVBoxLayout(self.output_format_group)
        ofg_layout.addWidget(QLabel("Формат вывода:"))
        self.output_format_combo = QComboBox()
        self.output_format_combo.addItems(OUTPUT_FORMATS)
        self.output_format_combo.currentTextChanged.connect(self.on_output_format_changed)
        ofg_layout.addWidget(self.output_format_combo)
        self.uniquify_checkbox = QCheckBox("Уникализировать при обработке")
        self.uniquify_checkbox.setToolTip(
            "Незаметные изменения, свои для каждого файла: срез долей секунды "
            "с начала и конца, сдвиг тона звука до 0,6%, своё качество "
            "сжатия и размер группы кадров.")
        ofg_layout.addWidget(self.uniquify_checkbox)
        uniquify_hint = QLabel(
            "Меняет отпечаток файла и звука, на глаз и на слух не заметно. "
            "Отражение, поворот и цветокоррекцию сюда не включили намеренно: "
            "модели поиска копий обучены на них и не реагируют.")
        uniquify_hint.setWordWrap(True)
        uniquify_hint.setObjectName("subtitleLabel")
        ofg_layout.addWidget(uniquify_hint)

        self.blur_background_checkbox = QCheckBox("Размыть фон")
        self.blur_background_checkbox.setToolTip("Заполняет черные полосы размытой версией видео (только для Reels)")
        self.blur_background_checkbox.setEnabled(False)
        ofg_layout.addWidget(self.blur_background_checkbox)
        ofg_layout.addWidget(QLabel("Видеокодек:"))
        self.codec_combo = QComboBox()
        for label, codec_value in CODECS.items():
            # Значение храним в данных пункта: подпись меняется после проверки.
            self.codec_combo.addItem(label, codec_value)
        self.codec_combo.setToolTip("Проверка доступных кодеков...")
        ofg_layout.addWidget(self.codec_combo)

        # Какие кодировщики реально работают, выясняем в фоне: каждая проверка
        # запускает ffmpeg, а на старте это заметная задержка.
        self.codec_probe = CodecProbeWorker()
        self.codec_probe.finished_signal.connect(self.on_codecs_detected)
        self.codec_probe.start()
        main_tab_layout.addWidget(self.output_format_group)

        preview_group = QGroupBox("Предпросмотр")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_label = QLabel("Выберите видео и нажмите 'Обновить'")
        self.preview_label.setObjectName("previewLabel")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(220)
        preview_layout.addWidget(self.preview_label)
        self.preview_button = QPushButton("Обновить предпросмотр")
        preview_layout.addWidget(self.preview_button)
        # Предпросмотр и группы первого уровня добавляются ниже, после того как
        # они созданы: разделение экрана и субтитры собираются на первой
        # вкладке, чтобы новичок видел всё нужное на одном экране.
        self.preview_group = preview_group

        # === TRANSFORM TAB ===
        self.crop_group = QGroupBox("Обрезка")
        crop_layout = QVBoxLayout(self.crop_group)
        self.auto_crop_checkbox = QCheckBox("Обрезать черные полосы (интеллектуально)")
        self.auto_crop_checkbox.setToolTip("Автоматически определяет и обрезает киношные черные полосы в видео")
        crop_layout.addWidget(self.auto_crop_checkbox)
        transform_tab_layout.addWidget(self.crop_group)

        self.filter_group = QGroupBox("Фильтры")
        f_lay = QVBoxLayout(self.filter_group)
        f_lay.addWidget(QLabel(
            "Можно отметить несколько — они применятся один за другим, сверху вниз."))
        self.filter_list = QListWidget()
        # Галочки вместо выделения: несколько фильтров можно было выбрать и
        # раньше, но только через Ctrl+клик, о чём никто не догадывался.
        self.filter_list.setSelectionMode(QAbstractItemView.NoSelection)
        # Клик по названию тоже переключает фильтр: попадать в квадратик
        # размером в двенадцать пикселей — лишняя работа для человека.
        self.filter_list.itemClicked.connect(self.on_filter_clicked)
        for group_name, names in FILTER_GROUPS:
            header = QListWidgetItem(group_name.upper())
            header.setFlags(Qt.NoItemFlags)
            font = header.font()
            font.setWeight(QFont.Bold)
            font.setPointSize(max(1, font.pointSize() - 1))
            header.setFont(font)
            # Заголовок группы отделяем цветом и фоном, а не только жирностью:
            # набранный тем же кеглем, он терялся среди самих фильтров.
            header.setForeground(QColor('#4ecdc4'))
            header.setBackground(QColor('#20242b'))
            self.filter_list.addItem(header)
            for name in names:
                if name not in FILTERS:
                    continue
                item = QListWidgetItem("    " + name)
                item.setData(Qt.UserRole, name)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                self.filter_list.addItem(item)
        self.filter_list.setMinimumHeight(300)
        f_lay.addWidget(self.filter_list)

        clear_filters_btn = QPushButton("Снять все фильтры")
        clear_filters_btn.clicked.connect(self.clear_filters)
        f_lay.addWidget(clear_filters_btn)
        transform_tab_layout.addWidget(self.filter_group)

        self.zoom_group = QGroupBox("Zoom (приближение)")
        zg_lay = QVBoxLayout(self.zoom_group)
        z_mode = QHBoxLayout()
        self.zoom_static_radio = QRadioButton("Статическое (%):")
        self.zoom_dynamic_radio = QRadioButton("Диапазон (%):")
        self.zoom_static_radio.setChecked(True)
        self.zoom_button_group = QButtonGroup()
        self.zoom_button_group.addButton(self.zoom_static_radio)
        self.zoom_button_group.addButton(self.zoom_dynamic_radio)
        self.zoom_button_group.buttonClicked.connect(self.on_zoom_mode_changed)
        z_mode.addWidget(self.zoom_static_radio)
        z_mode.addWidget(self.zoom_dynamic_radio)
        zg_lay.addLayout(z_mode)
        self.zoom_static_widget = QWidget()
        zsw_lay = QHBoxLayout(self.zoom_static_widget)
        zsw_lay.setContentsMargins(0, 0, 0, 0)
        self.zoom_static_spin = QSpinBox()
        self.zoom_static_spin.setRange(50, 300)
        self.zoom_static_spin.setValue(100)
        self.zoom_static_spin.setFixedWidth(80)
        zsw_lay.addWidget(self.zoom_static_spin)
        zsw_lay.addStretch()
        zg_lay.addWidget(self.zoom_static_widget)
        self.zoom_dynamic_widget = QWidget()
        zdd_lay = QHBoxLayout(self.zoom_dynamic_widget)
        zdd_lay.setContentsMargins(0, 0, 0, 0)
        self.zoom_min_spin = QSpinBox()
        self.zoom_min_spin.setRange(50, 300)
        self.zoom_min_spin.setValue(80)
        self.zoom_max_spin = QSpinBox()
        self.zoom_max_spin.setRange(50, 300)
        self.zoom_max_spin.setValue(120)
        zdd_lay.addWidget(QLabel("Мин:"))
        zdd_lay.addWidget(self.zoom_min_spin)
        zdd_lay.addWidget(QLabel("Макс:"))
        zdd_lay.addWidget(self.zoom_max_spin)
        zdd_lay.addStretch()
        zg_lay.addWidget(self.zoom_dynamic_widget)
        self.zoom_dynamic_widget.setVisible(False)
        transform_tab_layout.addWidget(self.zoom_group)

        self.speed_group = QGroupBox("Скорость")
        sp_lay = QVBoxLayout(self.speed_group)
        sp_mode = QHBoxLayout()
        self.speed_static_radio = QRadioButton("Статическое (%):")
        self.speed_dynamic_radio = QRadioButton("Диапазон (%):")
        self.speed_static_radio.setChecked(True)
        self.speed_button_group = QButtonGroup()
        self.speed_button_group.addButton(self.speed_static_radio)
        self.speed_button_group.addButton(self.speed_dynamic_radio)
        self.speed_button_group.buttonClicked.connect(self.on_speed_mode_changed)
        sp_mode.addWidget(self.speed_static_radio)
        sp_mode.addWidget(self.speed_dynamic_radio)
        sp_lay.addLayout(sp_mode)
        self.speed_static_widget = QWidget()
        ssw2 = QHBoxLayout(self.speed_static_widget)
        ssw2.setContentsMargins(0, 0, 0, 0)
        self.speed_static_spin = QSpinBox()
        self.speed_static_spin.setRange(50, 200)
        self.speed_static_spin.setValue(100)
        self.speed_static_spin.setFixedWidth(80)
        ssw2.addWidget(self.speed_static_spin)
        ssw2.addStretch()
        sp_lay.addWidget(self.speed_static_widget)
        self.speed_dynamic_widget = QWidget()
        sdy2 = QHBoxLayout(self.speed_dynamic_widget)
        sdy2.setContentsMargins(0, 0, 0, 0)
        self.speed_min_spin = QSpinBox()
        self.speed_min_spin.setRange(50, 200)
        self.speed_min_spin.setValue(90)
        self.speed_max_spin = QSpinBox()
        self.speed_max_spin.setRange(50, 200)
        self.speed_max_spin.setValue(110)
        sdy2.addWidget(QLabel("Мин:"))
        sdy2.addWidget(self.speed_min_spin)
        sdy2.addWidget(QLabel("Макс:"))
        sdy2.addWidget(self.speed_max_spin)
        sdy2.addStretch()
        sp_lay.addWidget(self.speed_dynamic_widget)
        self.speed_dynamic_widget.setVisible(False)
        transform_tab_layout.addWidget(self.speed_group)
        transform_tab_layout.addStretch()

        # === EFFECTS TAB ===
        self.split_group = QGroupBox("Разделение экрана (залипалка)")
        self.split_group.setCheckable(True)
        self.split_group.setChecked(False)
        split_lay = QVBoxLayout(self.split_group)

        split_hint = QLabel(
            "Кадр делится на две панели: ваш контент и зацикленное фоновое видео. "
            "Требуется формат Reels/TikTok.")
        split_hint.setWordWrap(True)
        split_lay.addWidget(split_hint)

        row_filler = QHBoxLayout()
        row_filler.addWidget(QLabel("Залипалка:"))
        self.filler_combo = QComboBox()
        for preset in list_filler_presets():
            self.filler_combo.addItem(os.path.splitext(os.path.basename(preset))[0], preset)
        self.filler_combo.addItem("Свой файл...", "")
        row_filler.addWidget(self.filler_combo, 1)
        split_lay.addLayout(row_filler)

        row_custom = QHBoxLayout()
        self.filler_path_edit = QLineEdit()
        self.filler_path_edit.setPlaceholderText("Путь к своему видео...")
        self.filler_browse_btn = QPushButton("Обзор")
        row_custom.addWidget(self.filler_path_edit)
        row_custom.addWidget(self.filler_browse_btn)
        self.filler_custom_widget = QWidget()
        self.filler_custom_widget.setLayout(row_custom)
        self.filler_custom_widget.setVisible(False)
        split_lay.addWidget(self.filler_custom_widget)

        row_split_layout = QHBoxLayout()
        row_split_layout.addWidget(QLabel("Пропорции:"))
        self.split_layout_combo = QComboBox()
        for layout_name in SPLIT_LAYOUTS:
            self.split_layout_combo.addItem(layout_name, SPLIT_LAYOUTS[layout_name])
        row_split_layout.addWidget(self.split_layout_combo, 1)
        split_lay.addLayout(row_split_layout)

        row_split_order = QHBoxLayout()
        row_split_order.addWidget(QLabel("Порядок:"))
        self.split_pos_combo = QComboBox()
        for position in SPLIT_POSITIONS:
            self.split_pos_combo.addItem(position)
        row_split_order.addWidget(self.split_pos_combo, 1)
        split_lay.addLayout(row_split_order)

        main_tab_layout.addWidget(self.split_group)

        self.overlay_group = QGroupBox("Наложение (баннер)")
        ov_lay = QVBoxLayout(self.overlay_group)
        row_ol = QHBoxLayout()
        self.overlay_path = QLineEdit()
        self.overlay_path.setPlaceholderText("Путь к файлу PNG, JPG, GIF...")
        btn_ol = QPushButton("Обзор")
        btn_clear_ol = QPushButton("X")
        btn_clear_ol.setFixedWidth(30)
        btn_clear_ol.setToolTip("Очистить поле наложения")
        row_ol.addWidget(QLabel("Файл:"))
        row_ol.addWidget(self.overlay_path)
        row_ol.addWidget(btn_ol)
        row_ol.addWidget(btn_clear_ol)
        ov_lay.addLayout(row_ol)
        row_pos = QHBoxLayout()
        row_pos.addWidget(QLabel("Расположение:"))
        self.overlay_pos_combo = QComboBox()
        for pos in OVERLAY_POSITIONS: self.overlay_pos_combo.addItem(pos)
        self.overlay_pos_combo.setCurrentText("Середина-Центр")
        row_pos.addWidget(self.overlay_pos_combo)
        row_pos.addStretch()
        ov_lay.addLayout(row_pos)
        transform_tab_layout.addWidget(self.overlay_group)

        self.subs_group = QGroupBox("Субтитры")
        subs_main_layout = QVBoxLayout(self.subs_group)
        self.subs_mode_group = QButtonGroup()
        subs_mode_layout = QHBoxLayout()
        self.subs_off_radio = QRadioButton("Выключены")
        self.subs_from_file_radio = QRadioButton("Из файла SRT")
        self.subs_generate_radio = QRadioButton("Сгенерировать (Whisper)")
        self.subs_off_radio.setChecked(True)
        self.subs_mode_group.addButton(self.subs_off_radio)
        self.subs_mode_group.addButton(self.subs_from_file_radio)
        self.subs_mode_group.addButton(self.subs_generate_radio)
        subs_mode_layout.addWidget(self.subs_off_radio)
        subs_mode_layout.addWidget(self.subs_from_file_radio)
        subs_mode_layout.addWidget(self.subs_generate_radio)
        subs_main_layout.addLayout(subs_mode_layout)
        self.subs_file_widget = QWidget()
        subs_file_layout = QHBoxLayout(self.subs_file_widget)
        subs_file_layout.setContentsMargins(0, 5, 0, 0)
        self.subs_srt_path = QLineEdit()
        self.subs_srt_path.setPlaceholderText("Путь к файлу .srt")
        btn_browse_srt = QPushButton("Обзор")
        subs_file_layout.addWidget(QLabel("Файл:"))
        subs_file_layout.addWidget(self.subs_srt_path)
        subs_file_layout.addWidget(btn_browse_srt)
        subs_main_layout.addWidget(self.subs_file_widget)
        self.subs_whisper_widget = QWidget()
        subs_whisper_layout = QVBoxLayout(self.subs_whisper_widget)
        subs_whisper_layout.setContentsMargins(0, 5, 0, 5)
        subs_whisper_layout.setSpacing(10)
        whisper_row1 = QHBoxLayout()
        whisper_row1.addWidget(QLabel("Модель:"))
        self.subs_model_combo = QComboBox()
        self.subs_model_combo.addItems(WHISPER_MODELS)
        self.subs_model_combo.setCurrentText("base")
        whisper_row1.addWidget(self.subs_model_combo)
        subs_whisper_layout.addLayout(whisper_row1)
        whisper_row2 = QHBoxLayout()
        whisper_row2.addWidget(QLabel("Язык:"))
        self.subs_lang_combo = QComboBox()
        self.subs_lang_combo.addItems(WHISPER_LANGUAGES)
        self.subs_lang_combo.setCurrentText("Russian")
        whisper_row2.addWidget(self.subs_lang_combo)
        subs_whisper_layout.addLayout(whisper_row2)
        whisper_row3 = QHBoxLayout()
        whisper_row3.addWidget(QLabel("Слов в строке:"))
        self.subs_words_spin = QSpinBox()
        self.subs_words_spin.setRange(1, 10)
        self.subs_words_spin.setValue(4)
        whisper_row3.addWidget(self.subs_words_spin)
        whisper_row3.addStretch()
        subs_whisper_layout.addLayout(whisper_row3)
        subs_main_layout.addWidget(self.subs_whisper_widget)

        common_style_layout = QHBoxLayout()
        common_style_layout.addWidget(QLabel("Размер (pt):"))
        self.subs_size_spin = QSpinBox()
        self.subs_size_spin.setRange(10, 100)
        self.subs_size_spin.setValue(36)
        common_style_layout.addWidget(self.subs_size_spin)

        self.subs_preview_btn = QPushButton("Предпросмотр стиля")
        self.subs_preview_btn.clicked.connect(self.on_subtitle_preview)
        self.subs_preview_btn.setEnabled(False)
        common_style_layout.addWidget(self.subs_preview_btn)
        common_style_layout.addStretch(1)
        subs_main_layout.addLayout(common_style_layout)

        main_tab_layout.addWidget(self.subs_group)
        main_tab_layout.addWidget(self.preview_group)
        main_tab_layout.addStretch()

        # === AUDIO TAB ===
        self.mute_group = QGroupBox("Управление звуком")
        mute_layout = QVBoxLayout(self.mute_group)
        self.mute_checkbox = QCheckBox("Удалить оригинальный звук из видео")
        mute_layout.addWidget(self.mute_checkbox)

        orig_vol_layout = QHBoxLayout()
        self.orig_vol_slider = QSlider(Qt.Horizontal)
        self.orig_vol_slider.setRange(0, 150)
        self.orig_vol_slider.setValue(100)
        self.orig_vol_label = QLabel("Громкость оригинала: 100%")
        self.orig_vol_slider.valueChanged.connect(lambda v: self.orig_vol_label.setText(f"Громкость оригинала: {v}%"))
        self.mute_checkbox.toggled.connect(lambda c: self.orig_vol_slider.setDisabled(c))
        orig_vol_layout.addWidget(self.orig_vol_label)
        orig_vol_layout.addWidget(self.orig_vol_slider)
        mute_layout.addLayout(orig_vol_layout)
        audio_tab_layout.addWidget(self.mute_group)

        self.overlay_audio_group = QGroupBox("Наложение аудио")
        overlay_audio_layout = QVBoxLayout(self.overlay_audio_group)

        ol_audio_path_layout = QHBoxLayout()
        self.overlay_audio_path_edit = QLineEdit()
        self.overlay_audio_path_edit.setPlaceholderText("Путь к аудиофайлу (MP3, WAV...)")
        browse_ol_audio_btn = QPushButton("Обзор")
        clear_ol_audio_btn = QPushButton("X")
        clear_ol_audio_btn.setFixedWidth(30)
        ol_audio_path_layout.addWidget(QLabel("Файл:"))
        ol_audio_path_layout.addWidget(self.overlay_audio_path_edit)
        ol_audio_path_layout.addWidget(browse_ol_audio_btn)
        ol_audio_path_layout.addWidget(clear_ol_audio_btn)
        overlay_audio_layout.addLayout(ol_audio_path_layout)

        over_vol_layout = QHBoxLayout()
        self.over_vol_slider = QSlider(Qt.Horizontal)
        self.over_vol_slider.setRange(0, 150)
        self.over_vol_slider.setValue(100)
        self.over_vol_label = QLabel("Громкость наложения: 100%")
        self.over_vol_slider.valueChanged.connect(lambda v: self.over_vol_label.setText(f"Громкость наложения: {v}%"))
        over_vol_layout.addWidget(self.over_vol_label)
        over_vol_layout.addWidget(self.over_vol_slider)
        overlay_audio_layout.addLayout(over_vol_layout)
        self.overlay_audio_path_edit.textChanged.connect(lambda t: self.over_vol_slider.setDisabled(not t))
        self.over_vol_slider.setDisabled(True)

        audio_tab_layout.addWidget(self.overlay_audio_group)
        audio_tab_layout.addStretch()

        # === BOTTOM CONTROLS ===
        self.process_button = QPushButton("Обработать")
        self.process_button.setObjectName("process_button")
        self.process_button.setFixedHeight(44)
        self.progress_label = QLabel("")
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.status_label = QLabel("")
        self.status_label.setObjectName("status_label")
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar, 1)

        self.watermark_label = QLabel()
        self.watermark_label.setText(
            f'Больше программ в Telegram-канале: '
            f'<a href="{links.TELEGRAM}">@magerdev1</a>'
            f' · <a href="{links.DONATE}">поддержать</a>'
            f' · <a href="{links.DONATE_UAH}">в гривнах</a>')
        self.watermark_label.setTextFormat(Qt.RichText)
        self.watermark_label.setOpenExternalLinks(True)
        self.watermark_label.setAlignment(Qt.AlignCenter)

        bottom_controls_layout = QVBoxLayout()
        bottom_controls_layout.addWidget(self.process_button)
        bottom_controls_layout.addLayout(progress_layout)
        bottom_controls_layout.addWidget(self.status_label)
        bottom_controls_layout.addWidget(self.watermark_label)
        self.right_panel.addLayout(bottom_controls_layout)

        # Connect signals
        btn_add.clicked.connect(self.on_add_files)
        btn_folder.clicked.connect(self.on_add_folder)
        btn_clear.clicked.connect(self.on_clear_list)
        btn_ol.clicked.connect(self.on_select_overlay)
        btn_clear_ol.clicked.connect(lambda: self.overlay_path.clear())
        self.filler_combo.currentIndexChanged.connect(self.on_filler_choice_changed)
        self.filler_browse_btn.clicked.connect(self.on_browse_filler)

        self.scenario_combo.currentIndexChanged.connect(self.apply_scenario)
        # Новичок видит три группы и кнопку «Обработать»; остальное по запросу.
        self.apply_density()
        self.apply_scenario()
        self.preview_button.clicked.connect(self.on_update_preview)
        btn_browse_srt.clicked.connect(self.on_browse_srt)
        self.subs_mode_group.buttonClicked.connect(self.on_subs_mode_changed)
        browse_ol_audio_btn.clicked.connect(self.on_browse_overlay_audio)
        clear_ol_audio_btn.clicked.connect(self.overlay_audio_path_edit.clear)
        self.process_button.clicked.connect(self.start_processing)

        self.on_subs_mode_changed()
        self.on_output_format_changed(self.output_format_combo.currentText())
        self.on_zoom_mode_changed()
        self.on_speed_mode_changed()
        self.video_list_widget.files_dropped.connect(self.refresh_video_list_display)
        self.subs_from_file_radio.toggled.connect(self.update_preview_btn_state)
        self.subs_srt_path.textChanged.connect(self.update_preview_btn_state)

    def update_preview_btn_state(self):
        is_file_mode = self.subs_from_file_radio.isChecked()
        has_srt = bool(self.subs_srt_path.text())
        self.subs_preview_btn.setEnabled(is_file_mode and has_srt)

    def on_subs_mode_changed(self):
        is_from_file = self.subs_from_file_radio.isChecked()
        is_generate = self.subs_generate_radio.isChecked()
        self.subs_file_widget.setVisible(is_from_file)
        self.subs_whisper_widget.setVisible(is_generate)

    def on_browse_srt(self):
        fs, _ = QFileDialog.getOpenFileName(self, "Выберите файл субтитров", "", "SRT Files (*.srt)")
        if fs: self.subs_srt_path.setText(fs)

    def on_browse_overlay_audio(self):
        fs, _ = QFileDialog.getOpenFileName(self, "Выберите аудиофайл", "", "Audio Files (*.mp3 *.wav *.m4a *.aac)")
        if fs: self.overlay_audio_path_edit.setText(fs)

    def on_update_preview(self):
        selected_items = self.video_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Видео не выбрано", "Пожалуйста, выберите видео из списка для предпросмотра.")
            return

        in_path = selected_items[0].data(Qt.UserRole)
        temp_preview_path = os.path.join(self.parent_window.temp_dir, f"preview_{uuid.uuid4()}.png")

        crop_filter = None
        if self.auto_crop_checkbox.isChecked():
            self.preview_label.setText("Анализ кадра для обрезки...")
            QApplication.processEvents()
            try:
                crop_filter = detect_crop_dimensions(in_path)
            except Exception as e:
                self.on_preview_error(f"Не удалось определить размеры обрезки: {e}")
                return

        params = {
            'in_path': in_path,
            'out_path': temp_preview_path,
            'filters': self.selected_filters(),
            'zoom_p': self.zoom_static_spin.value(),
            'overlay_file': self.overlay_path.text().strip() or None,
            'overlay_pos': self.overlay_pos_combo.currentText(),
            'output_format': self.output_format_combo.currentText(),
            'blur_background': self.blur_background_checkbox.isChecked(),
            'crop_filter': crop_filter,
            'filler_path': self.get_filler_path(),
            'split_content_height': self.split_layout_combo.currentData(),
            'content_on_top': self.split_pos_combo.currentText() == SPLIT_CONTENT_TOP
        }
        self.set_controls_enabled(False)
        self.preview_label.setText("Генерация предпросмотра...")
        self.parent_window.temp_files.append(temp_preview_path)

        self.preview_thread = PreviewWorker(params)
        self.preview_thread.finished_signal.connect(self.on_preview_finished)
        self.preview_thread.error_signal.connect(self.on_preview_error)
        self.preview_thread.start()

    def on_preview_finished(self, image_path):
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            self.preview_label.setPixmap(
                pixmap.scaled(self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.preview_label.setText("Ошибка: файл предпросмотра не найден")
        self.set_controls_enabled(True)

    def on_preview_error(self, error_msg):
        self.preview_label.setText("Ошибка генерации предпросмотра")
        QMessageBox.critical(self, "Ошибка предпросмотра", f"Не удалось создать предпросмотр:\n\n{error_msg}")
        self.set_controls_enabled(True)

    def set_controls_enabled(self, enabled):
        self.process_button.setEnabled(enabled)
        self.preview_button.setEnabled(enabled)
        self.video_list_widget.setEnabled(enabled)

    def on_output_format_changed(self, format_text):
        is_reels = (format_text == REELS_FORMAT_NAME)
        self.blur_background_checkbox.setEnabled(is_reels)
        if not is_reels: self.blur_background_checkbox.setChecked(False)

    def on_list_menu(self, pos: QPoint):
        menu = QMenu()
        act_del = menu.addAction("Удалить выделенное")
        act_clear = menu.addAction("Очистить список")
        chosen = menu.exec_(self.video_list_widget.viewport().mapToGlobal(pos))
        if chosen == act_del:
            selected_items = self.video_list_widget.selectedItems()
            if selected_items:
                for it in reversed(selected_items):
                    self.video_list_widget.takeItem(self.video_list_widget.row(it))
                self.refresh_video_list_display()
        elif chosen == act_clear:
            self.on_clear_list()

    def on_clear_list(self):
        self.video_list_widget.clear()
        self.refresh_video_list_display()

    # Уровень 1 остаётся на виду всегда: формат, разделение экрана и субтитры
    # определяют результат сильнее прочего. Уровень 2 — то, к чему обращаются
    # изредка. Уровень 3 — тонкая настройка, которая новичку только мешает.
    def _level_two_groups(self):
        return (self.crop_group, self.filter_group, self.speed_group,
                self.mute_group)

    def _level_three_groups(self):
        return (self.zoom_group, self.overlay_group, self.overlay_audio_group)

    def on_filter_clicked(self, item):
        if not item.data(Qt.UserRole):
            return
        item.setCheckState(Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked)

    def selected_filters(self):
        """Отмеченные фильтры в порядке их следования в списке."""
        names = []
        for row in range(self.filter_list.count()):
            item = self.filter_list.item(row)
            if item.data(Qt.UserRole) and item.checkState() == Qt.Checked:
                names.append(item.data(Qt.UserRole))
        return names

    def clear_filters(self):
        for row in range(self.filter_list.count()):
            item = self.filter_list.item(row)
            if item.data(Qt.UserRole):
                item.setCheckState(Qt.Unchecked)

    def apply_density(self):
        """Показывает все настройки: режим один, экспертный."""
        for group in self._level_two_groups() + self._level_three_groups():
            group.setVisible(True)

    def apply_scenario(self):
        """Заполнить настройки под выбранную площадку одним действием."""
        preset = SCENARIOS.get(self.scenario_combo.currentText(), {})
        if not preset:
            return

        if 'output_format' in preset:
            self.output_format_combo.setCurrentText(preset['output_format'])
        if 'blur_background' in preset and self.blur_background_checkbox.isEnabled():
            self.blur_background_checkbox.setChecked(preset['blur_background'])
        if 'auto_crop' in preset:
            self.auto_crop_checkbox.setChecked(preset['auto_crop'])
        if 'split' in preset:
            self.split_group.setChecked(preset['split'])
        if 'subtitles' in preset:
            # У субтитров режим выбирается переключателями, поэтому включаем
            # распознавание только когда сценарий его действительно требует.
            if preset['subtitles']:
                self.subs_generate_radio.setChecked(True)
            else:
                self.subs_off_radio.setChecked(True)
            self.on_subs_mode_changed()

    def on_codecs_detected(self, availability):
        if not availability:
            self.codec_combo.setToolTip(
                "Не удалось проверить кодеки. Если аппаратный не заработает, выберите CPU.")
            return

        model = self.codec_combo.model()
        working = []
        for index in range(self.codec_combo.count()):
            label = self.codec_combo.itemText(index)
            if availability.get(label):
                working.append(index)
                continue
            # Оставляем пункт видимым, но невыбираемым: так понятно, что кодек
            # существует, просто это железо его не поддерживает.
            item = model.item(index)
            if item is not None:
                item.setEnabled(False)
            self.codec_combo.setItemText(index, f"{label} — нет поддержки")

        if working and self.codec_combo.currentIndex() not in working:
            self.codec_combo.setCurrentIndex(working[0])

        hardware = [self.codec_combo.itemText(i) for i in working
                    if not self.codec_combo.itemText(i).startswith("CPU")]
        if hardware:
            self.codec_combo.setToolTip("Аппаратное ускорение доступно: " + ", ".join(hardware))
        else:
            # Частая причина - не отсутствие видеокарты, а устаревший драйвер:
            # свежие сборки ffmpeg требуют более новую версию NVENC API.
            self.codec_combo.setToolTip(
                "Аппаратное ускорение недоступно, обработка идёт на процессоре.\n"
                "Если видеокарта есть, обычно помогает обновление её драйвера.")

    def on_filler_choice_changed(self):
        # Пустые данные у пункта означают "Свой файл..."
        is_custom = not self.filler_combo.currentData()
        self.filler_custom_widget.setVisible(is_custom)

    def on_browse_filler(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите видео для залипалки", "",
            "Видео (*.mp4 *.mov *.avi *.mkv *.flv *.wmv);;Все файлы (*)")
        if path:
            self.filler_path_edit.setText(path)

    def get_filler_path(self):
        """Путь к фоновому ролику или None, если разделение экрана выключено."""
        if not self.split_group.isChecked():
            return None
        return self.filler_combo.currentData() or self.filler_path_edit.text().strip() or None

    def on_select_overlay(self):
        overlay_filter = "Файлы наложения (*.png *.jpg *.jpeg *.bmp *.gif);;Все файлы (*)"
        fs, _ = QFileDialog.getOpenFileNames(self, "Выберите файл для наложения (PNG, JPG, GIF)", "", overlay_filter)
        if fs: self.overlay_path.setText(fs[0])

    def on_add_files(self):
        file_filter = "Видео и GIF (*.mp4 *.mov *.avi *.mkv *.flv *.wmv *.gif);;Все файлы (*)"
        fs, _ = QFileDialog.getOpenFileNames(self, "Выберите видео или GIF", "", file_filter)
        if not fs: return
        added = False
        for f in fs:
            if (is_video_file(f) or f.lower().endswith('.gif')) and not self.video_list_widget.is_already_added(f):
                it = QListWidgetItem(f)
                it.setData(Qt.UserRole, f)
                self.video_list_widget.addItem(it)
                added = True
        if added: self.refresh_video_list_display()

    def on_add_folder(self):
        fol = QFileDialog.getExistingDirectory(self, "Выберите папку", "")
        if not fol: return
        vs = find_videos_in_folder(fol, include_gifs=True)
        added = False
        for v in vs:
            if not self.video_list_widget.is_already_added(v):
                it = QListWidgetItem(v)
                it.setData(Qt.UserRole, v)
                self.video_list_widget.addItem(it)
                added = True
        if added: self.refresh_video_list_display()

    def refresh_video_list_display(self):
        for i in range(self.video_list_widget.count()):
            it = self.video_list_widget.item(i)
            f = it.data(Qt.UserRole)
            base_name = os.path.basename(f)
            it.setText(f"{i + 1}. {base_name}")

    def on_zoom_mode_changed(self):
        is_dynamic = self.zoom_dynamic_radio.isChecked()
        self.zoom_static_widget.setVisible(not is_dynamic)
        self.zoom_dynamic_widget.setVisible(is_dynamic)

    def on_speed_mode_changed(self):
        is_dynamic = self.speed_dynamic_radio.isChecked()
        self.speed_static_widget.setVisible(not is_dynamic)
        self.speed_dynamic_widget.setVisible(is_dynamic)

    def start_processing(self):
        video_files = [self.video_list_widget.item(i).data(Qt.UserRole) for i in range(self.video_list_widget.count())]
        if not video_files:
            QMessageBox.warning(self, "Нет файлов", "Добавьте хотя бы один видео или GIF файл.")
            return
        out_dir = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения результатов")
        if not out_dir: return

        subtitle_settings = {"mode": "none"}
        if self.subs_from_file_radio.isChecked():
            subtitle_settings["mode"] = "srt_file"
            subtitle_settings["srt_path"] = self.subs_srt_path.text()
        elif self.subs_generate_radio.isChecked():
            subtitle_settings["mode"] = "whisper"
            subtitle_settings["model"] = self.subs_model_combo.currentText()
            subtitle_settings["language"] = self.subs_lang_combo.currentText()
            subtitle_settings["words_per_line"] = self.subs_words_spin.value()

        subtitle_settings["style"] = {"font_size": self.subs_size_spin.value()}

        self.processing_thread = Worker(
            files=video_files,
            filters=self.selected_filters(),
            zoom_mode='dynamic' if self.zoom_dynamic_radio.isChecked() else 'static',
            zoom_static=self.zoom_static_spin.value(),
            zoom_min=self.zoom_min_spin.value(),
            zoom_max=self.zoom_max_spin.value(),
            speed_mode='dynamic' if self.speed_dynamic_radio.isChecked() else 'static',
            speed_static=self.speed_static_spin.value(),
            speed_min=self.speed_min_spin.value(),
            speed_max=self.speed_max_spin.value(),
            overlay_file=self.overlay_path.text().strip() or None,
            overlay_pos=self.overlay_pos_combo.currentText(),
            out_dir=out_dir,
            mute_audio=self.mute_checkbox.isChecked(),
            output_format=self.output_format_combo.currentText(),
            blur_background=self.blur_background_checkbox.isChecked(),
            strip_metadata=self.parent_window.settings.get('strip_metadata', True),
            codec=self.codec_combo.currentData() or "libx264",
            subtitle_settings=subtitle_settings,
            auto_crop=self.auto_crop_checkbox.isChecked(),
            overlay_audio=self.overlay_audio_path_edit.text().strip() or None,
            original_volume=self.orig_vol_slider.value(),
            overlay_volume=self.over_vol_slider.value(),
            filler_path=self.get_filler_path(),
            split_content_height=self.split_layout_combo.currentData(),
            content_on_top=self.split_pos_combo.currentText() == SPLIT_CONTENT_TOP,
            uniquify=self.uniquify_checkbox.isChecked()
        )

        self.processing_thread.progress.connect(self.on_prog)
        self.processing_thread.file_progress.connect(self.on_file_prog)
        self.processing_thread.finished.connect(self.on_done)
        self.processing_thread.error.connect(self.on_err)
        self.processing_thread.file_processing.connect(self.on_file_processing)
        self.processing_thread.status_update.connect(self.on_status_update)

        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        self.progress_label.setText(f"0 / {len(video_files)}")
        self.status_label.setText("Подготовка...")
        self.set_controls_enabled(False)
        self.processing_thread.start()

    def on_prog(self, done, total):
        self.progress_label.setText(f"{done} / {total}")
        self.progress_bar.setValue(100)

    def on_file_prog(self, percentage):
        self.progress_bar.setValue(percentage)

    def on_file_processing(self, fname):
        try:
            fm = QFontMetrics(self.status_label.font())
            elided_text = fm.elidedText(f"Обрабатываю: {fname}", Qt.ElideMiddle, self.status_label.width() - 20)
            self.status_label.setText(elided_text)
            self.progress_bar.setValue(0)
        except Exception:
            self.status_label.setText(f"Обрабатываю: ...{fname[-30:]}")
            self.progress_bar.setValue(0)

    def on_status_update(self, message: str):
        self.status_label.setText(message)

    def on_done(self):
        if self.processing_thread and not self.processing_thread.isRunning():
            QMessageBox.information(self, "Готово", "Обработка успешно завершена!")
        self.set_controls_enabled(True)
        self.status_label.setText("Готово")
        self.processing_thread = None

    def on_err(self, msg):
        QMessageBox.critical(self, "Ошибка обработки", f"Произошла ошибка:\n\n{msg}")
        self.set_controls_enabled(True)
        self.status_label.setText("Ошибка")
        self.processing_thread = None

    def on_subtitle_preview(self):
        selected_items = self.video_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Нет видео", "Выберите видео для предпросмотра субтитров")
            return

        video_path = selected_items[0].data(Qt.UserRole)

        srt_path = None
        if self.subs_from_file_radio.isChecked():
            srt_path = self.subs_srt_path.text()
            if not srt_path or not os.path.exists(srt_path):
                QMessageBox.warning(self, "Нет SRT", "Укажите корректный файл субтитров .srt")
                return

        if not srt_path:
            QMessageBox.warning(self, "Режим не поддерживается",
                              "Предпросмотр доступен только для режима 'Из файла SRT'.\n"
                              "Сначала сгенерируйте субтитры или укажите готовый .srt файл.")
            return

        dialog = SubtitlePreviewDialog(video_path, srt_path, self)
        if dialog.exec_() == QDialog.Accepted:
            style = dialog.get_style()
            self.subs_size_spin.setValue(style.get('size', 36))


class VideoUnicApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.temp_dir = tempfile.mkdtemp(prefix="reels_maker_")
        self.temp_files = []
        self.settings = {
            'ffmpeg_path': '',
            'strip_metadata': True,
            'theme': 'Dark'
        }
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        # Подгоняемся под экран: 1150x800 не помещается на HD-ноутбуке, где
        # рабочая область около 1366x730.
        available = QApplication.primaryScreen().availableGeometry()
        width = min(1150, available.width() - 80)
        height = min(800, available.height() - 80)
        self.resize(width, height)
        self.move(available.left() + (available.width() - width) // 2,
                  available.top() + (available.height() - height) // 2)
        self.setMinimumSize(900, 560)

        icon_path = resource_path(os.path.join('resources', 'icon.png'))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Header bar
        header = QFrame()
        header.setObjectName("header_bar")
        header.setFixedHeight(56)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        # App title
        title = QLabel(APP_NAME)
        title.setObjectName("app_title")

        # Settings button
        self.settings_btn = QPushButton()
        self.settings_btn.setObjectName("settings_btn")
        self.settings_btn.setIcon(qta.icon('fa5s.cog', color='#a3a3a3'))
        self.settings_btn.setFixedSize(40, 40)
        self.settings_btn.setToolTip("Настройки")
        self.settings_btn.clicked.connect(self.show_settings_dialog)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.settings_btn)

        self.main_layout.addWidget(header)

        # Main content
        self.processing_widget = ProcessingWidgetContent(self)
        self.main_layout.addWidget(self.processing_widget)

        self.apply_stylesheet("Dark")

    def show_settings_dialog(self):
        dialog = SettingsDialog(self, self.settings)
        if dialog.exec_() == QDialog.Accepted:
            new_settings = dialog.get_settings()
            old_theme = self.settings.get('theme', 'Dark')
            self.settings = new_settings
            if new_settings['theme'] != old_theme:
                self.apply_stylesheet(new_settings['theme'])

    def apply_stylesheet(self, mode):
        QApplication.setStyle('Fusion')

        style_filename = "styles_dark.qss" if mode.lower() == "dark" else "styles_light.qss"
        path = resource_path(os.path.join('resources', style_filename))

        try:
            with open(path, "r", encoding="utf-8") as f:
                style = f.read()
                self.setStyleSheet(style)
        except FileNotFoundError:
            print(f"Stylesheet not found at {path}")
            self.setStyleSheet("")

    def _cleanup_temp_files(self):
        print("Cleaning up temporary files...")
        for f in self.temp_files:
            try:
                if os.path.exists(f): os.remove(f)
            except OSError as e:
                print(f"Error removing temp file {f}: {e}")
        self.temp_files.clear()
        try:
            if os.path.exists(self.temp_dir): shutil.rmtree(self.temp_dir)
        except OSError as e:
            print(f"Error removing temp directory {self.temp_dir}: {e}")

    def closeEvent(self, event):
        proc_thread = self.processing_widget.processing_thread
        is_running = proc_thread and proc_thread.isRunning()
        reply = QMessageBox.Yes
        if is_running:
            reply = QMessageBox.question(self, 'Подтверждение', "Идет обработка видео. Вы уверены, что хотите выйти?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            if is_running:
                try:
                    proc_thread.stop()
                    proc_thread.wait(1000)
                except Exception as e:
                    print(f"Error stopping worker thread: {e}")
            self._cleanup_temp_files()
            event.accept()
        else:
            event.ignore()
