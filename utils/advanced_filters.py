import random
from typing import Dict, Tuple

def get_rotation_filter(angle: float = None) -> str:
    if angle is None:
        angle = random.uniform(-3, 3)
    return f"rotate={angle}*PI/180:fillcolor=black@0"

def get_random_crop_offset() -> Tuple[int, int]:
    offset_x = random.randint(-20, 20)
    offset_y = random.randint(-20, 20)
    return offset_x, offset_y

def get_perspective_distortion() -> str:
    x0 = random.uniform(0, 20)
    y0 = random.uniform(0, 20)
    x1 = random.uniform(0, 20)
    y1 = random.uniform(0, 20)
    return f"perspective=x0={x0}:y0={y0}:x1=W-{x1}:y1={y1}:x2={x0}:y2=H-{y0}:x3=W-{x1}:y3=H-{y1}:sense=source"

def get_dynamic_zoom_filter(duration: float, start_zoom: float = 1.0, end_zoom: float = 1.2) -> str:
    return f"zoompan=z='min(zoom+0.0015,{end_zoom})':d={int(duration*25)}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920"

def get_chromatic_aberration() -> str:
    offset = random.uniform(1, 4)
    return f"split[main][tmp];[tmp]lutrgb=r=0[chroma];[main][chroma]blend=all_mode=addition:all_opacity=0.6"

def get_vignette_advanced() -> str:
    angle = random.uniform(3.14/5, 3.14/3)
    return f"vignette=angle={angle}"

def apply_random_advanced_filter() -> str:
    filters = [
        get_rotation_filter(),
        get_perspective_distortion(),
        get_chromatic_aberration(),
        get_vignette_advanced(),
    ]
    return random.choice(filters)

def get_metadata_randomizer() -> Dict[str, str]:
    import datetime
    import random

    random_date = datetime.datetime.now() - datetime.timedelta(
        days=random.randint(1, 365),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59)
    )

    cameras = [
        "iPhone 14 Pro", "Samsung Galaxy S23", "Canon EOS R5",
        "Sony A7III", "GoPro HERO11", "DJI Mavic 3"
    ]

    return {
        "creation_time": random_date.strftime("%Y-%m-%d %H:%M:%S"),
        "make": random.choice(cameras).split()[0],
        "model": random.choice(cameras),
        "software": f"v{random.randint(1,15)}.{random.randint(0,9)}.{random.randint(0,99)}"
    }

def get_micro_cuts_times(duration: float, num_cuts: int = 3) -> list:
    cuts = []
    for _ in range(num_cuts):
        cut_start = random.uniform(0.5, duration - 0.5)
        cut_duration = random.uniform(0.03, 0.08)
        cuts.append((cut_start, cut_duration))
    return sorted(cuts, key=lambda x: x[0])
