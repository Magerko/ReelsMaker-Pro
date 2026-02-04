import os
import tempfile
import uuid
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QSpinBox, QGroupBox, QColorDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QColor
from utils.constants import SUBTITLE_PRESETS
from utils.ffmpeg_utils import run_ffmpeg, get_video_duration

class SubtitlePreviewGenerator(QThread):
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, video_path, srt_path, style_params, temp_output):
        super().__init__()
        self.video_path = video_path
        self.srt_path = srt_path
        self.style_params = style_params
        self.temp_output = temp_output

    def run(self):
        try:
            duration = get_video_duration(self.video_path)
            mid_point = duration / 2 if duration > 0 else 0

            sanitized_srt = self.srt_path.replace('\\', '/').replace(':', '\\:')

            font = self.style_params.get('font', 'Arial')
            size = self.style_params.get('size', 36)
            color = self.style_params.get('color', '#FFFFFF').replace('#', '&H') + '&'
            outline_color = self.style_params.get('outline_color', '#000000').replace('#', '&H') + '&'
            outline_width = self.style_params.get('outline_width', 2)
            shadow = self.style_params.get('shadow', 1)
            position = self.style_params.get('position', 2)
            bold = self.style_params.get('bold', False)

            style_string = (
                f"Alignment={position},"
                f"FontName={font},"
                f"FontSize={size},"
                f"PrimaryColour={color},"
                f"OutlineColour={outline_color},"
                f"Outline={outline_width},"
                f"Shadow={shadow},"
                f"Bold={1 if bold else 0}"
            )

            cmd = [
                "-y",
                "-ss", str(mid_point),
                "-i", self.video_path,
                "-vf", f"subtitles='{sanitized_srt}':force_style='{style_string}'",
                "-vframes", "1",
                self.temp_output
            ]

            run_ffmpeg(cmd, self.video_path)
            self.finished_signal.emit(self.temp_output)

        except Exception as e:
            self.error_signal.emit(str(e))

class SubtitlePreviewDialog(QDialog):
    def __init__(self, video_path, srt_path, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.srt_path = srt_path
        self.temp_files = []
        self.preview_thread = None
        self.current_style = SUBTITLE_PRESETS["Классический"].copy()

        self.setWindowTitle("Предпросмотр субтитров")
        self.setMinimumSize(900, 700)
        self.init_ui()
        self.update_preview()

    def init_ui(self):
        layout = QVBoxLayout(self)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(400)
        self.preview_label.setStyleSheet("border: 2px solid #7b2cbf; border-radius: 8px;")
        layout.addWidget(self.preview_label)

        controls_group = QGroupBox("Настройки стиля")
        controls_layout = QVBoxLayout(controls_group)

        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Пресет:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(SUBTITLE_PRESETS.keys())
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addStretch()
        controls_layout.addLayout(preset_layout)

        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Шрифт:"))
        self.font_combo = QComboBox()
        self.font_combo.addItems(["Arial", "Arial Black", "Impact", "Calibri", "Roboto", "Times New Roman", "Verdana"])
        self.font_combo.setCurrentText(self.current_style['font'])
        self.font_combo.currentTextChanged.connect(self.on_style_changed)
        font_layout.addWidget(self.font_combo)
        font_layout.addStretch()
        controls_layout.addLayout(font_layout)

        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Размер:"))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(20, 80)
        self.size_spin.setValue(self.current_style['size'])
        self.size_spin.valueChanged.connect(self.on_style_changed)
        size_layout.addWidget(self.size_spin)
        size_layout.addStretch()
        controls_layout.addLayout(size_layout)

        color_layout = QHBoxLayout()
        self.color_btn = QPushButton("Цвет текста")
        self.color_btn.clicked.connect(lambda: self.pick_color('color'))
        self.outline_color_btn = QPushButton("Цвет обводки")
        self.outline_color_btn.clicked.connect(lambda: self.pick_color('outline_color'))
        color_layout.addWidget(self.color_btn)
        color_layout.addWidget(self.outline_color_btn)
        color_layout.addStretch()
        controls_layout.addLayout(color_layout)

        outline_layout = QHBoxLayout()
        outline_layout.addWidget(QLabel("Толщина обводки:"))
        self.outline_spin = QSpinBox()
        self.outline_spin.setRange(0, 5)
        self.outline_spin.setValue(self.current_style['outline_width'])
        self.outline_spin.valueChanged.connect(self.on_style_changed)
        outline_layout.addWidget(self.outline_spin)
        outline_layout.addStretch()
        controls_layout.addLayout(outline_layout)

        position_layout = QHBoxLayout()
        position_layout.addWidget(QLabel("Позиция:"))
        self.position_combo = QComboBox()
        self.position_combo.addItems([
            "Верх-Лево (1)", "Верх-Центр (2)", "Верх-Право (3)",
            "Середина-Лево (4)", "Середина-Центр (5)", "Середина-Право (6)",
            "Низ-Лево (7)", "Низ-Центр (8)", "Низ-Право (9)"
        ])
        self.position_combo.setCurrentIndex(self.current_style['position'] - 1)
        self.position_combo.currentIndexChanged.connect(self.on_style_changed)
        position_layout.addWidget(self.position_combo)
        position_layout.addStretch()
        controls_layout.addLayout(position_layout)

        layout.addWidget(controls_group)

        buttons_layout = QHBoxLayout()
        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.update_preview)
        apply_btn = QPushButton("Применить")
        apply_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(refresh_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(apply_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)

    def on_preset_changed(self, preset_name):
        if preset_name in SUBTITLE_PRESETS:
            self.current_style = SUBTITLE_PRESETS[preset_name].copy()
            self.font_combo.setCurrentText(self.current_style['font'])
            self.size_spin.setValue(self.current_style['size'])
            self.outline_spin.setValue(self.current_style['outline_width'])
            self.position_combo.setCurrentIndex(self.current_style['position'] - 1)
            self.update_preview()

    def on_style_changed(self):
        self.current_style['font'] = self.font_combo.currentText()
        self.current_style['size'] = self.size_spin.value()
        self.current_style['outline_width'] = self.outline_spin.value()
        self.current_style['position'] = self.position_combo.currentIndex() + 1

    def pick_color(self, color_type):
        current_color = QColor(self.current_style.get(color_type, '#FFFFFF'))
        color = QColorDialog.getColor(current_color, self, f"Выберите цвет")
        if color.isValid():
            self.current_style[color_type] = color.name()
            self.update_preview()

    def update_preview(self):
        temp_output = os.path.join(tempfile.gettempdir(), f"sub_preview_{uuid.uuid4()}.png")
        self.temp_files.append(temp_output)

        self.preview_label.setText("Генерация предпросмотра...")
        self.preview_thread = SubtitlePreviewGenerator(
            self.video_path, self.srt_path, self.current_style, temp_output
        )
        self.preview_thread.finished_signal.connect(self.on_preview_ready)
        self.preview_thread.error_signal.connect(self.on_preview_error)
        self.preview_thread.start()

    def on_preview_ready(self, image_path):
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            self.preview_label.setPixmap(
                pixmap.scaled(self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        else:
            self.preview_label.setText("Ошибка загрузки")

    def on_preview_error(self, error_msg):
        self.preview_label.setText(f"Ошибка: {error_msg}")

    def get_style(self):
        return self.current_style

    def closeEvent(self, event):
        for f in self.temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except:
                pass
        event.accept()
