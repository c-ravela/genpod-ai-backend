import os
from functools import wraps

import phoenix as px
from openinference.instrumentation.langchain import LangChainInstrumentor
from phoenix.otel import register

from utils.yaml_utils import read_yaml

DEFAULT_CONFIG_PATH = os.path.join(os.getcwd(), "utils", "otel", "otel_config.yaml")


class TraceManager:
    """Singleton class to initialize and manage tracing."""

    _instance = None

    def __init__(self, project_name=None, endpoint=None, config_path=DEFAULT_CONFIG_PATH):
        if TraceManager._instance is not None:
            raise Exception("TraceManager already initialized!")

        config = read_yaml(config_path)
        tracing_config = config.get("tracing", {})

        project_name = project_name or tracing_config.get("project_name")
        endpoint = endpoint or tracing_config.get("tracing_endpoint")

        if project_name is None or endpoint is None:
            raise Exception("Tracing configuration missing required fields: 'project_name' and/or 'tracing_endpoint'")

        # Initialize the tracer provider and instrument required modules.
        self.tracer_provider = register(project_name=project_name, endpoint=endpoint)
        LangChainInstrumentor().instrument(tracer_provider=self.tracer_provider)
        self.tracer = self.tracer_provider.get_tracer(__name__)
        TraceManager._instance = self

    @staticmethod
    def get_instance():
        """
        Get the singleton instance of the TraceManager. Initializes it if it hasn't been created.
        
        Args:
            project_name (str): The project name used for tracing.
            endpoint (str): The tracing endpoint.
            
        Returns:
            TraceManager: The singleton instance.
        """
        if TraceManager._instance is None:
            TraceManager()
        return TraceManager._instance

    def get_tracer(self, name: str = __name__):
        """
        Return a tracer instance for the given module name.
        
        Args:
            name (str): The module name to be used for the tracer.
        
        Returns:
            A tracer instance.
        """
        return self.tracer_provider.get_tracer(name)

def start_trace_session():
    """
    Start the tracing session.
    
    This function reads the 'launch_options' from the tracing configuration file.
    The configuration should include:
    
        tracing:
          launch_options:
            use_temp_dir: <boolean>
    
    If not specified, 'use_temp_dir' defaults to False.
    
    Returns:
        The session object.
    """
    config = read_yaml(DEFAULT_CONFIG_PATH)
    tracing_config = config.get("tracing", {})
    launch_options = tracing_config.get("launch_options", {})
    use_temp_dir = launch_options.get("use_temp_dir", False)
    return px.launch_app(use_temp_dir=use_temp_dir)

def stop_trace_session():
    """
    Stop the tracing session.
    
    This function reads the 'delete_data' option from the tracing configuration file.
    The configuration should include:
    
        tracing:
          launch_options:
            delete_data: <boolean>
    
    If not specified, 'delete_data' defaults to False.
    
    Returns:
        The result of closing the session.
    """
    config = read_yaml(DEFAULT_CONFIG_PATH)
    tracing_config = config.get("tracing", {})
    launch_options = tracing_config.get("launch_options", {})
    delete_data = launch_options.get("delete_data", False)
    return px.close_app(delete_data=delete_data)

def chain_decorator(tracer):
    """
    Returns a decorator that wraps a function in a tracing span using the tracer's chain attribute if available.
    Otherwise, returns a no-op decorator.
    
    Args:
        tracer: A tracer object, which may have a 'chain' attribute.
    
    Returns:
        A decorator function.
    """
    if hasattr(tracer, 'chain'):
        return tracer.chain
    else:
        # No-op decorator: simply returns the wrapped function unchanged.
        def noop_decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return noop_decorator
