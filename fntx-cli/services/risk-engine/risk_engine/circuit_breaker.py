"""
Circuit Breaker implementation for fault tolerance

Provides automatic failure detection and recovery with three states:
- CLOSED: Normal operation, requests pass through
- OPEN: Failures exceeded threshold, requests fail immediately  
- HALF_OPEN: Testing if service has recovered
"""
import asyncio
import time
from enum import Enum
from typing import Callable, Optional, Dict, Any, List, Type
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for fault tolerance
    
    Prevents cascade failures by failing fast when a service is down
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exceptions: List[Type[Exception]] = None,
        half_open_requests: int = 1
    ):
        """
        Initialize circuit breaker
        
        Args:
            name: Circuit breaker identifier
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
            expected_exceptions: Exceptions that trigger the breaker
            half_open_requests: Number of test requests in half-open state
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions or [Exception]
        self.half_open_requests = half_open_requests
        
        # State tracking
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._success_count = 0
        self._half_open_attempts = 0
        
        # Metrics
        self.total_requests = 0
        self.total_failures = 0
        self.total_successes = 0
        self.state_changes = []
        
    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        return self._state
    
    def is_open(self) -> bool:
        """Check if circuit is open"""
        return self._state == CircuitState.OPEN
    
    def is_closed(self) -> bool:
        """Check if circuit is closed"""
        return self._state == CircuitState.CLOSED
    
    def is_half_open(self) -> bool:
        """Check if circuit is half open"""
        return self._state == CircuitState.HALF_OPEN
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self._last_failure_time is None:
            return False
        
        return time.time() - self._last_failure_time >= self.recovery_timeout
    
    def _change_state(self, new_state: CircuitState):
        """Change circuit state and log transition"""
        old_state = self._state
        self._state = new_state
        self.state_changes.append({
            "from": old_state.value,
            "to": new_state.value,
            "timestamp": datetime.now(),
            "failure_count": self._failure_count
        })
        
        logger.info(
            f"Circuit breaker '{self.name}' changed state: "
            f"{old_state.value} -> {new_state.value}"
        )
        
        # Reset counters based on new state
        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._half_open_attempts = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_attempts = 0
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: If circuit is open
        """
        self.total_requests += 1
        
        # Check if we should transition from OPEN to HALF_OPEN
        if self.is_open() and self._should_attempt_reset():
            self._change_state(CircuitState.HALF_OPEN)
        
        # Fail fast if circuit is open
        if self.is_open():
            raise CircuitBreakerError(
                f"Circuit breaker '{self.name}' is OPEN. "
                f"Service unavailable. Retry after {self.recovery_timeout}s"
            )
        
        # Execute the function
        try:
            # For async functions
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            self._on_success()
            return result
            
        except Exception as e:
            # Only count expected exceptions as failures
            if any(isinstance(e, exc) for exc in self.expected_exceptions):
                self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful call"""
        self.total_successes += 1
        self._success_count += 1
        
        if self.is_half_open():
            self._half_open_attempts += 1
            
            # If we've had enough successful requests, close the circuit
            if self._half_open_attempts >= self.half_open_requests:
                self._change_state(CircuitState.CLOSED)
                logger.info(
                    f"Circuit breaker '{self.name}' recovered. "
                    f"Closing circuit after {self._half_open_attempts} successful requests"
                )
    
    def _on_failure(self):
        """Handle failed call"""
        self.total_failures += 1
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        # If half open, immediately open the circuit
        if self.is_half_open():
            self._change_state(CircuitState.OPEN)
            logger.warning(
                f"Circuit breaker '{self.name}' failed during recovery. "
                f"Re-opening circuit"
            )
        
        # If closed, check if we've exceeded threshold
        elif self.is_closed() and self._failure_count >= self.failure_threshold:
            self._change_state(CircuitState.OPEN)
            logger.warning(
                f"Circuit breaker '{self.name}' opened after "
                f"{self._failure_count} failures"
            )
    
    def record_success(self):
        """Manually record a success (for non-decorated usage)"""
        self._on_success()
    
    def record_failure(self):
        """Manually record a failure (for non-decorated usage)"""
        self._on_failure()
    
    def reset(self):
        """Manually reset the circuit breaker"""
        self._change_state(CircuitState.CLOSED)
        self._failure_count = 0
        self._success_count = 0
        self._half_open_attempts = 0
        logger.info(f"Circuit breaker '{self.name}' manually reset")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        success_rate = (
            self.total_successes / self.total_requests 
            if self.total_requests > 0 else 0
        )
        
        return {
            "name": self.name,
            "state": self._state.value,
            "total_requests": self.total_requests,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "success_rate": success_rate,
            "failure_count": self._failure_count,
            "last_failure_time": self._last_failure_time,
            "state_changes": len(self.state_changes)
        }


def circuit_breaker(
    name: str = None,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exceptions: List[Type[Exception]] = None
):
    """
    Decorator for applying circuit breaker pattern to functions
    
    Usage:
        @circuit_breaker(name="external_api", failure_threshold=3)
        async def call_external_api():
            # Function implementation
    """
    def decorator(func: Callable) -> Callable:
        # Use function name if no name provided
        breaker_name = name or func.__name__
        breaker = CircuitBreaker(
            name=breaker_name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exceptions=expected_exceptions
        )
        
        async def async_wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we need to run in event loop
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(
                breaker.call(func, *args, **kwargs)
            )
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers"""
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
    
    def register(self, breaker: CircuitBreaker):
        """Register a circuit breaker"""
        self._breakers[breaker.name] = breaker
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name"""
        return self._breakers.get(name)
    
    def get_all(self) -> Dict[str, CircuitBreaker]:
        """Get all circuit breakers"""
        return self._breakers.copy()
    
    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get stats for all circuit breakers"""
        return {
            name: breaker.get_stats() 
            for name, breaker in self._breakers.items()
        }
    
    def reset_all(self):
        """Reset all circuit breakers"""
        for breaker in self._breakers.values():
            breaker.reset()


# Global registry instance
circuit_breaker_registry = CircuitBreakerRegistry()