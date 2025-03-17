from utils.otel.otel_tracing import TraceManager, chain_decorator


def trace_span(fn=None, *, module_name: str = None):
    """
    Decorator that wraps a function in a tracing span using the centralized tracer.
    
    If no module_name is provided, the function's __module__ attribute is used by default.
    
    Usage:
        @trace_span
        def example_function():
            pass

        # Or with an explicit module name:
        @trace_span(module_name="custom.module")
        def example_function():
            pass
    """
    def decorator(func):
        local_module_name = module_name if module_name is not None else func.__module__
        tracing_manager = TraceManager.get_instance()
        tracer = tracing_manager.get_tracer(local_module_name)
        decorator_func = chain_decorator(tracer)
        return decorator_func(func)
    
    if fn is not None:
        return decorator(fn)
    else:
        return decorator
