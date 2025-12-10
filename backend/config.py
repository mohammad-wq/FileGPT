"""
FileGPT Configuration Module
Centralized configuration for logging, rate limiting, and Ollama health checks.
"""

import os
import sys
import io
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

def setup_logging(log_file: str = None) -> logging.Logger:
    """
    Configure structured logging for the application.
    
    Args:
        log_file: Path to log file (default: logs/filegpt.log)
        
    Returns:
        Configured logger instance
    """
    if log_file is None:
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "filegpt.log"
    
    # Create logger
    logger = logging.getLogger("filegpt")
    logger.setLevel(logging.DEBUG)
    
    # Console handler (INFO and above)
    # Use a UTF-8 wrapped stdout stream to avoid UnicodeEncodeError on Windows consoles
    try:
        console_stream = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        # Fallback if stdout has no buffer (very rare)
        console_stream = sys.stdout

    console_handler = logging.StreamHandler(stream=console_stream)
    # Reduce console verbosity to WARNING to avoid noisy startup logs
    console_handler.setLevel(logging.WARNING)
    console_format = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    
    # File handler (DEBUG and above, rotating) - ensure UTF-8 encoding
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    
    # Add handlers
    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger


# Get global logger instance
logger = setup_logging()


# ============================================================================
# RATE LIMITING CONFIGURATION
# ============================================================================

class RateLimitConfig:
    """Rate limiting settings for expensive operations."""
    
    # Expensive operations: limit to 1 request per second per IP
    EXPENSIVE_OPS_RPM = 60  # requests per minute
    
    # Moderate operations: limit to 30 per minute per IP
    MODERATE_OPS_RPM = 30
    
    # Endpoints configuration
    LIMITS = {
        "/ask_rag": "1/second",  # Document grading is expensive
        "/organize": "1/second",  # Batch operations
        "/categorize": "2/second",  # Moderate load
        "/ask": "5/second",  # Standard ask endpoint
        "/search": "10/second",  # Fast keyword search
    }


# ============================================================================
# OLLAMA CONFIGURATION
# ============================================================================

class OllamaConfig:
    """Ollama health check and recovery settings."""
    
    # Ollama connection settings
    HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
    
    # Health check intervals (seconds)
    HEALTH_CHECK_INTERVAL = 30  # Check every 30 seconds
    HEALTH_CHECK_TIMEOUT = 5  # 5 second timeout
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds between retries
    
    # Circuit breaker: disable Ollama after 5 consecutive failures
    CIRCUIT_BREAKER_THRESHOLD = 5
    CIRCUIT_BREAKER_RESET = 300  # Try again after 5 minutes


# ============================================================================
# SESSION STORAGE CONFIGURATION
# ============================================================================

class SessionConfig:
    """Session management settings."""
    
    # Session storage mode: 'memory' or 'sqlite'
    STORAGE_MODE = os.getenv("SESSION_STORAGE", "sqlite")
    
    # SQLite database path
    DB_PATH = os.path.join(
        os.path.dirname(__file__),
        "..",
        "session_store.db"
    )
    
    # Session settings
    MAX_MESSAGES_PER_SESSION = 10
    SESSION_TTL_SECONDS = 86400  # 24 hours
    CLEANUP_INTERVAL_SECONDS = 3600  # Clean up expired sessions every hour


# ============================================================================
# ASYNC CONFIGURATION
# ============================================================================

class AsyncConfig:
    """Async/concurrency settings."""
    
    # Thread pool for running blocking operations
    THREAD_POOL_SIZE = 5
    
    # Use thread executor for blocking Ollama calls
    USE_THREAD_EXECUTOR = True


# Logging convenience
def get_logger(name: str = None) -> logging.Logger:
    """Get a logger instance."""
    if name:
        return logging.getLogger(f"filegpt.{name}")
    return logger
