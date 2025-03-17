from pathlib import Path

from langchain_google_community import GoogleSearchAPIWrapper
from pydantic import BaseModel, Field

from models import WebSearchResults
from utils.logs.logging_utils import logger
from utils.yaml_utils import read_yaml

DEFAULT_CONFIG_PATH = Path("core/search/engines/google/google.yaml")


class GoogleSearchConfig(BaseModel):
    """
    Represents the configuration required for the Google Search API.
    """
    google_api_key: str = Field(..., description="Google API key.")
    google_cse_id: str = Field(..., description="Google Custom Search Engine ID.")

def load_google_search_config(config_path: Path = DEFAULT_CONFIG_PATH) -> GoogleSearchConfig:
    """
    Loads and returns the Google search configuration from a YAML file.

    Args:
        config_path (Path, optional): Path to the configuration YAML file.
                                      Defaults to DEFAULT_CONFIG_PATH.

    Returns:
        GoogleSearchConfig: Parsed configuration settings for the Google Search API.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        RuntimeError: If there is an error during loading or parsing the configuration.
    """
    if not config_path.is_file():
        logger.error(f"Configuration file not found: {config_path.resolve()}")
        raise FileNotFoundError(f"Configuration file not found: {config_path.resolve()}")

    try:
        config_data = read_yaml(str(config_path))
        google_config = GoogleSearchConfig(**config_data)
        logger.info(f"Successfully loaded Google search configuration from {config_path.resolve()}")
        return google_config
    except Exception as e:
        logger.exception("Failed to load or parse the Google search configuration.")
        raise RuntimeError("Google search configuration could not be loaded.") from e

try:
    google_info = load_google_search_config()
except Exception as e:
    logger.critical("Critical error loading Google search configuration. Exiting application.", exc_info=True)
    raise

try:
    google_search_instance = GoogleSearchAPIWrapper(
        google_api_key=google_info.google_api_key,
        google_cse_id=google_info.google_cse_id
    )
    logger.info("GoogleSearchAPIWrapper initialized successfully.")
except Exception as e:
    logger.exception("Failed to initialize GoogleSearchAPIWrapper.")
    raise RuntimeError("Google search instance initialization failed.") from e


def google_search(query: str, max_results: int = 5) -> WebSearchResults:
    """
    Executes a Google search using the pre-initialized GoogleSearchAPIWrapper.
    
    Args:
        query (str): The search query string.
        max_results (int, optional): Maximum number of search results to return. Defaults to 5.
    
    Returns:
        WebSearchResults: A validated Pydantic model containing the search results.
    
    Raises:
        RuntimeError: If the search operation fails.
    """
    logger.info(f"Starting Google search for query: '{query}' with max_results={max_results}")
    try:
        # Get search results from the API wrapper
        results = google_search_instance.results(query, num_results=max_results)
        
        validated_results = WebSearchResults(results=results)
        logger.info(f"Google search completed successfully for query: '{query}'.")
        logger.debug(f"Search Result: {validated_results}")
        return validated_results
    except Exception as e:
        logger.exception("Google search failed.")
        raise RuntimeError("Google search operation failed.") from e
