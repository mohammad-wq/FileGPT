"""
Ollama Health Monitor & Circuit Breaker
Monitors Ollama availability and handles graceful degradation.
"""

import os
import sys
import threading
import time
import requests
from typing import Dict, Optional
from enum import Enum

# Add parent directory to path for config import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import OllamaConfig, get_logger

logger = get_logger("ollama_monitor")


class OllamaStatus(Enum):
    """Ollama connection status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"  # Intermittent failures
    UNAVAILABLE = "unavailable"  # Circuit breaker open


class OllamaHealthMonitor:
    """
    Monitors Ollama health and manages circuit breaker.
    Prevents cascade failures when Ollama is down.
    """
    
    def __init__(self):
        self.status = OllamaStatus.HEALTHY
        self.consecutive_failures = 0
        self.last_check_time = time.time()
        self.lock = threading.Lock()
        self.circuit_open_at = None
    
    def check_health(self) -> bool:
        """
        Improved health check: Distinguish between connection errors, port in use, and true unavailability.
        Returns True if healthy, False otherwise.
        """
        try:
            response = requests.get(
                f"{OllamaConfig.HOST}/api/tags",
                timeout=OllamaConfig.HEALTH_CHECK_TIMEOUT
            )
            if response.status_code == 200:
                return True
            logger.warning(f"Ollama responded with status {response.status_code}")
            return False
        except requests.ConnectionError as e:
            if "[WinError 10048]" in str(e) or "Only one usage of each socket address" in str(e):
                logger.warning("Ollama port is already in use. Ollama may already be running or another process is using the port.")
                # Do not open circuit breaker for port in use, just log and retry
                return True
            logger.debug(f"Ollama connection error: {e}")
            return False
        except requests.Timeout as e:
            logger.warning(f"Ollama health check timed out: {e}")
            return False
        except Exception as e:
            logger.debug(f"Ollama health check failed: {e}")
            return False
    
    def record_failure(self):
        """Record a failed Ollama call."""
        with self.lock:
            self.consecutive_failures += 1
            
            if self.consecutive_failures >= OllamaConfig.CIRCUIT_BREAKER_THRESHOLD:
                self.status = OllamaStatus.UNAVAILABLE
                self.circuit_open_at = time.time()
                logger.warning(
                    f"🔴 Ollama Circuit Breaker OPEN: {self.consecutive_failures} consecutive failures. "
                    f"Disabling LLM features for {OllamaConfig.CIRCUIT_BREAKER_RESET}s"
                )
            elif self.consecutive_failures > 1:
                self.status = OllamaStatus.DEGRADED
                logger.warning(f"⚠️  Ollama degraded: {self.consecutive_failures} consecutive failures")
    
    def record_success(self):
        """Record a successful Ollama call."""
        with self.lock:
            old_status = self.status
            self.consecutive_failures = 0
            
            # Reset circuit breaker if it was open
            if self.status == OllamaStatus.UNAVAILABLE:
                self.status = OllamaStatus.HEALTHY
                self.circuit_open_at = None
                logger.info("✅ Ollama Circuit Breaker RESET - Service restored")
            elif self.status == OllamaStatus.DEGRADED:
                self.status = OllamaStatus.HEALTHY
                logger.info("✅ Ollama recovered - Status HEALTHY")
    
    def is_circuit_open(self) -> bool:
        """Check if circuit breaker is open."""
        with self.lock:
            if self.status == OllamaStatus.UNAVAILABLE:
                # Check if enough time has passed to try again
                elapsed = time.time() - self.circuit_open_at
                if elapsed > OllamaConfig.CIRCUIT_BREAKER_RESET:
                    logger.info("🔄 Attempting to reset circuit breaker...")
                    return False  # Try again
                return True
            return False
    
    def get_status(self) -> Dict[str, any]:
        """Get current health status."""
        with self.lock:
            return {
                "status": self.status.value,
                "consecutive_failures": self.consecutive_failures,
                "circuit_open": self.status == OllamaStatus.UNAVAILABLE,
                "last_check": self.last_check_time
            }


# Global monitor instance
_monitor = OllamaHealthMonitor()


def get_monitor() -> OllamaHealthMonitor:
    """Get the global Ollama health monitor."""
    return _monitor


def is_ollama_available() -> bool:
    """
    Check if Ollama is available for use.
    
    Returns:
        False if circuit breaker is open, True otherwise
    """
    return not _monitor.is_circuit_open()


def record_ollama_success():
    """Call after successful Ollama operation."""
    _monitor.record_success()


def record_ollama_failure():
    """Call after failed Ollama operation."""
    _monitor.record_failure()


class BackgroundHealthChecker:
    """Periodically checks Ollama health in background."""
    
    def __init__(self):
        self.running = False
        self.thread = None
    
    def start(self):
        """Start background health checking."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._check_loop, daemon=True)
        self.thread.start()
        logger.info("✓ Ollama health checker started")
    
    def stop(self):
        """Stop background health checking."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("✓ Ollama health checker stopped")
    
    def _check_loop(self):
        """Background checking loop."""
        while self.running:
            try:
                if _monitor.check_health():
                    _monitor.record_success()
                else:
                    _monitor.record_failure()
            except Exception as e:
                logger.debug(f"Health check error: {e}")
                _monitor.record_failure()
            
            time.sleep(OllamaConfig.HEALTH_CHECK_INTERVAL)


# Global background checker
_checker = BackgroundHealthChecker()


def start_health_checker():
    """Start the background health monitor."""
    _checker.start()


def stop_health_checker():
    """Stop the background health monitor."""
    _checker.stop()
