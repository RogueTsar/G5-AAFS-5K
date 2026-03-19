import logging
import os
import json
from datetime import datetime

# Define base logs directory
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")

# Ensure the logs directory exists
os.makedirs(LOGS_DIR, exist_ok=True)

def get_agent_logger(agent_name: str) -> logging.Logger:
    """
    Creates or retrieves a logger configured to write to specifically {agent_name}.log
    inside the project `logs/` folder.
    """
    logger = logging.getLogger(agent_name)
    logger.setLevel(logging.INFO)
    
    # Check if handlers already exist to prevent duplicate logging
    if not logger.handlers:
        log_file = os.path.join(LOGS_DIR, f"{agent_name}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        
        # Format the log output
        formatter = logging.Formatter(
            '%(asctime)s - [%(name)s] - %(levelname)s\n%(message)s\n' + ('-' * 60)
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    return logger

def log_agent_action(agent_name: str, action: str, data: dict = None):
    """
    Utility wrapper to log an agent's execution step with formatted JSON properties.
    """
    logger = get_agent_logger(agent_name)
    
    if data is not None:
        try:
            formatted_data = json.dumps(data, indent=2, ensure_ascii=False)
            logger.info(f"{action}\nData payload:\n{formatted_data}")
        except TypeError:
            logger.info(f"{action}\nData payload: {str(data)}")
    else:
        logger.info(action)
