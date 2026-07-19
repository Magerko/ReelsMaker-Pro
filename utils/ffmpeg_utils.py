# C:\Users\27030\Desktop\RLS\utils\ffmpeg_utils.py

import os
import subprocess
import random
import platform
import shlex
import shutil
import re
import tempfile
import uuid
from typing import List, Optional, Tuple, Dict, Callable
import logging

from .constants import (
    FFMPEG_EXE_PATH, FILTERS, OVERLAY_POSITIONS,
    REELS_WIDTH, REELS_HEIGHT, REELS_FORMAT_NAME,
    PRESETS_DIR, VIDEO_EXTENSIONS
)
from .path_utils import resource_path

logger = logging.getLogger(__name__)


def find_executable(base_path, exe_name):
    if os.path.exists(base_path):
        return base_path

    logging.info(f"Info: Executable not found at '{base_path}'. Trying system PATH for '{exe_name}'...")
    exe_in_path = shutil.which(exe_name)
    if exe_in_path:
        logging.info(f"Info: Using '{exe_name}' found in system PATH: {exe_in_path}")
        return exe_in_path

    logging.warning(f"Warning: '{exe_name}' not found at '{base_path}' or in system PATH.")
    return None


FFMPEG_PATH_BASE = resource_path(FFMPEG_EXE_PATH)
# ИСПРАВЛЕНО: Убран лишний .replace(), который ломал путь
FFPROBE_PATH_BASE = FFMPEG_PATH_BASE.replace("ffmpeg.exe", "ffprobe.exe")

FFMPEG_PATH_EFFECTIVE = find_executable(FFMPEG_PATH_BASE, "ffmpeg")
FFPROBE_PATH_EFFECTIVE = find_executable(FFPROBE_PATH_BASE, "ffprobe")


def run_ffmpeg(cmd: List[str], input_file_for_log: str = "input", duration: float = 0,
               progress_callback: Optional[Callable[[int], None]] = None):
    if not FFMPEG_PATH_EFFECTIVE:
        raise FileNotFoundError("FFmpeg executable not found. Cannot run command.")

    creationflags = 0
    startupinfo = None
    if platform.system() == "Windows":
        creationflags = subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

    final_cmd = [FFMPEG_PATH_EFFECTIVE]

    if "-loglevel" not in cmd:
        final_cmd.extend(["-loglevel", "debug"])
    if progress_callback:
        final_cmd.extend(["-progress", "pipe:1"])
    if "-hide_banner" not in cmd:
        final_cmd.append("-hide_banner")
    final_cmd.extend(cmd)
    command_for_log = ' '.join(shlex.quote(str(c)) for c in final_cmd)
    logging.info(f"Running FFmpeg command: {command_for_log}")
    try:
        process_cwd = os.path.dirname(FFMPEG_PATH_EFFECTIVE)

        process = subprocess.Popen(
            final_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace',
            creationflags=creationflags, startupinfo=startupinfo, bufsize=1,
            cwd=process_cwd
        )
        output_lines = []
        time_regex = re.compile(r"out_time_ms=(\d+)")
        while True:
            line = process.stdout.readline()
            if not line: break
            line = line.strip()
            if line:
                logging.debug(f"FFmpeg: {line}")
                output_lines.append(line)
                if progress_callback and duration > 0 and line.startswith("out_time_ms"):
                    match = time_regex.search(line)
                    if match:
                        elapsed_ms = int(match.group(1))
                        progress = int((elapsed_ms / (duration * 1000000)) * 100)
                        progress_callback(min(progress, 100))
        process.stdout.close()
        return_code = process.wait()
        if return_code != 0:
            error_message = (
                    f"FFmpeg failed with exit code {return_code} for file '{os.path.basename(input_file_for_log)}'.\n"
                    f"Command: {command_for_log}\n"
                    "Last lines of output:\n" + "\n".join(output_lines[-15:]))
            raise subprocess.CalledProcessError(return_code, final_cmd, output="\n".join(output_lines),
                                                stderr="\n".join(output_lines))
        logging.info(f"FFmpeg successfully processed '{os.path.basename(input_file_for_log)}'")
    except FileNotFoundError:
        raise FileNotFoundError(
            f"FFmpeg executable not found at '{FFMPEG_PATH_EFFECTIVE}'. Please ensure FFmpeg is installed and accessible.")
    except Exception as e:
        raise RuntimeError(
            f"An error occurred while running FFmpeg for file '{os.path.basename(input_file_for_log)}': {e}")


