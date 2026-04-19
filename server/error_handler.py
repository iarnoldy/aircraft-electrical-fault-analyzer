"""
Comprehensive error handling system for Aircraft Electrical Fault Analyzer
Includes custom exceptions, error logging, and recovery mechanisms
"""

import logging
import traceback
import json
from typing import Dict, Any, Optional
from datetime import datetime
from functools import wraps
from flask import jsonify
import os


# Configure error logging
error_logger = logging.getLogger('error_handler')
error_logger.setLevel(logging.ERROR)

# Create error log file handler
error_log_path = os.path.join(
    os.path.dirname(__file__),
    '..',
    'data',
    'error_log.json'
)


class ErrorLogger:
    """
    Persistent error logger for academic documentation
    """

    def __init__(self, log_file: str = error_log_path):
        self.log_file = log_file
        self.errors = []
        self._load_errors()

    def _load_errors(self):
        """Load existing error log"""
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r') as f:
                    self.errors = json.load(f)
        except Exception as e:
            error_logger.warning(f"Could not load error log: {e}")
            self.errors = []

    def log_error(self, error: Exception, context: Dict = None):
        """
        Log an error with full context for academic documentation

        Args:
            error: The exception that occurred
            context: Additional context information
        """
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'context': context or {},
            'resolved': False
        }

        self.errors.append(error_entry)
        self._save_errors()

        # Also log to standard logger
        error_logger.error(
            f"Error logged: {error_entry['error_type']} - {error_entry['error_message']}",
            exc_info=True
        )

        return error_entry

    def _save_errors(self):
        """Save error log to file"""
        try:
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            with open(self.log_file, 'w') as f:
                json.dump(self.errors, f, indent=2)
        except Exception as e:
            error_logger.error(f"Could not save error log: {e}")

    def get_recent_errors(self, count: int = 10) -> list:
        """Get recent errors for analysis"""
        return self.errors[-count:] if self.errors else []


# Global error logger instance
error_log = ErrorLogger()


