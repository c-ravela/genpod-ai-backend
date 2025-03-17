"""We will use this module to implement all sanitization policies related to logs"""
import re
from typing import Any, Dict


def sanitize_log_message(message: str) -> str:
    # Sanitize API keys
    api_key_pattern = r'(api[_-]?key|access[_-]?token)["\']?\s*[:=]\s*["\']?([^\s"\']+)'
    message = re.sub(api_key_pattern, r'\1=<REDACTED>', message, flags=re.IGNORECASE)

    # Sanitize URLs (basic pattern, may need refinement based on your specific URLs)
    url_pattern = r'https?://[^\s]+'
    message = re.sub(url_pattern, '<REDACTED_URL>', message)

    return message

def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_log_message(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[key] = [sanitize_dict(item) if isinstance(item, dict) else 
                              sanitize_log_message(item) if isinstance(item, str) else item 
                              for item in value]
        else:
            sanitized[key] = value
    return sanitized