# ==============================================================================
# ИСПРАВЛЕННАЯ ВЕРСИЯ ФУНКЦИИ
# ==============================================================================
def detect_crop_dimensions(path: str) -> Optional[str]:
    """
    Определяет размеры обрезки, используя FFMPEG (а не FFPROBE), что является
    правильным подходом для применения видеофильтров.
    """
    logging.info(f"Detecting crop dimensions for {os.path.basename(path)} using ffmpeg...")

    if not FFMPEG_PATH_EFFECTIVE:
        error_msg = "FFmpeg executable not found. Cannot perform crop detection."
        logging.error(error_msg)
        raise FileNotFoundError(error_msg)

    try:
        # Используем FFMPEG, пропускаем первые 5 секунд (чтобы избежать титров)
        # и анализируем следующие 10 секунд. Это надежно и быстро.
        cmd = [
            FFMPEG_PATH_EFFECTIVE,
            "-hide_banner",
            "-ss", "5",
            "-t", "10",
            "-i", path,
            "-vf", "cropdetect=limit=24:round=16",
            "-an",
            "-f", "null",
            "-"
        ]

        # Результат cropdetect пишется в stderr.
        # Флаги скрытия обязательны: без них на каждое обновление
        # предпросмотра поверх окна мигает консоль.
        creationflags = 0
        startupinfo = None
        if platform.system() == "Windows":
            creationflags = subprocess.CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        process = subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            text=True,
            encoding='utf-8',
            errors='replace',
            creationflags=creationflags,
            startupinfo=startupinfo
        )
        _, stderr_output = process.communicate(timeout=60)

        # Ищем последнюю строку с результатом
        crop_lines = [line for line in stderr_output.split('\n') if 'crop=' in line]

        if not crop_lines:
            logging.warning(f"cropdetect found no crop values for {os.path.basename(path)}")
            return None

        last_crop_line = crop_lines[-1]
        crop_match = re.search(r'crop=(\d+:\d+:\d+:\d+)', last_crop_line)

        if crop_match:
            crop_params = crop_match.group(1)
            logging.info(f"Successfully detected crop dimensions: crop={crop_params}")
            return f"crop={crop_params}"  # Возвращаем готовую часть фильтра

        return None

    except Exception as e:
        logging.error(f"An error occurred during crop detection for {os.path.basename(path)}: {e}")
        return None


# ==============================================================================
# КОНЕЦ ИСПРАВЛЕННОЙ ВЕРСИИ ФУНКЦИИ
# ==============================================================================


def get_video_dimensions(path: str) -> Tuple[int, int]:
    if not FFPROBE_PATH_EFFECTIVE:
        logging.warning("ffprobe not found, cannot get video dimensions.")
        return 0, 0

    cmd = [FFPROBE_PATH_EFFECTIVE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
           "-of", "csv=s=x:p=0", path]
    try:
        creationflags = 0;
        startupinfo = None
        if platform.system() == "Windows": creationflags = subprocess.CREATE_NO_WINDOW; startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW; startupinfo.wShowWindow = subprocess.SW_HIDE

        process_cwd = os.path.dirname(FFPROBE_PATH_EFFECTIVE)

        result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace',
                                creationflags=creationflags, startupinfo=startupinfo, cwd=process_cwd)
        dims = result.stdout.strip().split('x')
        if len(dims) == 2:
            return int(dims[0]), int(dims[1])
        else:
            logging.warning(
                f"Warning: Could not parse dimensions from ffprobe output: '{result.stdout.strip()}' for file '{os.path.basename(path)}'");
            return 0, 0
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running ffprobe for '{os.path.basename(path)}': {e.stderr.strip()}");
        return 0, 0
    except FileNotFoundError:
        logging.error(f"Error: ffprobe executable not found at '{FFPROBE_PATH_EFFECTIVE}'.");
        return 0, 0
    except Exception as e:
        logging.error(f"Unexpected error getting dimensions for '{os.path.basename(path)}': {e}");
        return 0, 0


