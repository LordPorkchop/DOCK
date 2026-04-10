import configparser
import os
from threading import RLock


def parseValue(value: str):
    """Convert string to int, float, bool, or keep as string."""
    value = value.strip()

    lower = value.lower()
    if lower in ("true", "yes", "on"):
        return True
    if lower in ("false", "no", "off"):
        return False

    try:
        return int(value)
    except ValueError:
        pass

    try:
        return float(value)
    except ValueError:
        pass

    return value


def serializeValue(value):
    """Convert Python value to string for storage."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


class SectionProxy:
    def __init__(self, configObj, sectionName):
        object.__setattr__(self, "_configObj", configObj)
        object.__setattr__(self, "_sectionName", sectionName)

    def __getattr__(self, option):
        parser = self._configObj._parser #type: ignore

        if not parser.has_option(self._sectionName, option):
            raise AttributeError(f"Option '{option}' not found in section '{self._sectionName}'")

        rawValue = parser.get(self._sectionName, option)
        return parseValue(rawValue)

    def __setattr__(self, option, value):
        configObj = object.__getattribute__(self, "_configObj")
        sectionName = object.__getattribute__(self, "_sectionName")

        with configObj._lock:
            if not configObj._parser.has_section(sectionName):
                configObj._parser.add_section(sectionName)

            serialized = serializeValue(value)
            configObj._parser.set(sectionName, option, serialized)
            configObj.write()


class Config:
    def __init__(self, filePath="settings.cfg"):
        self._filePath = filePath
        self._parser = configparser.ConfigParser()
        self._parser.optionxform = str #type: ignore
        self._lock = RLock()

        if os.path.exists(self._filePath):
            self._parser.read(self._filePath)

    def __getattr__(self, section):
        if not self._parser.has_section(section):
            raise AttributeError(f"Section '{section}' not found")
        return SectionProxy(self, section)

    def __setattr__(self, name, value):
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            raise AttributeError(
                "Cannot assign directly to config. Use config.<section>.<option> = value"
            )

    def write(self):
        with open(self._filePath, "w") as f:
            self._parser.write(f)

    def reload(self):
        with self._lock:
            self._parser.read(self._filePath)

    def sections(self):
        return self._parser.sections()

    def hasSection(self, section):
        return self._parser.has_section(section)

    def addSection(self, section):
        with self._lock:
            if not self._parser.has_section(section):
                self._parser.add_section(section)
                self.write()


# Singleton instance
_configInstance = Config()


# Module-level access
def __getattr__(name):
    return getattr(_configInstance, name)


def __setattr__(name, value):
    return setattr(_configInstance, name, value)