from datetime import datetime


def get_timestamp() -> str:
    """
    Returns the current timestamp in the format `YYYY-MM-DD_HH-MM-SS-MS`.
        Ex: 
            `2024-07-26_16-41-25-057777`
    """
    
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