def get_video_duration(path: str) -> float:
    if not FFPROBE_PATH_EFFECTIVE:
        logging.warning("ffprobe not found, cannot get video duration.")
        return 0.0

    cmd = [FFPROBE_PATH_EFFECTIVE, "-v", "error", "-show_entries", "format=duration", "-of",
           "default=noprint_wrappers=1:nokey=1", path]
    try:
        creationflags = 0;
        startupinfo = None
        if platform.system() == "Windows": creationflags = subprocess.CREATE_NO_WINDOW; startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW; startupinfo.wShowWindow = subprocess.SW_HIDE

        process_cwd = os.path.dirname(FFPROBE_PATH_EFFECTIVE)

        result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace',
                                creationflags=creationflags, startupinfo=startupinfo, cwd=process_cwd)
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def probe_encoder(codec: str, timeout: int = 20) -> bool:
    """Проверяет, что кодировщик реально работает на этой машине.

    Списку `ffmpeg -encoders` доверять нельзя: сборки содержат nvenc, qsv и amf
    одновременно, независимо от установленного железа. Единственный надёжный
    признак — попытка закодировать кадр.
    """
    if not FFMPEG_PATH_EFFECTIVE:
        return False
    cmd = [
        FFMPEG_PATH_EFFECTIVE, "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=black:s=256x256:d=0.1",
        "-frames:v", "1", "-c:v", codec, "-f", "null", "-",
    ]
    try:
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        result = subprocess.run(
            cmd, capture_output=True, timeout=timeout,
            stdin=subprocess.DEVNULL, creationflags=creationflags)
        return result.returncode == 0
    except Exception as e:
        logger.warning(f"Encoder probe failed for {codec}: {e}")
        return False


def detect_available_codecs(codecs: Dict[str, str]) -> Dict[str, bool]:
    """Отображение "название в интерфейсе -> доступен ли кодировщик"."""
    availability = {}
    for label, codec in codecs.items():
        availability[label] = probe_encoder(codec)
        logger.info(f"Encoder {codec}: {'available' if availability[label] else 'unavailable'}")
    return availability


def build_split_screen_filter(
        content_node: str,
        filler_node: str,
        content_height: int,
        content_on_top: bool,
) -> str:
    """Складывает две панели в вертикальный кадр 1080x1920.

    Обе панели кадрируются по центру под свою высоту, а не вписываются с
    полями: залипалку принято показывать во всю ширину, без чёрных краёв.
    """
    target_w, target_h = REELS_WIDTH, REELS_HEIGHT
    content_h = max(2, min(target_h - 2, int(content_height)))
    content_h -= content_h % 2  # yuv420p не принимает нечётные размеры
    filler_h = target_h - content_h

    # setsar=1 обязателен: при разном пиксельном соотношении vstack
    # отказывается склеивать панели.
    panels = (
        f"{content_node}scale={target_w}:{content_h}:force_original_aspect_ratio=increase,"
        f"crop={target_w}:{content_h},setsar=1[sp_content];"
        f"{filler_node}scale={target_w}:{filler_h}:force_original_aspect_ratio=increase,"
        f"crop={target_w}:{filler_h},setsar=1[sp_filler];"
    )
    order = "[sp_content][sp_filler]" if content_on_top else "[sp_filler][sp_content]"
    return panels + f"{order}vstack=inputs=2[formatted]"


