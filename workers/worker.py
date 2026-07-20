from PyQt5.QtCore import QThread, pyqtSignal
import os
import random
import subprocess
import uuid
from typing import List, Optional, Dict

from utils.ffmpeg_utils import process_single, detect_crop_dimensions
from utils.subtitle_utils import extract_audio, generate_srt_from_whisper


class Worker(QThread):
    progress = pyqtSignal(int, int)
    file_progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    file_processing = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(
            self,
            files: List[str],
            filters: List[str],
            zoom_mode: str,
            zoom_static: int,  # FIX: Added static zoom value
            zoom_min: int,
            zoom_max: int,
            speed_mode: str,
            speed_static: int,  # FIX: Added static speed value
            speed_min: int,
            speed_max: int,
            overlay_file: Optional[str],
            overlay_pos: str,
            out_dir: str,
            mute_audio: bool,
            output_format: str,
            blur_background: bool,
            strip_metadata: bool,
            codec: str,
            subtitle_settings: Dict,
            auto_crop: bool,
            overlay_audio: Optional[str],
            original_volume: int,
            overlay_volume: int,
            filler_path: Optional[str] = None,
            split_content_height: int = 1080,
            content_on_top: bool = True,
            uniquify: bool = False,
            uniquify_methods: dict = None,
    ):
        super().__init__()
        self.files = list(files)
        self.filters = list(filters)
        self.zoom_mode = zoom_mode
        self.zoom_static = zoom_static  # FIX: Store static zoom
        self.zoom_min = zoom_min
        self.zoom_max = zoom_max
        self.speed_mode = speed_mode
        self.speed_static = speed_static  # FIX: Store static speed
        self.speed_min = speed_min
        self.speed_max = speed_max
        self.overlay_file = overlay_file
        self.overlay_pos = overlay_pos
        self.out_dir = out_dir
        self.mute_audio = mute_audio
        self.output_format = output_format
        self.blur_background = blur_background
        self.strip_metadata = strip_metadata
        self.codec = codec
        self.subtitle_settings = subtitle_settings
        self.auto_crop = auto_crop
        self.overlay_audio = overlay_audio
        self.original_volume = original_volume / 100.0
        self.overlay_volume = overlay_volume / 100.0
        self.filler_path = filler_path
        self.split_content_height = split_content_height
        self.content_on_top = content_on_top
        self.uniquify = uniquify
        self.uniquify_methods = uniquify_methods or {}
        self._is_running = True
        self.output_paths = []

    def pick_zoom(self) -> int:
        # FIX: Correctly return static or dynamic value
        if self.zoom_mode == 'dynamic' and self.zoom_max >= self.zoom_min:
            try:
                return random.randint(self.zoom_min, self.zoom_max)
            except ValueError:
                return self.zoom_min  # Fallback for dynamic mode
        return self.zoom_static  # Return the correct static value

    def pick_speed(self) -> int:
        # FIX: Correctly return static or dynamic value
        if self.speed_mode == 'dynamic' and self.speed_max >= self.speed_min:
            try:
                return random.randint(self.speed_min, self.speed_max)
            except ValueError:
                return self.speed_min  # Fallback for dynamic mode
        return self.speed_static  # Return the correct static value

    def stop(self):
        self._is_running = False
        print("Worker stop requested.")

    def run(self):
        total_files = len(self.files)
        if total_files == 0:
            self.finished.emit()
            return

        try:
            os.makedirs(self.out_dir, exist_ok=True)
        except OSError as e:
            self.error.emit(f"Не удалось создать выходную папку: {self.out_dir}\nОшибка: {e}")
            return

        for i, in_file_path in enumerate(self.files):
            if not self._is_running:
                print("Worker stopped.")
                break

            base_name = os.path.basename(in_file_path)
            name_part, _ = os.path.splitext(base_name)
            suffix = "_reels" if self.output_format != "Оригинальный" else "_processed"
            out_file_name = f"{name_part}{suffix}.mp4"
            out_file_path = os.path.join(self.out_dir, out_file_name)

            if os.path.abspath(in_file_path) == os.path.abspath(out_file_path):
                alt_out_file_name = f"{name_part}{suffix}_output.mp4"
                out_file_path = os.path.join(self.out_dir, alt_out_file_name)
                print(f"Warning: Output path is same as input. Saving to: {alt_out_file_name}")

            self.file_processing.emit(base_name)
            self.file_progress.emit(0)

            srt_path = None
            temp_audio_path = None
            crop_filter = None

            try:
                if self.auto_crop:
                    self.status_update.emit("Анализ черных полос...")
                    crop_filter = detect_crop_dimensions(in_file_path)
                    self.status_update.emit("Обработка...")

                subtitle_mode = self.subtitle_settings.get("mode")
                if subtitle_mode == "whisper":
                    temp_dir = self.out_dir
                    temp_audio_path = os.path.join(temp_dir, f"{uuid.uuid4()}.wav")
                    srt_path = os.path.join(temp_dir, f"{uuid.uuid4()}.srt")

                    self.status_update.emit(f"Извлечение аудио из '{base_name}'...")
                    extract_audio(in_file_path, temp_audio_path)

                    self.status_update.emit("Распознавание речи...")
                    generate_srt_from_whisper(
                        audio_path=temp_audio_path,
                        srt_path=srt_path,
                        model_name=self.subtitle_settings.get("model"),
                        language=self.subtitle_settings.get("language"),
                        words_per_line=self.subtitle_settings.get("words_per_line"),
                        progress_callback=lambda p: self.status_update.emit(
                            f"Распознавание речи... {p}%")
                    )
                    self.file_processing.emit(base_name)
                elif subtitle_mode == "srt_file":
                    srt_path = self.subtitle_settings.get("srt_path")
                    if not srt_path or not os.path.exists(srt_path):
                        raise FileNotFoundError(f"Файл субтитров не найден: {srt_path}")

                current_zoom = self.pick_zoom()
                current_speed = self.pick_speed()

                process_single(
                    in_path=in_file_path,
                    out_path=out_file_path,
                    filters=self.filters,
                    zoom_p=current_zoom,
                    speed_p=current_speed,
                    overlay_file=self.overlay_file,
                    overlay_pos=self.overlay_pos,
                    output_format=self.output_format,
                    blur_background=self.blur_background,
                    mute_audio=self.mute_audio,
                    strip_metadata=self.strip_metadata,
                    codec=self.codec,
                    srt_path=srt_path,
                    subtitle_style=self.subtitle_settings.get("style", {}),
                    crop_filter=crop_filter,
                    overlay_audio_path=self.overlay_audio,
                    original_volume=self.original_volume,
                    overlay_volume=self.overlay_volume,
                    filler_path=(pick_random_filler()
                                 if self.filler_path == RANDOM_FILLER
                                 else self.filler_path),
                    split_content_height=self.split_content_height,
                    content_on_top=self.content_on_top,
                    uniquify=self.uniquify,
                    uniquify_methods=self.uniquify_methods,
                    progress_callback=self.file_progress.emit
                )
                self.output_paths.append(out_file_path)
                self.progress.emit(i + 1, total_files)

            except Exception as e:
                error_msg = f"Ошибка при обработке файла '{base_name}':\n{type(e).__name__}: {e}"
                if isinstance(e, subprocess.CalledProcessError) and e.output:
                    error_msg += f"\n\nFFmpeg output:\n{e.output[-500:]}"
                print(f"Error in worker thread: {error_msg}")
                self.error.emit(error_msg)
                continue

            finally:
                if temp_audio_path and os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)
                if srt_path and subtitle_mode == "whisper" and os.path.exists(srt_path):
                    os.remove(srt_path)

        if self._is_running:
            print("Worker finished processing all files.")
            self.finished.emit()
        else:
            print("Worker finished due to stop request.")
