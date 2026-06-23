from __future__ import annotations


def langgraph_available() -> bool:
    try:
        import langgraph  # noqa: F401
    except ImportError:
        return False
    return True


def require_langgraph() -> None:
    if not langgraph_available():
        raise RuntimeError(
            "LangGraph is not installed. Install the runtime extra with "
            "`python -m pip install -e .[runtime]`."
        )