def list_filler_presets() -> List[str]:
    """Пути к фоновым роликам, поставляемым с программой."""
    folder = resource_path(PRESETS_DIR)
    if not os.path.isdir(folder):
        return []
    return sorted(
        os.path.join(folder, name)
        for name in os.listdir(folder)
        if os.path.splitext(name)[1].lower() in VIDEO_EXTENSIONS
    )


def build_uniquify_plan(in_path: str) -> Dict:
    """Разыгрывает незаметные изменения для одного файла.

    Отобраны те, что подтверждаются не только советами в блогах:

    * сдвиг тона и темпа — единственное, про что в исследованиях прямо
      сказано, что отпечаток звука их не переносит;
    * срез начала и конца сдвигает временную нарезку целиком;
    * перекодирование со своим качеством и своей группой кадров меняет
      каждый байт файла.

    Отражение, поворот и цветокоррекция сюда не входят намеренно: модели
    поиска копий обучают на этих же преобразованиях, то есть они по замыслу
    ничего не меняют в описателе. Они остались отдельными фильтрами — на
    случай, когда нужен именно вид, а не уникальность.

    Начало режем не глубже 0.4 с: первая секунда держит зрителя, и ради
    уникальности терять её нельзя.
    """
    return {
        'head': round(random.uniform(0.10, 0.40), 3),
        'tail': round(random.uniform(0.15, 0.60), 3),
        'pitch': round(random.uniform(0.994, 1.006), 4),
        'crf': random.randint(19, 23),
        'gop': random.choice([48, 50, 60, 72, 75]),
    }


