# Codebase Analysis Component

A modular, extensible codebase analysis system for GenPod that provides code context, querying, and bug impact analysis capabilities.

## Features

- **Modular Architecture**: Easy to swap between different analysis backends (LocAgent, LSP, etc.)
- **Context Management**: Build and maintain comprehensive codebase context
- **Query Interface**: Search and analyze code using various query types
- **Bug Impact Analysis**: Analyze dependencies and impact of bugs/changes
- **Git Integration**: Optional git hooks for automatic context updates
- **AI Enhancement**: Optional AI features for natural language queries and advanced analysis

## Quick Start

### Basic Usage

```python
from core.codebase_analysis import CodebaseAnalysisFactory

# Create analyzer (uses LocAgent by default)
analyzer = CodebaseAnalysisFactory.create(
    storage_base_path="/path/to/generated/app/.genpod"
)

# Build context
context = analyzer.build_context("/path/to/source/code")

# Get summary
summary = analyzer.get_summary()
print(summary.summary_text)

# Query codebase
from core.codebase_analysis.models.query_models import QueryRequest, QueryType

request = QueryRequest(
    query_type=QueryType.FIND_FUNCTION,
    query="user_login"
)
response = analyzer.query_codebase(request)

# Analyze bug impact
impact = analyzer.analyze_bug_impact(
    "AttributeError: 'User' object has no attribute 'email' in validate_user() at line 45"
)
```

### With Configuration

```python
# Using configuration file
analyzer = CodebaseAnalysisFactory.create(
    storage_base_path="/path/to/.genpod",
    config_path="analysis_config.yaml"
)

# Or with configuration dictionary
config = {
    "ai": {"enabled": True, "api_key": "your-key"},
    "analysis": {"max_file_size": 5000000}
}
analyzer = CodebaseAnalysisFactory.create(
    storage_base_path="/path/to/.genpod",
    config_dict=config
)
```

## Configuration

Create a YAML configuration file:

```yaml
# analysis_config.yaml
ai:
  enabled: true
  provider: openai
  api_key: sk-your-key-here  # Or use environment variable
  model: gpt-4o-mini

storage:
  cache_enabled: true

analysis:
  max_file_size: 10485760  # 10MB
  supported_extensions: [.py, .js, .ts, .java]
  exclude_directories: [.git, node_modules, __pycache__]

analyzer_type: locagent
```

## Architecture

### Directory Structure

```
core/codebase_analysis/
├── interfaces/           # Abstract base classes
│   ├── analyzer.py       # Main analyzer interface
│   ├── context_manager.py
│   ├── query_engine.py
│   ├── impact_analyzer.py
│   └── storage.py
├── locagent_impl/       # LocAgent implementation
│   ├── locagent_analyzer.py
│   └── locagent_storage.py
├── models/              # Data models
│   ├── context_models.py
│   ├── query_models.py
│   └── response_models.py
├── config/              # Configuration management
│   └── config_manager.py
├── factories/           # Factory for creating analyzers
│   └── analysis_factory.py
└── utils/               # Utilities
    ├── git_hooks.py
    └── error_handling.py
```

### Storage Structure

When you provide a `.genpod` path, the component creates:

```
.genpod/
└── code_analysis/
    ├── context/          # Dependency graphs, metadata
    ├── vectors/          # Vector embeddings (if AI enabled)
    ├── indexes/          # Text search indexes
    └── cache/            # Query cache, temporary data
```

## Query Types

The system supports various query types:

```python
from core.codebase_analysis.models.query_models import QueryType

# Simple lookups
QueryType.FIND_FUNCTION     # Find functions by name
QueryType.FIND_CLASS        # Find classes by name
QueryType.FIND_FILE         # Find files by name

# Analysis queries
QueryType.GET_DEPENDENCIES  # Get what a component depends on
QueryType.GET_DEPENDENTS    # Get what depends on a component
QueryType.GET_CALL_CHAIN    # Get call chains to a function

# Search queries
QueryType.SEARCH_CODE       # Search in code content
QueryType.NATURAL_LANGUAGE  # AI-powered natural language queries

# Statistics
QueryType.GET_STATS         # Get codebase statistics
QueryType.GET_SUMMARY       # Get codebase summary
```

## Bug Impact Analysis

Analyze the impact of bugs and changes:

```python
# From exception message
impact = analyzer.analyze_bug_impact(
    "TypeError: unsupported operand type(s) for +: 'str' and 'int' in calculate_total()"
)

# Results include
print(f"Primary impacts: {len(impact.primary_locations)}")
print(f"Secondary impacts: {len(impact.secondary_impacts)}")
print(f"Risk level: {impact.risk_assessment}")
print("Suggestions:", impact.suggested_fixes)

# Get affected files
files_to_review = impact.get_files_to_review()
```

