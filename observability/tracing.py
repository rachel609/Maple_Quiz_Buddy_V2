"""
LangFuse Tracing - Observability for all LLM calls.

Purpose: Set up LangFuse callback handler for tracing LLM calls,
         RAG retrievals, and quiz sessions.
Inputs: LangFuse credentials from config.
Outputs: LangFuse callback handler (or None if not configured).
Dependencies: config, langfuse.
"""
import config

_handler = None


def get_langfuse_handler():
    """
    Get the LangFuse callback handler for LangChain.
    Returns None if LangFuse is not configured.
    """
    global _handler

    if not config.LANGFUSE_PUBLIC_KEY or not config.LANGFUSE_SECRET_KEY:
        return None

    if _handler is not None:
        return _handler

    try:
        from langfuse.callback import CallbackHandler

        _handler = CallbackHandler(
            public_key=config.LANGFUSE_PUBLIC_KEY,
            secret_key=config.LANGFUSE_SECRET_KEY,
            host=config.LANGFUSE_HOST,
        )
        return _handler
    except ImportError:
        print("[Warning] langfuse not installed. Run: pip install langfuse")
        return None
    except Exception as e:
        print(f"[Warning] LangFuse init failed: {e}")
        return None


def get_callbacks() -> list:
    """Get a list of active callback handlers for LangChain calls."""
    handler = get_langfuse_handler()
    return [handler] if handler else []


def trace_event(name: str, metadata: dict = None) -> None:
    """Log a custom trace event to LangFuse."""
    handler = get_langfuse_handler()
    if handler and hasattr(handler, "langfuse"):
        try:
            handler.langfuse.trace(name=name, metadata=metadata or {})
        except Exception:
            pass


if __name__ == "__main__":
    handler = get_langfuse_handler()
    if handler:
        print("LangFuse connected!")
    else:
        print("LangFuse not configured (no keys in .env)")