def process_single(
        in_path: str,
        out_path: str,
        filters: List[str],
        zoom_p: int,
        speed_p: int,
        overlay_file: Optional[str],
        overlay_pos: str,
        output_format: str,
        blur_background: bool,
        mute_audio: bool = False,
        strip_metadata: bool = False,
        codec: str = "libx264",
        srt_path: Optional[str] = None,
        subtitle_style: Optional[Dict] = None,
        crop_filter: Optional[str] = None,
        overlay_audio_path: Optional[str] = None,
        original_volume: float = 1.0,
        overlay_volume: float = 1.0,
        filler_path: Optional[str] = None,
        split_content_height: int = 1080,
        content_on_top: bool = True,
        uniquify: bool = False,
        progress_callback: Optional[Callable[[int], None]] = None,
):
    is_gif_input = in_path.lower().endswith('.gif')
    # Значения разыгрываются на каждый файл заново. Постоянный набор правок
    # сам становится приметой: по ней вычисляли партии роликов из телеграм-ботов.
    unique = build_uniquify_plan(in_path) if uniquify else None
    is_gif_overlay = overlay_file and overlay_file.lower().endswith('.gif')
    cmd = []
    input_streams = []
    if is_gif_input:
        cmd.extend(["-stream_loop", "-1", "-i", in_path])
        input_streams.append({"type": "video", "index": 0, "path": in_path})
        has_real_audio = False
    else:
        if unique and unique['head'] > 0:
            cmd.extend(["-ss", f"{unique['head']:.3f}"])
        cmd.extend(["-i", in_path])
        input_streams.append({"type": "video+audio", "index": 0, "path": in_path})
        has_real_audio = True
    main_video_stream_label = f"[0:v]"
    main_audio_stream_label = f"[0:a]" if has_real_audio else None

    # Фоновый ролик для разделения экрана. Зацикливаем: залипалки обычно
    # короче исходного видео, а обрывать картинку на середине нельзя.
    # Длину ограничит -shortest по основному видео.
    filler_stream_label = None
    if filler_path and os.path.exists(filler_path):
        filler_index = len(input_streams)
        cmd.extend(["-stream_loop", "-1", "-i", filler_path])
        input_streams.append({"type": "filler", "index": filler_index, "path": filler_path})
        filler_stream_label = f"[{filler_index}:v]"

    overlay_stream_label = None
    if overlay_file and os.path.exists(overlay_file):
        overlay_input_index = len(input_streams)
        if is_gif_overlay:
            cmd.extend(["-stream_loop", "-1", "-i", overlay_file])
        else:
            cmd.extend(["-i", overlay_file])
        input_streams.append({"type": "overlay", "index": overlay_input_index, "path": overlay_file})
        overlay_stream_label = f"[{overlay_input_index}:v]"
    else:
        is_gif_overlay = False
    overlay_audio_stream_label = None
    if overlay_audio_path and os.path.exists(overlay_audio_path):
        overlay_audio_index = len(input_streams)
        cmd.extend(["-i", overlay_audio_path])
        input_streams.append({"type": "audio_overlay", "index": overlay_audio_index, "path": overlay_audio_path})
        overlay_audio_stream_label = f"[{overlay_audio_index}:a]"
    filter_complex_parts = []
    last_video_node = main_video_stream_label
    node_idx = 0
    if crop_filter:
        new_node_label = f"[v{node_idx}]"
        filter_complex_parts.append(f"{last_video_node}{crop_filter}{new_node_label}")
        last_video_node = new_node_label
        node_idx += 1
    target_w, target_h = REELS_WIDTH, REELS_HEIGHT
    is_reels_format = (output_format == REELS_FORMAT_NAME)
    use_split_screen = bool(filler_stream_label) and is_reels_format
    if is_reels_format:
        if use_split_screen:
            filter_complex_parts.append(
                build_split_screen_filter(
                    last_video_node, filler_stream_label,
                    split_content_height, content_on_top))
        elif blur_background:
            filter_complex_parts.append(
                f"{last_video_node}split[original][original_copy];"
                f"[original_copy]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
                f"crop={target_w}:{target_h}:(in_w-{target_w})/2:(in_h-{target_h})/2,"
                f"gblur=sigma=25[bg];"
                f"[original]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease[fg];"
                f"[bg][fg]overlay=x=(W-w)/2:y=(H-h)/2:shortest=1[formatted]"
            )
        else:
            filter_complex_parts.append(
                f"{last_video_node}scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
                f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:color=black[formatted]"
            )
        last_video_node = "[formatted]"
    for f_name in filters:
        f_template = FILTERS.get(f_name)
        if not f_template or f_name == "Нет фильтра":
            continue
        final_template = ""
        if f_name == "Случайный фильтр":
            possible_filters = [k for k, v in FILTERS.items() if
                                v and k not in ("Нет фильтра", "Случайный фильтр", "Случ. цвет (яркость/контраст/...")]
            if possible_filters:
                chosen_filter_name = random.choice(possible_filters)
                final_template = FILTERS[chosen_filter_name]
        elif f_name == "Случ. цвет (яркость/контраст/...)":
            br = random.uniform(-0.15, 0.15)
            ct = random.uniform(0.8, 1.2)
            sat = random.uniform(0.8, 1.3)
            hue = random.uniform(-5, 5)
            final_template = f_template.format(br=br, ct=ct, sat=sat, hue=hue)
        else:
            final_template = f_template
        if final_template:
            new_node_label = f"[v{node_idx}]"
            filter_complex_parts.append(f"{last_video_node}{final_template}{new_node_label}")
            last_video_node = new_node_label
            node_idx += 1
    zoom_factor = zoom_p / 100.0
    if abs(zoom_factor - 1.0) > 1e-5:
        if zoom_factor >= 1.0:
            scale_node = f"[v{node_idx}]";
            node_idx += 1
            filter_complex_parts.append(
                f"{last_video_node}scale=iw*{zoom_factor}:ih*{zoom_factor}:flags=bicubic{scale_node}")
            crop_node = f"[v{node_idx}]";
            node_idx += 1
            if is_reels_format:
                filter_complex_parts.append(
                    f"{scale_node}crop={target_w}:{target_h}:(in_w-{target_w})/2:(in_h-{target_h})/2{crop_node}")
            else:
                filter_complex_parts.append(
                    f"{scale_node}crop=iw/{zoom_factor}:ih/{zoom_factor}:(in_w-iw/{zoom_factor})/2:(in_h-ih/{zoom_factor})/2{crop_node}")
            last_video_node = crop_node
        else:
            scale_node = f"[v{node_idx}]"
            node_idx += 1
            filter_complex_parts.append(
                f"{last_video_node}scale=iw*{zoom_factor}:ih*{zoom_factor}:flags=bicubic{scale_node}")
            last_video_node = scale_node

    if srt_path and subtitle_style:
        sanitized_srt_path = srt_path.replace('\\', '/').replace(':', '\\:')
        font_size = subtitle_style.get("font_size", 36)

        position_code = 2
        vertical_margin = 70

        style_params = [
            f"Alignment={position_code}",
            f"MarginL=25",
            f"MarginR=25",
            f"MarginV={vertical_margin}",
            "FontName=Arial",
            f"FontSize={font_size}",
            "PrimaryColour=&HFFFFFF",
            "BorderStyle=1",
            "OutlineColour=&H000000",
            "Outline=2",
            "Shadow=1"
        ]

        style_string = r'\,'.join(style_params)

        new_node_label = f"[v{node_idx}]";
        node_idx += 1
        filter_complex_parts.append(
            f"{last_video_node}subtitles='{sanitized_srt_path}':force_style='{style_string}'{new_node_label}")
        last_video_node = new_node_label

    speed_factor = speed_p / 100.0
    audio_nodes_to_mix = []
    final_audio_node = None
    if has_real_audio and not mute_audio:
        vol_node = f"[a_orig_vol]"
        filter_complex_parts.append(f"{main_audio_stream_label}volume={original_volume}{vol_node}")
        audio_nodes_to_mix.append(vol_node)
    if overlay_audio_stream_label:
        vol_node = f"[a_over_vol]"
        filter_complex_parts.append(f"{overlay_audio_stream_label}volume={overlay_volume}{vol_node}")
        audio_nodes_to_mix.append(vol_node)
    if len(audio_nodes_to_mix) > 1:
        mixed_audio_node = f"[a_mixed]"
        filter_complex_parts.append(
            f"{''.join(audio_nodes_to_mix)}amix=inputs={len(audio_nodes_to_mix)}:duration=longest[a_mixed]")
        final_audio_node = mixed_audio_node
    elif len(audio_nodes_to_mix) == 1:
        final_audio_node = audio_nodes_to_mix[0]
    if final_audio_node and abs(speed_factor - 1.0) > 1e-5:
        speed_audio_node_in = final_audio_node
        tempo_filters = []
        current_tempo = speed_factor
        while current_tempo > 2.0: tempo_filters.append("atempo=2.0"); current_tempo /= 2.0
        min_tempo = 0.5
        while current_tempo < min_tempo: tempo_filters.append(f"atempo={min_tempo}"); current_tempo /= min_tempo
        if abs(current_tempo - 1.0) > 1e-5 and min_tempo <= current_tempo <= 2.0:
            tempo_filters.append(f"atempo={current_tempo}")
        if tempo_filters:
            audio_filters_str = ",".join(tempo_filters)
            new_audio_node = "[a_speed]"
            filter_complex_parts.append(f"{speed_audio_node_in}{audio_filters_str}{new_audio_node}")
            final_audio_node = new_audio_node
    if abs(speed_factor - 1.0) > 1e-5:
        new_node_label = f"[v_speed]";
        filter_complex_parts.append(f"{last_video_node}setpts=PTS/{speed_factor}{new_node_label}")
        last_video_node = new_node_label
    if overlay_stream_label:
        pos_params = OVERLAY_POSITIONS.get(overlay_pos, "x=(W-w)/2:y=(H-h)/2")
        alpha_node = f"[ovl{node_idx}]";
        node_idx += 1
        overlay_node = f"[v{node_idx}]";
        node_idx += 1
        filter_complex_parts.append(f"{overlay_stream_label}format=rgba{alpha_node}")
        filter_complex_parts.append(f"{last_video_node}{alpha_node}overlay={pos_params}{overlay_node}")
        last_video_node = overlay_node
    filter_complex_parts.append(f"{last_video_node}format=pix_fmts=yuv420p[vout]")
    if final_audio_node and unique:
        # Сдвиг тона — единственный приём из отобранных, про который в
        # исследованиях прямо сказано, что отпечаток звука его не переносит.
        # Меньше процента на слух не различимо.
        filter_complex_parts.append(
            f"{final_audio_node}rubberband=pitch={unique['pitch']}[apitch]")
        final_audio_node = '[apitch]'
    if final_audio_node:
        filter_complex_parts.append(f"{final_audio_node}anull[aout]")
    fc_string = ";".join(filter(None, filter_complex_parts))
    cmd.extend(["-filter_complex", fc_string])
    cmd.extend(["-map", "[vout]"])
    if final_audio_node:
        cmd.extend(["-map", "[aout]"])
        cmd.extend(["-c:a", "aac", "-b:a", "128k"])
    else:
        cmd.append("-an")
        if is_gif_input:
            cmd.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100", "-shortest"])
    cmd.extend(["-c:v", codec])
    quality = unique['crf'] if unique else 24
    if "nvenc" in codec or "amf" in codec:
        cmd.extend(["-cq", str(quality)])
    elif "qsv" in codec:
        cmd.extend(["-global_quality", str(quality)])
    else:
        cmd.extend(["-preset", "veryfast", "-crf", str(quality)])
    if unique:
        # Размер группы кадров меняет структуру потока, а не картинку.
        cmd.extend(["-g", str(unique['gop'])])
        if unique['tail'] > 0:
            source = get_video_duration(in_path)
            if source > 0:
                keep = source - unique['head'] - unique['tail']
                if keep > 1.0:
                    cmd.extend(["-t", f"{keep:.3f}"])
    if strip_metadata: cmd.extend(["-map_metadata", "-1", "-map_chapters", "-1"])
    # Залипалка подаётся с -stream_loop -1, поэтому без -shortest рендер не
    # закончится никогда: длину должно задавать основное видео.
    if use_split_screen or (not is_gif_input and not overlay_audio_path):
        cmd.append("-shortest")
    final_cmd = ["-y"] + cmd
    final_cmd.append(out_path)
    duration = get_video_duration(in_path)
    run_ffmpeg(final_cmd, input_file_for_log=in_path, duration=duration, progress_callback=progress_callback)


