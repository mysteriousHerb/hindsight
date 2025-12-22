"""
Client for communicating with the Hindsight daemon.

Handles daemon lifecycle (start if needed) and API requests via the Python client.
"""

import logging
import os
import subprocess
import time
from pathlib import Path

import httpx  # Used only for health check

logger = logging.getLogger(__name__)

DAEMON_PORT = 8889
DAEMON_URL = f"http://127.0.0.1:{DAEMON_PORT}"
DAEMON_STARTUP_TIMEOUT = 30  # seconds


def _find_hindsight_api_command() -> list[str]:
    """Find the command to run hindsight-api."""
    # Check if we're in development mode (local hindsight-api available)
    # Path: daemon_client.py -> hindsight_embed/ -> hindsight-embed/ -> memory-poc/
    dev_api_path = Path(__file__).parent.parent.parent / "hindsight-api"
    if dev_api_path.exists() and (dev_api_path / "pyproject.toml").exists():
        # Use uv run with the local project
        return ["uv", "run", "--project", str(dev_api_path), "hindsight-api"]

    # Fall back to uvx for installed version
    return ["uvx", "hindsight-api"]


def _is_daemon_running() -> bool:
    """Check if daemon is running and responsive."""
    try:
        with httpx.Client(timeout=2) as client:
            response = client.get(f"{DAEMON_URL}/health")
            return response.status_code == 200
    except Exception:
        return False


def _start_daemon(config: dict) -> bool:
    """
    Start the daemon in background.

    Returns True if daemon started successfully.
    """
    logger.info("Starting daemon...")

    # Build environment with LLM config
    env = os.environ.copy()
    if config.get("llm_api_key"):
        env["HINDSIGHT_API_LLM_API_KEY"] = config["llm_api_key"]
    if config.get("llm_provider"):
        env["HINDSIGHT_API_LLM_PROVIDER"] = config["llm_provider"]
    if config.get("llm_model"):
        env["HINDSIGHT_API_LLM_MODEL"] = config["llm_model"]

    # Use pg0 database specific to bank
    bank_id = config.get("bank_id", "default")
    env["HINDSIGHT_API_DATABASE_URL"] = f"pg0://hindsight-embed-{bank_id}"

    # Optimization flags for faster startup
    env["HINDSIGHT_API_SKIP_LLM_VERIFICATION"] = "true"
    env["HINDSIGHT_API_LOG_LEVEL"] = "warning"

    cmd = _find_hindsight_api_command() + ["--daemon"]

    try:
        # Start daemon in background
        # On Unix, we don't need to do anything special since --daemon does the fork
        subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        # Wait for daemon to be ready
        start_time = time.time()
        while time.time() - start_time < DAEMON_STARTUP_TIMEOUT:
            if _is_daemon_running():
                logger.info("Daemon started successfully")
                return True
            time.sleep(0.5)

        logger.error("Daemon failed to start within timeout")
        return False

    except FileNotFoundError:
        logger.error("hindsight-api command not found. Install with: pip install hindsight-api")
        return False
    except Exception as e:
        logger.error(f"Failed to start daemon: {e}")
        return False


def ensure_daemon_running(config: dict) -> bool:
    """
    Ensure daemon is running, starting it if needed.

    Returns True if daemon is running.
    """
    if _is_daemon_running():
        logger.debug("Daemon already running")
        return True

    return _start_daemon(config)


def stop_daemon() -> bool:
    """Stop the running daemon."""
    # Try to kill by PID from lockfile
    lockfile = Path.home() / ".hindsight" / "daemon.lock"
    if lockfile.exists():
        try:
            pid = int(lockfile.read_text().strip())
            os.kill(pid, 15)  # SIGTERM
            # Wait for process to exit
            for _ in range(50):
                time.sleep(0.1)
                try:
                    os.kill(pid, 0)
                except OSError:
                    return True
        except (ValueError, OSError):
            pass

    return not _is_daemon_running()


def get_client():
    """
    Get a Hindsight client connected to the daemon.

    Returns:
        Hindsight client instance
    """
    from hindsight_client import Hindsight

    return Hindsight(base_url=DAEMON_URL)


async def retain(bank_id: str, content: str, context: str = "general") -> dict:
    """
    Store a memory via the daemon API.

    Args:
        bank_id: Memory bank ID
        content: Memory content to store
        context: Category for the memory

    Returns:
        API response dict
    """
    client = get_client()
    try:
        response = await client.aretain(
            bank_id=bank_id,
            content=content,
            context=context,
        )
        return {"success": response.success if hasattr(response, 'success') else True}
    finally:
        await client.aclose()


async def recall(
    bank_id: str,
    query: str,
    budget: str = "low",
    max_tokens: int = 4096,
) -> dict:
    """
    Search memories via the daemon API.

    Args:
        bank_id: Memory bank ID
        query: Search query
        budget: Budget level (low, mid, high)
        max_tokens: Maximum tokens in results

    Returns:
        API response dict with results
    """
    client = get_client()
    try:
        results = await client.arecall(
            bank_id=bank_id,
            query=query,
            budget=budget,
            max_tokens=max_tokens,
        )
        # Convert results to dict format
        return {
            "results": [
                {
                    "text": r.text if hasattr(r, 'text') else str(r),
                    "type": r.type if hasattr(r, 'type') else None,
                    "occurred_start": r.occurred_start.isoformat() if hasattr(r, 'occurred_start') and r.occurred_start else None,
                    "occurred_end": r.occurred_end.isoformat() if hasattr(r, 'occurred_end') and r.occurred_end else None,
                    "entities": r.entities if hasattr(r, 'entities') else [],
                    "context": r.context if hasattr(r, 'context') else None,
                }
                for r in results
            ]
        }
    finally:
        await client.aclose()
