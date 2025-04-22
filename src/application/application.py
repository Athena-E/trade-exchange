from abc import ABC, abstractmethod
import argparse
from datetime import datetime
import logging
from pathlib import Path
import signal
import sys
from types import FrameType
from typing import Any
import jsonschema
import json

logger = logging.getLogger(__name__)


class BaseApplication(ABC):
    def __init__(self, config_schema: Path, app_name: str | None = None) -> None:
        self._executable_name = Path(sys.argv[0]).absolute().name
        self._app_name = app_name or self._executable_name
        self._config_schema = _load_json(config_schema)
        
        self._init_args_parser()
        self._args = self._parser.parse_args()
        self._config_file = self._find_config_file_path()
        self._config = _load_json(self._config_file)
        self._validate_config()
        
        self._init_logging()
        logger.info(f"Config loaded: {json.dumps(self._config, indent=4)}")

    def run(self) -> None:
        """Call this method to run the application."""
        self._register_signal_handlers()
        try:
            logger.info("Starting application...")
            self._start()
            logger.info("Normal application exit, shutting down")
        except Exception:
            logger.exception("Oops, something went wrong.")
            logger.error("Shutting down")
            raise SystemExit(1)
    
    @abstractmethod
    def _start(self) -> None:
        """This method should be implemented by the subclass to start the application."""
        pass

    def _init_args_parser(self) -> None:
        self._parser = argparse.ArgumentParser()
        self._parser.add_argument("-c", "--config", help="(String) Path to config file to load", default=None)

    def _find_config_file_path(self) -> Path:
        if self._args.config is None:
            default_config_file = Path(sys.argv[0]).parent / f"{self._app_name}_config.json"
            logger.info(f"No config file specified, using default: {default_config_file}")
            return default_config_file
        return Path(self._args.config)

    def _validate_config(self) -> None:
        try:
            jsonschema.validate(instance=self._config, schema=self._config_schema)
        except jsonschema.ValidationError as e:
            raise SystemExit(f"Failed to validate config: {e}")

    def _init_logging(self) -> None:
        log_level_str = self._config["logLevel"]
        log_directory = Path(self._config["logDirectory"])
        log_file = log_directory / f"{self._app_name}_{datetime.now():%Y%m%d_%H%M%S}.log"
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            level=_get_log_level(log_level_str),
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        logger.info(f"Logging initialized. Log file: {log_file}")

    def _register_signal_handlers(self) -> None:
        signal.signal(signal.SIGINT, handler=self._shutdown)
        signal.signal(signal.SIGTERM, handler=self._shutdown)

    def _shutdown(self, signum: int, frame: FrameType | None) -> None:
        logger.info(f"Received signal {signal.Signals(signum).name} ({signum}) at frame {frame}, shutting down")
        raise SystemExit(0)


def _get_log_level(log_level_str: str) -> Any:
    logging_level = logging.getLevelNamesMapping().get(log_level_str)
    if logging_level is None:
        raise ValueError(f"Invalid log level: {log_level_str}")
    return logging_level


def _load_json(file: Path) -> dict:
    logger.debug(f"Loading JSON file: {file}")
    with file.open("r") as f:
        return json.load(f)