## Git Hooks Integration

Enable automatic context updates:

```python
from core.codebase_analysis.utils.git_hooks import GitHooksManager

# Setup git hooks
hooks_manager = GitHooksManager("/path/to/repo", config)
hooks_manager.install_hooks(
    hooks_config={
        "on_commit": True,
        "on_pull": True,
        "on_merge": True
    },
    storage_base_path="/path/to/.genpod",
    config_path="analysis_config.yaml"
)
```

## Error Handling

The system includes robust error handling:

```python
from core.codebase_analysis.utils.error_handling import with_error_handling

@with_error_handling(fallback_return=None, log_errors=True)
def risky_operation():
    # Your code here
    pass

# Or use context manager for graceful failures
from core.codebase_analysis.utils.error_handling import GracefulFailure

with GracefulFailure("vector_storage") as vectors:
    # Try to use vector storage
    if vectors.is_available():
        # Use vectors
        pass
    else:
        # Fall back to alternative
        pass
```

## Extending the System

### Adding New Analyzer Implementations

1. Create a new implementation:

```python
from core.codebase_analysis.interfaces.analyzer import CodebaseAnalyzer

class MyCustomAnalyzer(CodebaseAnalyzer):
    def build_context(self, source_path: str, force_rebuild: bool = False):
        # Your implementation
        pass
    
    # Implement other abstract methods...
```

2. Register with factory:

```python
from core.codebase_analysis.factories.analysis_factory import CodebaseAnalysisFactory

CodebaseAnalysisFactory.register_analyzer('my_analyzer', MyCustomAnalyzer)
```

3. Use in configuration:

```yaml
analyzer_type: my_analyzer
```

### Adding New Query Types

1. Add to QueryType enum in `models/query_models.py`
2. Implement handler in your analyzer implementation
3. Update query validation logic

## API Keys and AI Features

### Environment Variables

Set environment variables for AI features:

```bash
export OPENAI_API_KEY="sk-your-key-here"
# Or for Azure
export AZURE_OPENAI_API_KEY="your-azure-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
```

### Features Available With/Without AI

**Without AI Keys (Always Available):**
- ✅ Context building and dependency analysis
- ✅ File and entity searching
- ✅ Bug impact analysis (static)
- ✅ Call chain analysis
- ✅ Statistics and summaries

**With AI Keys (Enhanced):**
- 🤖 Natural language queries
- 🤖 Intelligent bug analysis suggestions
- 🤖 Semantic code search
- 🤖 Enhanced impact analysis

## Performance and Caching

The system includes several optimization features:

- **Incremental Updates**: Only analyze changed files when possible
- **Caching**: Cache query results and analysis data
- **Parallel Processing**: Analyze multiple files concurrently
- **Storage Compression**: Compress graph and vector data
- **Lazy Loading**: Load components only when needed

## Integration with GenPod

### In GenPod Agents

```python
# In a GenPod agent
from core.codebase_analysis import CodebaseAnalysisFactory

class ReviewerAgent:
    def __init__(self, storage_path: str):
        self.analyzer = CodebaseAnalysisFactory.create(
            storage_base_path=storage_path
        )
    
    def analyze_bug(self, bug_report: str):
        # Build context if not exists
        if not self.analyzer.is_context_available():
            self.analyzer.build_context(self.get_source_path())
        
        # Analyze impact
        impact = self.analyzer.analyze_bug_impact(bug_report)
        
        return {
            "affected_files": impact.get_files_to_review(),
            "risk_level": impact.risk_assessment,
            "suggestions": impact.suggested_fixes
        }
```

### For Generated Applications

Each generated application gets its own analysis context:

```
generated_app/
├── .genpod/
│   └── code_analysis/    # Analysis data for this app
├── src/
├── tests/
└── ...
```

## Troubleshooting

### Common Issues

1. **LocAgent not available**: Falls back to simple analyzer
2. **Large codebase**: Adjust `max_files_to_process` and `max_file_size`
3. **Memory issues**: Disable file content caching or reduce `max_workers`
4. **API rate limits**: Adjust `max_requests_per_hour` in AI config

### Debug Mode

Enable debug logging:

```yaml
debug_mode: true
logging:
  level: DEBUG
```

### Storage Issues

Check storage statistics:

```python
storage_info = analyzer.get_storage_info()
print(storage_info)

# Clean up if needed
analyzer.cleanup_storage(confirm=True)
```

## Dependencies

- **Required**: Python 3.8+, pathlib, typing
- **LocAgent**: For full functionality (falls back to simple analyzer if not available)
- **AI Features**: OpenAI/Azure/Anthropic API keys
- **Git Hooks**: Git repository (optional)

## License

Part of the GenPod project.
