"""Собирает resources/styles_dark.qss и styles_light.qss из одного шаблона.

Приложение читает готовые .qss с диска — этот порядок не менялся. Менялось то,
что раньше две темы были двумя независимыми файлами по 420 строк: любая правка
в одном требовала ручного повторения в другом, и темы неизбежно расходились.

Значения из дизайн-системы семейства: бирюза #4ecdc4 — родовой акцент трёх
приложений, коралловый #ff6b6b — опасные действия, шкала 4/8/12/16/24/32.

Запуск: python tools/build_styles.py
"""
import os

DARK = {
    'bg': '#141519',
    'surface': '#1b1d21',
    'surface_alt': '#1c1e23',
    'raised': '#24272e',
    'raised_alt': '#2b2f37',
    'hover': '#2d313a',
    'border': '#3a3f49',
    'border_strong': '#4c525d',
    'text': '#e9ebee',
    'text_secondary': '#aab0ba',
    'text_muted': '#868c96',
    'accent': '#4ecdc4',
    'accent_deep': '#0d7c72',
    'accent_mid': '#0f8378',
    'accent_bg': '#12302c',
    'danger': '#ff6b6b',
    'disabled_text': '#565b63',
}

LIGHT = {
    'bg': '#f4f5f7',
    'surface': '#ffffff',
    'surface_alt': '#fafbfc',
    'raised': '#ffffff',
    'raised_alt': '#eef0f3',
    'hover': '#e6e9ed',
    'border': '#d5d9e0',
    'border_strong': '#b6bcc6',
    'text': '#1b1d21',
    'text_secondary': '#4c525d',
    'text_muted': '#7c828b',
    'accent': '#0f8378',
    'accent_deep': '#0d7c72',
    'accent_mid': '#4ecdc4',
    'accent_bg': '#e2f5f2',
    'danger': '#d64545',
    'disabled_text': '#aab0ba',
}

