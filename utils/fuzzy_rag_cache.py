import re
from difflib import SequenceMatcher


class FuzzyRAGCache:
    def __init__(self):
        self.cache = {}

    def add(self, query, result):
        self.cache[query] = result

    def get(self, query, threshold=0.8):
        # Exact match
        if query in self.cache:
            return self.cache[query]

        # Lowercase and remove special characters for comparison
        cleaned_query = re.sub(r'[^\w\s]', '', query.lower())

        # Partial substring match
        for cached_query, result in self.cache.items():
            cleaned_cached = re.sub(r'[^\w\s]', '', cached_query.lower())
            if cleaned_query in cleaned_cached or cleaned_cached in cleaned_query:
                return result

        # Fuzzy match using SequenceMatcher
        for cached_query, result in self.cache.items():
            similarity = SequenceMatcher(None, cleaned_query, re.sub(r'[^\w\s]', '', cached_query.lower())).ratio()
            if similarity >= threshold:
                return result

        return None