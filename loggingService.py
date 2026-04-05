import logging
import sys


class Logger:
    _RESET = "\033[0m"
    _GRAY = "\033[1;90m"
    _BLUE = "\033[1;34m"
    _AMBER = "\033[1;38;5;214m"
    _RED = "\033[1;31m"
    _PURPLE = "\033[1;31m"

    _LEVEL_MAP = {
        logging.DEBUG: ("DBG", _GRAY),
        logging.INFO: ("INF", _BLUE),
        logging.WARNING: ("WRN", _AMBER),
        logging.ERROR: ("ERR", _RED),
        logging.CRITICAL: ("EXC", _PURPLE),
    }

    class _Formatter(logging.Formatter):
        def __init__(self, parent):
            super().__init__()
            self._parent = parent

            self._level_tag_map = {
                logging.DEBUG: f"{self._parent._GRAY}DBG{self._parent._RESET}",
                logging.INFO: f"{self._parent._BLUE}INF{self._parent._RESET}",
                logging.WARNING: f"{self._parent._AMBER}WRN{self._parent._RESET}",
                logging.ERROR: f"{self._parent._RED}ERR{self._parent._RESET}",
                logging.CRITICAL: f"{self._parent._PURPLE}{self._parent._RESET}",
            }
            self._exc_tag = f"{self._parent._PURPLE}EXC{self._parent._RESET}"

            self.format = self._format_level_only

        def _format_level_only(self, record):
            is_exception = record.exc_info is not None
            level_code = (
                self._exc_tag
                if is_exception
                else self._level_tag_map.get(
                    record.levelno, f"\033[1mUNK{self._parent._RESET}"
                )
            )

            timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
            timestamp += f".{int(record.msecs):03d}"
            origin = record.name
            message = record.getMessage()

            line = f"[{timestamp}][{origin}][{level_code}] {message}"
            if is_exception and record.exc_info:
                line += "\n" + self.formatException(record.exc_info)
            return line

        def format(self, record):
            is_exception = record.exc_info is not None
            level_code, color = (
                ("EXC", self._parent._DARK_RED_BOLD)
                if is_exception
                else self._parent._LEVEL_MAP.get(
                    record.levelno, ("UNK", self._parent._RESET)
                )
            )

            timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
            origin = record.name
            message = record.getMessage()

            line = f"[{timestamp}][{origin}][{level_code}] {message}"
            if is_exception:
                line = f"{color}{line}{self._parent._RESET}"
                if record.exc_info:
                    line += "\n" + self.formatException(record.exc_info)
            else:
                line = f"{color}{line}{self._parent._RESET}"
            return line

    def __init__(self, name=__name__, level=logging.DEBUG, stream=None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.propagate = False

        if not self.logger.handlers:
            handler = logging.StreamHandler(stream or sys.stdout)
            handler.setFormatter(self._Formatter(self))
            self.logger.addHandler(handler)

    def getLogger(self):
        return self.logger