# Custom Exception Classes
class ApplicationError(Exception):
    """Base exception for application-specific errors"""

    def __init__(self, message: str, code: str = "APP_ERROR", details: Dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict:
        """Convert exception to dictionary for API response"""
        return {
            'error': True,
            'code': self.code,
            'message': self.message,
            'details': self.details
        }


class ValidationError(ApplicationError):
    """Input validation errors"""

    def __init__(self, message: str, field: str = None, value: Any = None):
        details = {}
        if field:
            details['field'] = field
        if value is not None:
            details['invalid_value'] = str(value)

        super().__init__(message, "VALIDATION_ERROR", details)


class ElectricalSystemError(ApplicationError):
    """Electrical system simulation errors"""

    def __init__(self, message: str, component: str = None, state: Dict = None):
        details = {}
        if component:
            details['component'] = component
        if state:
            details['system_state'] = state

        super().__init__(message, "ELECTRICAL_ERROR", details)


class APIError(ApplicationError):
    """External API errors"""

    def __init__(self, message: str, api_name: str, status_code: int = None):
        details = {
            'api_name': api_name
        }
        if status_code:
            details['status_code'] = status_code

        super().__init__(message, "API_ERROR", details)


class AgentError(ApplicationError):
    """Claude Agent SDK errors"""

    def __init__(self, message: str, prompt: str = None, response: str = None):
        details = {}
        if prompt:
            details['prompt_excerpt'] = prompt[:200]
        if response:
            details['response_excerpt'] = response[:200]

        super().__init__(message, "AGENT_ERROR", details)


class DataError(ApplicationError):
    """Data persistence and file system errors"""

    def __init__(self, message: str, file_path: str = None, operation: str = None):
        details = {}
        if file_path:
            details['file_path'] = file_path
        if operation:
            details['operation'] = operation

        super().__init__(message, "DATA_ERROR", details)


class TimeoutError(ApplicationError):
    """Operation timeout errors"""

    def __init__(self, message: str, operation: str, timeout: float):
        details = {
            'operation': operation,
            'timeout_seconds': timeout
        }
        super().__init__(message, "TIMEOUT_ERROR", details)


# Error Handling Decorators
def handle_errors(default_response: Any = None):
    """
    Decorator for handling errors in Flask routes

    Args:
        default_response: Default response to return on error
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ApplicationError as e:
                # Log application error
                error_log.log_error(e, {'function': func.__name__})

                # Return structured error response
                return jsonify({
                    'success': False,
                    'error': e.message,
                    'code': e.code,
                    'details': e.details
                }), 400

            except Exception as e:
                # Log unexpected error
                error_log.log_error(e, {'function': func.__name__})

                # Return generic error response
                return jsonify({
                    'success': False,
                    'error': 'An unexpected error occurred',
                    'code': 'INTERNAL_ERROR',
                    'details': {
                        'error_type': type(e).__name__
                    }
                }), 500

        return wrapper

    return decorator


def validate_input(schema: Dict):
    """
    Decorator for input validation

    Args:
        schema: Dictionary defining required fields and types
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get request data (assuming Flask request context)
            from flask import request
            data = request.get_json() if request.is_json else {}

            # Validate required fields
            for field, field_type in schema.items():
                if field not in data:
                    raise ValidationError(
                        f"Missing required field: {field}",
                        field=field
                    )

                # Type validation
                if field_type and not isinstance(data[field], field_type):
                    raise ValidationError(
                        f"Invalid type for field {field}. Expected {field_type.__name__}",
                        field=field,
                        value=data[field]
                    )

            return func(*args, **kwargs)

        return wrapper

    return decorator


def retry_on_failure(max_attempts: int = 3, delay: float = 1.0):
    """
    Decorator to retry operations on failure

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Delay between attempts in seconds
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time

            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        error_logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}"
                        )
                        time.sleep(delay * (attempt + 1))  # Exponential backoff
                    else:
                        error_logger.error(
                            f"All attempts failed for {func.__name__}: {e}"
                        )

            raise last_exception

        return wrapper

    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern for external service calls
    """

    def __init__(self, failure_threshold: int = 5,
                 recovery_timeout: float = 60,
                 expected_exception: type = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half-open

    def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection
        """
        if self.state == 'open':
            if self._should_attempt_reset():
                self.state = 'half-open'
            else:
                raise APIError(
                    "Service unavailable - circuit breaker open",
                    api_name=func.__name__
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        import time
        return (self.last_failure_time and
                time.time() - self.last_failure_time >= self.recovery_timeout)

    def _on_success(self):
        """Reset circuit breaker on success"""
        self.failure_count = 0
        self.state = 'closed'

    def _on_failure(self):
        """Handle failure and potentially open circuit"""
        import time
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = 'open'
            error_logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures"
            )


# Recovery Strategies
class RecoveryStrategies:
    """
    Collection of recovery strategies for various error scenarios
    """

    @staticmethod
    def recover_from_api_failure(api_name: str, error: Exception) -> Optional[Dict]:
        """
        Recover from external API failure

        Args:
            api_name: Name of the failed API
            error: The exception that occurred

        Returns:
            Fallback data if available, None otherwise
        """
        fallback_data = {
            'weather': {
                'temperature_celsius': 25,
                'humidity_percent': 65,
                'pressure_mb': 1013,
                'source': 'fallback',
                'warning': 'Using default weather data due to API failure'
            },
            'aircraft': {
                'model': 'Generic Aircraft',
                'electrical_system': '14V',
                'source': 'fallback',
                'warning': 'Using generic aircraft data due to API failure'
            }
        }

        if api_name in fallback_data:
            error_logger.info(f"Using fallback data for {api_name}")
            return fallback_data[api_name]

        return None

    @staticmethod
    def recover_from_data_corruption(file_path: str) -> bool:
        """
        Attempt to recover from corrupted data file

        Args:
            file_path: Path to corrupted file

        Returns:
            True if recovery successful, False otherwise
        """
        backup_path = f"{file_path}.backup"

        try:
            if os.path.exists(backup_path):
                # Restore from backup
                import shutil
                shutil.copy2(backup_path, file_path)
                error_logger.info(f"Recovered {file_path} from backup")
                return True
            else:
                # Create new empty file
                with open(file_path, 'w') as f:
                    json.dump({}, f)
                error_logger.info(f"Created new {file_path}")
                return True

        except Exception as e:
            error_logger.error(f"Could not recover {file_path}: {e}")
            return False


# Flask Error Handlers
def register_error_handlers(app):
    """
    Register global error handlers for Flask app

    Args:
        app: Flask application instance
    """

    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({
            'success': False,
            'error': 'Resource not found',
            'code': 'NOT_FOUND'
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        # Log the error
        error_log.log_error(error)

        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

    @app.errorhandler(ValidationError)
    def validation_error(error):
        return jsonify(error.to_dict()), 400

    @app.errorhandler(APIError)
    def api_error(error):
        return jsonify(error.to_dict()), 503

    @app.errorhandler(AgentError)
    def agent_error(error):
        return jsonify(error.to_dict()), 500

    @app.errorhandler(ApplicationError)
    def application_error(error):
        return jsonify(error.to_dict()), 400


# Monitoring and Metrics
class ErrorMetrics:
    """
    Track error metrics for monitoring
    """

    def __init__(self):
        self.error_counts = {}
        self.last_errors = {}

    def record_error(self, error_type: str):
        """Record an error occurrence"""
        if error_type not in self.error_counts:
            self.error_counts[error_type] = 0

        self.error_counts[error_type] += 1
        self.last_errors[error_type] = datetime.now()

    def get_metrics(self) -> Dict:
        """Get current error metrics"""
        return {
            'error_counts': self.error_counts,
            'last_errors': {
                k: v.isoformat() for k, v in self.last_errors.items()
            },
            'total_errors': sum(self.error_counts.values())
        }

    def reset_metrics(self):
        """Reset all metrics"""
        self.error_counts.clear()
        self.last_errors.clear()


# Global metrics instance
error_metrics = ErrorMetrics()