def generate_preview(
        in_path: str,
        out_path: str,
        filters: List[str],
        zoom_p: int,
        overlay_file: Optional[str],
        overlay_pos: str,
        output_format: str,
        blur_background: bool,
        crop_filter: Optional[str] = None,
        filler_path: Optional[str] = None,
        split_content_height: int = 1080,
        content_on_top: bool = True
):
    is_gif_input = in_path.lower().endswith('.gif')
    duration = get_video_duration(in_path)
    mid_point = duration / 2 if duration > 0 and not is_gif_input else 0
    cmd = ["-y"]
    if not is_gif_input:
        cmd.extend(["-ss", str(mid_point)])
    input_files = ["-i", in_path]
    has_filler = bool(filler_path) and os.path.exists(filler_path)
    if has_filler:
        input_files.extend(["-i", filler_path])
    if overlay_file and os.path.exists(overlay_file):
        input_files.extend(["-i", overlay_file])
    cmd.extend(input_files)
    filter_complex_parts = []
    main_video_stream_label = "[0:v]"
    filler_stream_label = "[1:v]" if has_filler else None
    overlay_index = 2 if has_filler else 1
    overlay_stream_label = (f"[{overlay_index}:v]"
                            if overlay_file and os.path.exists(overlay_file) else None)
    last_video_node = main_video_stream_label
    node_idx = 0
    if crop_filter:
        new_node_label = f"[v{node_idx}]"
        filter_complex_parts.append(f"{last_video_node}{crop_filter}{new_node_label}")
        last_video_node = new_node_label
        node_idx += 1
    target_w, target_h = REELS_WIDTH, REELS_HEIGHT
    is_reels_format = (output_format == REELS_FORMAT_NAME)
    if is_reels_format:
        if filler_stream_label:
            filter_complex_parts.append(
                build_split_screen_filter(
                    last_video_node, filler_stream_label,
                    split_content_height, content_on_top))
        elif blur_background:
            filter_complex_parts.append(
                f"{last_video_node}split[original][original_copy];"
                f"[original_copy]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
                f"crop={target_w}:{target_h}:(in_w-{target_w})/2:(in_h-{target_h})/2,"
                f"gblur=sigma=25[bg];"
                f"[original]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease[fg];"
                f"[bg][fg]overlay=x=(W-w)/2:y=(H-h)/2[formatted]"
            )
        else:
            filter_complex_parts.append(
                f"{last_video_node}scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
                f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:color=black[formatted]"
            )
        last_video_node = "[formatted]"
    is_random_filter_in_list = "Случайный фильтр" in filters
    for f_name in filters:
        f_template = FILTERS.get(f_name)
        if not f_template or f_name == "Нет фильтра":
            continue
        if is_random_filter_in_list and f_name != "Случайный фильтр":
            continue
        final_template = ""
        if f_name == "Случайный фильтр":
            final_template = FILTERS["Сепия"]
        elif f_name == "Случ. цвет (яркость/контраст/...)":
            br = 0.1;
            ct = 1.1;
            sat = 1.1;
            hue = 2
            final_template = f_template.format(br=br, ct=ct, sat=sat, hue=hue)
        else:
            final_template = f_template
        if final_template:
            new_node_label = f"[v{node_idx}]"
            filter_complex_parts.append(f"{last_video_node}{final_template}{new_node_label}")
            last_video_node = new_node_label
            node_idx += 1
    zoom_factor = zoom_p / 100.0
    if abs(zoom_factor - 1.0) > 1e-5:
        if zoom_factor >= 1.0:
            scale_node = f"[v{node_idx}]";
            node_idx += 1
            filter_complex_parts.append(
                f"{last_video_node}scale=iw*{zoom_factor}:ih*{zoom_factor}:flags=bicubic{scale_node}")
            crop_node = f"[v{node_idx}]";
            node_idx += 1
            if is_reels_format:
                filter_complex_parts.append(
                    f"{scale_node}crop={target_w}:{target_h}:(in_w-{target_w})/2:(in_h-{target_h})/2{crop_node}")
            else:
                filter_complex_parts.append(
                    f"{scale_node}crop=iw/{zoom_factor}:ih/{zoom_factor}:(in_w-iw/{zoom_factor})/2:(in_h-ih/{zoom_factor})/2{crop_node}")
            last_video_node = crop_node
        else:
            scale_node = f"[v{node_idx}]";
            node_idx += 1
            filter_complex_parts.append(
                f"{last_video_node}scale=iw*{zoom_factor}:ih*{zoom_factor}:flags=bicubic{scale_node}")
            last_video_node = scale_node
    if overlay_stream_label:
        pos_params = OVERLAY_POSITIONS.get(overlay_pos, "x=(W-w)/2:y=(H-h)/2")
        alpha_node = f"[ovl{node_idx}]";
        node_idx += 1
        overlay_node = f"[v{node_idx}]";
        node_idx += 1
        filter_complex_parts.append(f"{overlay_stream_label}format=rgba{alpha_node}")
        filter_complex_parts.append(f"{last_video_node}{alpha_node}overlay={pos_params}{overlay_node}")
        last_video_node = overlay_node
    filter_complex_parts.append(f"{last_video_node}format=rgba[vout]")
    fc_string = ";".join(filter(None, filter_complex_parts))
    if fc_string:
        cmd.extend(["-filter_complex", fc_string])
        cmd.extend(["-map", "[vout]"])
    cmd.extend(["-vframes", "1"])
    cmd.append(out_path)
    run_ffmpeg(cmd, input_file_for_log=in_path)
