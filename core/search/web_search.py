from typing import Literal

from core.search.engines.duckduckgo.duckduckgo import duckduckgo_search
from core.search.engines.google.google import google_search
from models import WebSearchResults
from utils.logs.logging_utils import logger

SearchEngine = Literal['google', 'duckduckgo']


class WebSearch:
    """
    A simple and extendible search wrapper that supports multiple search engines.
    
    Currently supported search engines:
      - google: Uses the Google Search API.
      - duckduckgo: Uses the DuckDuckGo search engine.
    
    Additional search engines can be integrated by adding them to the `self.search_engines` dictionary.
    """
    def __init__(self):
        self.search_engines = {
            'google': google_search,
            'duckduckgo': duckduckgo_search
        }

    def search(
        self, 
        query: str, 
        engine: SearchEngine = 'duckduckgo', 
        max_results: int = 5, 
        **kwargs
    ) -> WebSearchResults:
        """
        Performs a search using the specified search engine.
        
        Args:
            query (str): The search query string.
            engine (SearchEngine): The search engine to use. Must be either 'google' or 'duckduckgo'.
                                   Defaults to 'duckduckgo'.
            max_results (int): The maximum number of search results to return. Defaults to 5.
            **kwargs: Additional keyword arguments to pass to the specific search engine function.
        
        Returns:
            WebSearchResults: A validated Pydantic model containing the search results.
        
        Raises:
            ValueError: If the specified search engine is not supported.
            RuntimeError: If the search operation fails.
        """
        logger.info(f"Starting search using engine '{engine}' for query: '{query}'")
        
        if engine not in self.search_engines:
            error_msg = f"Search engine '{engine}' is not supported."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            results = self.search_engines[engine](query, max_results, **kwargs)
        except Exception as e:
            logger.exception(f"Search using engine '{engine}' failed for query: '{query}'")
            raise RuntimeError(f"Search operation failed for engine '{engine}'.") from e
        
        logger.info(f"Search using engine '{engine}' completed with {len(results.results)} results.")
        return results