TEMPLATE = """/* Собрано автоматически из tools/build_styles.py — правьте шаблон, не этот файл. */

QMainWindow, QDialog {{
    background-color: {bg};
}}
QWidget {{
    color: {text};
    font-family: "Segoe UI", system-ui, sans-serif;
    font-size: 13px;
}}
QLabel {{
    background: transparent;
    color: {text};
}}
QLabel#app_title {{
    font-size: 17px;
    font-weight: 600;
    color: {text};
}}
QLabel#status_label {{
    color: {text_secondary};
}}
QLabel#dnd_label {{
    color: {text_muted};
    border: 1px dashed {border_strong};
    border-radius: 10px;
    padding: 18px;
}}
QLabel#previewLabel {{
    background-color: {surface_alt};
    border: 1px solid {border};
    border-radius: 10px;
    color: {text_muted};
}}
QLabel[text*="<a"] {{
    color: {accent};
}}
QFrame#header_bar {{
    background-color: {surface};
    border-bottom: 1px solid {border};
}}

QTabWidget::pane {{
    background-color: {surface};
    border: 1px solid {border};
    border-radius: 10px;
    top: -1px;
}}
QTabBar {{
    background: transparent;
}}
QTabBar::tab {{
    background: transparent;
    color: {text_secondary};
    padding: 8px 16px;
    margin-right: 6px;
    border: 1px solid transparent;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
}}
QTabBar::tab:hover {{
    background-color: {hover};
    color: {text};
}}
QTabBar::tab:selected {{
    background-color: {surface};
    color: {accent};
    border: 1px solid {border};
    border-bottom-color: {surface};
}}

QGroupBox {{
    background-color: {surface};
    border: 1px solid {border};
    border-radius: 10px;
    margin-top: 14px;
    padding: 16px 12px 12px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {accent};
}}

QPushButton {{
    background-color: {raised};
    color: {text};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 7px 16px;
    min-height: 18px;
}}
QPushButton:hover {{
    background-color: {hover};
    border-color: {border_strong};
}}
QPushButton:pressed {{
    background-color: {raised_alt};
}}
QPushButton:disabled {{
    background-color: {surface_alt};
    border-color: {border};
    color: {disabled_text};
}}
QPushButton#process_button, QPushButton#ok_button {{
    background-color: {accent_deep};
    border: 1px solid {accent_mid};
    color: #ffffff;
    font-weight: 600;
    padding: 9px 22px;
}}
QPushButton#process_button:hover, QPushButton#ok_button:hover {{
    background-color: {accent_mid};
}}
QPushButton#process_button:pressed {{
    background-color: {accent_deep};
}}
QPushButton#process_button:disabled {{
    background-color: {surface_alt};
    border-color: {border};
    color: {disabled_text};
}}
QPushButton#settings_btn {{
    background: transparent;
    border: none;
    padding: 6px;
    border-radius: 8px;
}}
QPushButton#settings_btn:hover {{
    background-color: {hover};
}}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit {{
    background-color: {surface_alt};
    color: {text};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: {accent_deep};
    selection-color: #ffffff;
}}
QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {{
    border-color: {border_strong};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QComboBox:focus, QPlainTextEdit:focus {{
    border-color: {accent};
}}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
    background-color: {surface};
    color: {disabled_text};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background-color: {raised};
    color: {text};
    border: 1px solid {border};
    border-radius: 8px;
    selection-background-color: {accent_bg};
    selection-color: {text};
    outline: none;
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background-color: {raised};
    border: none;
    width: 16px;
}}

QCheckBox, QRadioButton {{
    background: transparent;
    color: {text};
    spacing: 8px;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {border_strong};
    background-color: {surface_alt};
}}
QCheckBox::indicator {{
    border-radius: 4px;
}}
QRadioButton::indicator {{
    border-radius: 8px;
}}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {accent};
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {accent_deep};
    border-color: {accent};
}}
QCheckBox::indicator:disabled {{
    background-color: {surface};
    border-color: {border};
}}
/* Включатель у заголовка группы — ещё один отдельный элемент, третий по счёту
   после QCheckBox и QListWidget. Без своих правил он тоже чёрный по чёрному. */
QGroupBox::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid {border_strong};
    border-radius: 4px;
    background-color: {surface_alt};
}}
QGroupBox::indicator:hover {{
    border-color: {accent};
}}
QGroupBox::indicator:checked {{
    background-color: {accent_deep};
    border-color: {accent};
}}

/* Маркеры в списках — это QListWidget::indicator, отдельный элемент от
   QCheckBox::indicator. Без своих правил он рисуется системным стилем и на
   тёмном фоне выходит чёрным по чёрному. */
QListWidget::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid {border_strong};
    border-radius: 4px;
    background-color: {surface_alt};
}}
QListWidget::indicator:hover {{
    border-color: {accent};
}}
QListWidget::indicator:checked {{
    background-color: {accent_deep};
    border-color: {accent};
}}
/* Отмеченная, но неактивная галочка. Без этого правила предыдущее затирает
   заливку, и внутри выключенной группы выбор выглядит потерянным. */
QCheckBox::indicator:checked:disabled,
QRadioButton::indicator:checked:disabled {{
    background-color: {accent_bg};
    border-color: {border_strong};
}}

QListWidget {{
    background-color: {surface_alt};
    color: {text};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 4px;
    outline: none;
}}
QListWidget::item {{
    padding: 7px 10px;
    border-radius: 6px;
}}
QListWidget::item:hover {{
    background-color: {hover};
}}
QListWidget::item:selected {{
    background-color: {accent_bg};
    color: {text};
}}

QProgressBar {{
    background-color: {surface};
    border: 1px solid {border};
    border-radius: 7px;
    height: 14px;
    text-align: center;
    color: {text_secondary};
    font-size: 11px;
}}
QProgressBar::chunk {{
    background-color: {accent_deep};
    border-radius: 6px;
}}

QSlider::groove:horizontal {{
    background-color: {surface_alt};
    border: 1px solid {border};
    height: 5px;
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background-color: {accent};
    border: none;
    width: 15px;
    height: 15px;
    margin: -6px 0;
    border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{
    background-color: {accent_mid};
}}
QSlider::handle:horizontal:disabled {{
    background-color: {border_strong};
}}

QSplitter::handle {{
    background-color: {border};
}}
QSplitter::handle:hover {{
    background-color: {accent_deep};
}}

/* Область прокрутки и её содержимое рисуются обычным QWidget, а он берёт фон
   из системной палитры — на тёмной теме сквозь настройки просвечивала белая
   подложка. Оба уровня нужны: сама область и вложенная страница. */
QScrollArea {{
    background-color: {surface};
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background-color: {surface};
}}
QScrollBar:vertical {{
    background: transparent;
    width: 11px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background-color: {border};
    border-radius: 5px;
    min-height: 28px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {border_strong};
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 11px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background-color: {border};
    border-radius: 5px;
    min-width: 28px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {border_strong};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    height: 0;
    width: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
}}

QMenu {{
    background-color: {raised};
    color: {text};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{
    padding: 7px 18px;
    border-radius: 6px;
}}
QMenu::item:selected {{
    background-color: {accent_bg};
}}
QMessageBox {{
    background-color: {surface};
}}
QMessageBox QLabel {{
    color: {text};
    background: transparent;
}}
QToolTip {{
    background-color: {raised};
    color: {text};
    border: 1px solid {border_strong};
    border-radius: 6px;
    padding: 6px 8px;
}}
"""

if __name__ == '__main__':
    resources = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resources')
    for name, palette in (('styles_dark.qss', DARK), ('styles_light.qss', LIGHT)):
        path = os.path.join(resources, name)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(TEMPLATE.format(**palette))
        print(f'wrote {name}')
