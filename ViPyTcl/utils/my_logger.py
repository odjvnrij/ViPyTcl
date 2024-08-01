# cython: language_level=3
import logging

root_logger = logging.getLogger()
root_logger.setLevel(0)
import os
import colorlog
import sys
import uuid
from datetime import date

today = date.today()
log_root = "./log"
random_uuid = str(uuid.uuid4())
date_str = "-".join((str(today.year), str(today.month), str(today.day)))
console_formatter = colorlog.ColoredFormatter(
    '%(log_color)s[%(levelname)s] [%(asctime)s] %(message)s',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }
)
file_formatter = logging.Formatter('[%(levelname)s] [%(asctime)s] %(message)s')


def set_log_root(root_path: str):
    global log_root
    log_root = root_path
    os.makedirs(log_root, exist_ok=True)


def get_console_logger(level: logging.DEBUG):
    return get_logger(use_stdout=True, use_file=False, stdout_level=level)


def get_logger(logger_name: str = "root",
               use_stdout: bool = True,
               use_file: bool = True,
               file_level: int = logging.INFO,
               stdout_level: int = logging.INFO):
    """
    创造一个logger
    :param logger_name: logger名字
    :param use_stdout: 是否输出到stdout
    :param use_file: 是否输出到文件
    :param file_level: 输出到文件的log等级
    :param stdout_level: 输出到stdout的log等级
    :return:
    """
    if logger_name in logging.Logger.manager.loggerDict:
        return logging.getLogger(logger_name)

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    if use_file:
        upper_folder_path = os.path.join(log_root, logger_name)
        os.makedirs(upper_folder_path, exist_ok=True)
        logger_full_path = os.path.join(upper_folder_path, random_uuid)
        file_handler = logging.FileHandler(filename=logger_full_path, mode="w", delay=True)
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(file_level)
        logger.addHandler(file_handler)

    if use_stdout:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(console_formatter)
        stream_handler.setLevel(stdout_level)
        logger.addHandler(stream_handler)

    return logger


class MockLogger:
    def __init__(self, default_recall: callable = print):
        self.default_recall = default_recall

    def info(self, *args, **kwargs):
        self.default_recall(*args, **kwargs)

    def debug(self, *args, **kwargs):
        self.default_recall(*args, **kwargs)

    def warning(self, *args, **kwargs):
        self.default_recall(*args, **kwargs)

    def error(self, *args, **kwargs):
        self.default_recall(*args, **kwargs)
