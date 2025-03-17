from typing import Any, Dict, List

from utils.logs.logging_utils import logger
from utils.yaml_utils import read_yaml


def load_instructions_from_yaml(filepath: str) -> Dict[str, str]:
    """
    Loads and aggregates instructions from a YAML configuration file.

    The YAML file should have an "instructions" key containing an array of objects.
    Each object must have:
      - 'template': A multi-line string representing the instruction text.
      - 'position': A string indicating where the instruction should be applied,
                    either "top" or "bottom". If not provided, "top" is assumed.

    This function concatenates all instructions by their designated positions and
    returns a dictionary with keys "top" and "bottom".

    Args:
        filepath (str): The path to the YAML file containing instructions.

    Returns:
        dict: A dictionary with keys "top" and "bottom" containing the aggregated instructions.

    Raises:
        Exception: Any exceptions during file reading or YAML parsing are logged and re-raised.
    """
    try:
        config = read_yaml(filepath)
        
        instructions_list: List[Dict[str, Any]] = config.get("instructions", [])
        top_instructions: List[str] = []
        bottom_instructions: List[str] = []
        
        for item in instructions_list:
            template = item.get("template", "").strip()
            # Default to "top" if no position is provided.
            position = item.get("position", "top").lower().strip()
            
            if position == "top":
                top_instructions.append(template)
            elif position == "bottom":
                bottom_instructions.append(template)
            else:
                logger.warning("Unknown position '%s' for instruction: %s", position, template)
        
        top_text = "\n".join(top_instructions)
        bottom_text = "\n".join(bottom_instructions)
        
        logger.info("Loaded instructions from %s", filepath)
        return {"top": top_text, "bottom": bottom_text}
    except Exception as e:
        logger.error("Failed to load instructions from %s: %s", filepath, e)
        raise
