#logging

import logging
import sys
from pathlib import Path
from .persistence import get_data_dir


def setup_logging() -> None:
    log_dir = get_data_dir()
    log_file = log_dir / "curlmonkey.log"
    
    #create formatter
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    #file handler
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    #console handler
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    #root logger
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    #reduce noise from qt
    logging.getLogger("PySide6").setLevel(logging.WARNING)

