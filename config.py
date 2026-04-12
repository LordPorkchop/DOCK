from __future__ import annotations
from configparser import ConfigParser
from pathlib import Path
from threading import RLock
from typing import Any

_CONFIG_PATH = Path(__file__).with_name("settings.cfg")
_PARSER = ConfigParser()
_LOCK = RLock()
_LOADED = False


def _coerceValue(raw: str) -> Any:
    value = raw.strip()
    lowered = value.lower()

    if lowered in {"yes", "true", "on"}:
        return True
    if lowered in {"no", "off", "false"}:
        return False
    if lowered == "none":
        return None

    try:
        return int(value)
    except ValueError:
        pass

    try:
        return float(value)
    except ValueError:
        pass

    return value


def _serializeValue(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "none"
    return str(value)


def _ensureLoaded() -> None:
    global _LOADED

    if _LOADED:
        return

    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(f"settings file not found: {_CONFIG_PATH}")

    _PARSER.read(_CONFIG_PATH, encoding="utf-8")
    _LOADED = True


def _writeLocked() -> None:
    with _CONFIG_PATH.open("w", encoding="utf-8") as file:
        _PARSER.write(file)


class _SectionAccessor:
    __slots__ = ("_section",)

    def __init__(self, section: str):
        object.__setattr__(self, "_section", section)

    def __getattr__(self, option: str) -> Any:
        with _LOCK:
            _ensureLoaded()

            section = object.__getattribute__(self, "_section")
            if not _PARSER.has_section(section):
                raise AttributeError(f"unknown section: {section}")
            if not _PARSER.has_option(section, option):
                raise AttributeError(f"unknown option: {section}.{option}")

            return _coerceValue(_PARSER.get(section, option))

    def __setattr__(self, option: str, value: Any) -> None:
        if option == "_section":
            object.__setattr__(self, option, value)
            return

        update(object.__getattribute__(self, "_section"), option, value)

    def __repr__(self) -> str:
        return f"<ConfigSection {object.__getattribute__(self, '_section')}>"


def __getattr__(name: str) -> _SectionAccessor:
    with _LOCK:
        _ensureLoaded()

        if _PARSER.has_section(name):
            return _SectionAccessor(name)

    raise AttributeError(f"unknown config section: {name}")


def getValue(section: str, option: str) -> Any:
    with _LOCK:
        _ensureLoaded()

        if not _PARSER.has_section(section):
            raise KeyError(f"unknown section: {section}")
        if not _PARSER.has_option(section, option):
            raise KeyError(f"unknown option: {section}.{option}")

        return _coerceValue(_PARSER.get(section, option))


def update(section: str, option: str, newValue: Any) -> Any:
    with _LOCK:
        _ensureLoaded()

        if not _PARSER.has_section(section):
            _PARSER.add_section(section)

        _PARSER.set(section, option, _serializeValue(newValue))
        _writeLocked()

        return _coerceValue(_PARSER.get(section, option))


def setValue(section: str, option: str, value: Any) -> Any:
    return update(section, option, value)


def reload() -> None:
    global _LOADED

    with _LOCK:
        _PARSER.clear()
        _LOADED = False
        _ensureLoaded()
