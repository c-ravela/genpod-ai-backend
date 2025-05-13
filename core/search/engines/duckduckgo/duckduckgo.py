from pathlib import Path

from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from pydantic import BaseModel, Field

from models import WebSearchResults
from utils.logger import logger
from utils.yaml_utils import read_yaml

DEFAULT_CONFIG_PATH = Path("core/search/engines/duckduckgo/duckduckgo.yaml")


class DuckduckgoSearchConfig(BaseModel):
    """
    Configuration model for performing a DuckDuckGo search.

    Attributes:
        region (str): The regional code to be used for the search (default: 'wt-wt').
        time (str): A filter for the time period of the search results, e.g., 'y' for the past year (default: 'y').
    """
    region: str = Field(default="wt-wt", description="The regional code for the DuckDuckGo search (default: 'wt-wt').")
    time: str = Field(default="y", description="Time filter for search results, e.g., 'y' for past year (default: 'y').")

def load_duckduckgo_search_config(config_path: Path = DEFAULT_CONFIG_PATH) -> DuckduckgoSearchConfig:
    """
    Loads and returns the DuckDuckGo search configuration from a YAML file.

    Args:
        config_path (Path, optional): The path to the YAML configuration file.
                                      Defaults to DEFAULT_CONFIG_PATH.

    Returns:
        DuckduckgoSearchConfig: A validated configuration instance for DuckDuckGo search.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        RuntimeError: If an error occurs during loading or parsing the configuration.
    """
    logger.info("Loading DuckDuckGo search configuration from: %s", config_path.resolve())

    if not config_path.is_file():
        logger.error("Configuration file not found: %s", config_path.resolve())
        raise FileNotFoundError(f"Configuration file not found: {config_path.resolve()}")

    try:
        config_data = read_yaml(str(config_path))
        duckduckgo_config = DuckduckgoSearchConfig(**config_data)
        logger.info("Successfully loaded DuckDuckGo search configuration.")
        return duckduckgo_config
    except Exception as e:
        logger.exception("Failed to load or parse DuckDuckGo search configuration from: %s", config_path.resolve())
        raise RuntimeError("DuckDuckGo search configuration could not be loaded.") from e

try:
    duckduckgo_info = load_duckduckgo_search_config()
except Exception as e:
    logger.critical("Critical error loading Duckduckgo search configuration. Exiting application.", exc_info=True)
    raise

try:
    duckduckgo_search_instance = DuckDuckGoSearchAPIWrapper(
        region=duckduckgo_info.region,
        time=duckduckgo_info.time
    )
    logger.info("DuckDuckGoSearchAPIWrapper initialized successfully.")
except Exception as e:
    logger.exception("Failed to initialize DuckDuckGoSearchAPIWrapper.")
    raise RuntimeError("DuckDuckGo search instance initialization failed.") from e


def duckduckgo_search(query: str, max_results: int = 5) -> WebSearchResults:
    """
    Executes a DuckDuckGo search using the pre-initialized DuckDuckGoSearchAPIWrapper.
    
    Args:
        query (str): The search query string.
        max_results (int, optional): Maximum number of search results to return. Defaults to 5.
    
    Returns:
        WebSearchResults: A validated Pydantic model containing the search results.
    
    Raises:
        RuntimeError: If the search operation fails.
    """
    logger.info("Starting DuckDuckGo search for query: '%s' with max_results=%d", query, max_results)
    try:
        results = duckduckgo_search_instance.results(query, max_results=max_results)
        validated_results = WebSearchResults(results=results)
        logger.info("DuckDuckGo search completed successfully for query: '%s'.", query)
        logger.debug("Search Result: %s", validated_results)
        return validated_results
    except Exception as e:
        logger.exception("DuckDuckGo search failed for query: '%s'.", query)
        raise RuntimeError("DuckDuckGo search operation failed.") from e
