import re
from difflib import SequenceMatcher
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class FuzzyRAGCache(BaseModel):
    """
    In-memory lookup with fuzzy matching for RAG cache entries.
    
    This class stores query-response pairs with frequency counts and supports:
      - Exact matching.
      - Substring matching after cleaning (lowercasing and removing special characters).
      - Fuzzy matching using SequenceMatcher with a configurable threshold.
    
    It also maintains a size limit and performs cleanup of least frequently used entries when the limit is exceeded.
    """
    limit: int = Field(default=50, description="Maximum number of query entries to store.")
    lookup: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Internal lookup dictionary.")

    def add(self, query: str, response: Any) -> None:
        """
        Add a query-response pair to the lookup.
        
        Each entry is stored as a dictionary with keys:
          - "response": the result corresponding to the query.
          - "frequency": the number of times this query (or a similar query) has been retrieved.
        
        If the lookup size is at or exceeds the defined limit, cleanup is performed before adding the new entry.
        
        Args:
            query (str): The query string.
            response (Any): The result corresponding to the query.
        """
        # If the query already exists, update its frequency and response.
        if query in self.lookup:
            self.lookup[query]["frequency"] += 1
            self.lookup[query]["response"] = response
            return

        # Before adding a new query, perform cleanup if we're at or over the limit.
        if len(self.lookup) >= self.limit:
            self._cleanup()

        self.lookup[query] = {"response": response, "frequency": 1}

    def get(self, query: str, threshold: float = 0.8) -> Optional[Any]:
        """
        Retrieve a response from the lookup using fuzzy matching.
        
        The method first attempts an exact match. If not found, it cleans the query (lowercase,
        remove special characters) and compares with stored queries using both substring and fuzzy matching.
        
        Args:
            query (str): The query string to search for.
            threshold (float, optional): The similarity threshold for fuzzy matching (default is 0.8).
        
        Returns:
            Optional[Any]: The cached response if a matching entry is found; otherwise, None.
        """
        # Exact match.
        if query in self.lookup:
            self.lookup[query]["frequency"] += 1
            return self.lookup[query]["response"]

        # Clean the query for matching.
        cleaned_query = re.sub(r'[^\w\s]', '', query.lower())

        # Substring matching.
        for cached_query, entry in self.lookup.items():
            cleaned_cached = re.sub(r'[^\w\s]', '', cached_query.lower())
            if cleaned_query in cleaned_cached or cleaned_cached in cleaned_query:
                entry["frequency"] += 1
                return entry["response"]

        # Fuzzy matching.
        for cached_query, entry in self.lookup.items():
            cleaned_cached = re.sub(r'[^\w\s]', '', cached_query.lower())
            similarity = SequenceMatcher(None, cleaned_query, cleaned_cached).ratio()
            if similarity >= threshold:
                entry["frequency"] += 1
                return entry["response"]

        return None

    def _cleanup(self) -> None:
        """
        Cleanup the lookup by removing the least frequently used entries.
        
        The strategy is to remove at least one entry or 10% of the current entries (whichever is greater),
        starting with the entries with the lowest frequency counts.
        """
        num_entries = len(self.lookup)
        num_to_remove = max(1, num_entries // 10)
        sorted_entries = sorted(self.lookup.items(), key=lambda item: item[1]["frequency"])
        queries_to_remove = [query for query, _ in sorted_entries[:num_to_remove]]

        for query in queries_to_remove:
            del self.lookup[query]
