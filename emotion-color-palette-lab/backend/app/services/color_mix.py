from __future__ import annotations

import colorsys
import re
from typing import Iterable

HEX_RE = re.compile(r"^#?[0-9a-fA-F]{6}$")


def normalize_hex(value: str) -> str:
    cleaned = value.strip()
    if not HEX_RE.match(cleaned):
        raise ValueError(f"Invalid hex color: {value}")
    if not cleaned.startswith("#"):
        cleaned = f"#{cleaned}"
    return cleaned.upper()


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    hex_value = normalize_hex(value).lstrip("#")
    return (
        int(hex_value[0:2], 16),
        int(hex_value[2:4], 16),
        int(hex_value[4:6], 16),
    )


def rgb_to_hex(rgb: Iterable[int]) -> str:
    r, g, b = [max(0, min(255, int(round(channel)))) for channel in rgb]
    return f"#{r:02X}{g:02X}{b:02X}"


def rgb_to_hsl(rgb: Iterable[int]) -> list[float]:
    r, g, b = [channel / 255 for channel in rgb]
    h, lightness, saturation = colorsys.rgb_to_hls(r, g, b)
    return [round(h * 360), round(saturation, 3), round(lightness, 3)]


def mix_colors(hex_values: list[str]) -> dict:
    if not hex_values:
        raise ValueError("At least one color is required.")

    channels = [hex_to_rgb(value) for value in hex_values]
    count = len(channels)
    mixed_rgb = [
        round(sum(rgb[index] for rgb in channels) / count)
        for index in range(3)
    ]

    return {
        "hex": rgb_to_hex(mixed_rgb),
        "rgb": mixed_rgb,
        "hsl": rgb_to_hsl(mixed_rgb),
    }

