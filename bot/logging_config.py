import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default_formatter": {
            "format": "%(asctime)s - [%(levelname)-8s] - %(name)s - %(message)s"
        },
    },
    "handlers": {
        "stream_handler": {
            "class": "logging.StreamHandler",
            "formatter": "default_formatter",
        },
        "rotating_file_handler": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/bot.log",
            "maxBytes": 1024 * 1024 * 5,
            "backupCount": 5,
            "formatter": "default_formatter",
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "root": {
            "handlers": ["stream_handler", "rotating_file_handler"],
            "level": "INFO",
            "propagate": True,
        },
        "urllib3": {
            "level": "WARNING",
            "propagate": False,
        },
        "selenium": {
            "level": "WARNING",
            "propagate": False,
        },
    },
}
