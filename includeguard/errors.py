"""
Production-grade error handling for IncludeGuard.

All errors inherit from IncludeGuardError for easy catching.
"""


class IncludeGuardError(Exception):
    """Base exception for all IncludeGuard errors."""
    
    def __init__(self, message: str, error_code: str = "UNKNOWN", details: str = None):
        """
        Initialize IncludeGuard error.
        
        Args:
            message: User-friendly error message
            error_code: Machine-readable error code (e.g., "FILE_NOT_FOUND")
            details: Optional technical details for debugging
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details
    
    def __str__(self) -> str:
        """Return formatted error message."""
        msg = f"[{self.error_code}] {self.message}"
        if self.details:
            msg += f"\nDetails: {self.details}"
        return msg


class ProjectError(IncludeGuardError):
    """Error related to project analysis."""
    
    def __init__(self, message: str, details: str = None):
        super().__init__(message, "PROJECT_ERROR", details)


class ProjectNotFoundError(ProjectError):
    """Project path does not exist."""
    
    def __init__(self, path: str):
        super().__init__(
            f"Project path not found: {path}",
            f"Make sure the path exists and is accessible"
        )
        self.path = path


class NoSourceFilesError(ProjectError):
    """No C++ source files found in project."""
    
    def __init__(self, path: str, searched_extensions: list = None):
        searched = searched_extensions or ["*.cpp", "*.cc", "*.cxx", "*.h", "*.hpp"]
        super().__init__(
            f"No C++ source files found in {path}",
            f"Searched for: {', '.join(searched)}"
        )
        self.path = path


class FileError(IncludeGuardError):
    """Error reading or processing a file."""
    
    def __init__(self, message: str, filepath: str = None, details: str = None):
        super().__init__(message, "FILE_ERROR", details)
        self.filepath = filepath


class FileNotReadableError(FileError):
    """Cannot read file (permissions, encoding, etc)."""
    
    def __init__(self, filepath: str, reason: str = None):
        super().__init__(
            f"Cannot read file: {filepath}",
            filepath,
            f"Reason: {reason or 'Unknown (check permissions and file format)'}"
        )


class EncodingError(FileError):
    """File has encoding issues."""
    
    def __init__(self, filepath: str, encoding: str = "UTF-8"):
        super().__init__(
            f"Cannot decode file with {encoding}: {filepath}",
            filepath,
            "File may contain binary data or use different encoding"
        )


class ParseError(IncludeGuardError):
    """Error parsing C++ file."""
    
    def __init__(self, message: str, filepath: str = None, line_number: int = None, details: str = None):
        error_msg = message
        if filepath and line_number:
            error_msg = f"{filepath}:{line_number}: {message}"
        elif filepath:
            error_msg = f"{filepath}: {message}"
        
        super().__init__(error_msg, "PARSE_ERROR", details)
        self.filepath = filepath
        self.line_number = line_number


class ValidationError(IncludeGuardError):
    """Error validating analysis results."""
    
    def __init__(self, message: str, details: str = None):
        super().__init__(message, "VALIDATION_ERROR", details)


class CompilerError(ValidationError):
    """Error running compiler for validation."""
    
    def __init__(self, compiler: str, return_code: int, stderr: str = None):
        super().__init__(
            f"Compiler failed: {compiler} (exit code {return_code})",
            f"stderr: {stderr or 'No output'}"
        )
        self.compiler = compiler
        self.return_code = return_code


class ConfigError(IncludeGuardError):
    """Error in configuration."""
    
    def __init__(self, message: str, config_key: str = None, details: str = None):
        super().__init__(message, "CONFIG_ERROR", details)
        self.config_key = config_key


class InvalidThresholdError(ConfigError):
    """Invalid confidence threshold."""
    
    def __init__(self, value: float):
        super().__init__(
            f"Invalid threshold value: {value}",
            "min_confidence",
            f"Threshold must be between 0.0 and 1.0, got {value}"
        )


class InvalidReportFormatError(ConfigError):
    """Invalid report format specified."""
    
    def __init__(self, format_name: str, valid_formats: list = None):
        valid = valid_formats or ["text", "json", "html", "csv"]
        super().__init__(
            f"Invalid report format: {format_name}",
            "report_format",
            f"Valid formats: {', '.join(valid)}"
        )


class CLIError(IncludeGuardError):
    """Error in command-line interface."""
    
    def __init__(self, message: str, details: str = None):
        super().__init__(message, "CLI_ERROR", details)


class HelpRequestedError(CLIError):
    """User requested help (--help flag)."""
    
    def __init__(self, help_text: str):
        super().__init__("Help requested", "HELP_REQUESTED", help_text)
        self.help_text = help_text


class TimeoutError(IncludeGuardError):
    """Operation timed out."""
    
    def __init__(self, operation: str, timeout_seconds: int):
        super().__init__(
            f"Operation timed out: {operation}",
            "TIMEOUT",
            f"Timeout after {timeout_seconds} seconds"
        )
        self.operation = operation
        self.timeout_seconds = timeout_seconds


class AnalysisError(IncludeGuardError):
    """Error during analysis."""
    
    def __init__(self, message: str, details: str = None):
        super().__init__(message, "ANALYSIS_ERROR", details)


class InternalError(IncludeGuardError):
    """Unexpected internal error."""
    
    def __init__(self, message: str, exception: Exception = None):
        super().__init__(
            message,
            "INTERNAL_ERROR",
            f"Exception: {type(exception).__name__}: {str(exception)}" if exception else None
        )
        self.exception = exception


# Error handler utilities
class ErrorHandler:
    """Centralized error handling and reporting.
    
    Provides common validation and error handling patterns.
    """
    
    @staticmethod
    def handle_file_operation(func, filepath: str, operation: str = "read"):
        """
        Safely execute file operation with proper error handling.
        
        Args:
            func: Function to execute
            filepath: File being operated on
            operation: Operation name for error messages
            
        Returns:
            Result of func() or raises appropriate error
        """
        try:
            return func()
        except FileNotFoundError:
            raise ProjectNotFoundError(filepath)
        except PermissionError:
            raise FileNotReadableError(filepath, "Permission denied")
        except UnicodeDecodeError as e:
            raise EncodingError(filepath, "UTF-8")
        except Exception as e:
            raise FileError(
                f"Error during {operation}: {str(e)}",
                filepath,
                str(e)
            )
    
    @staticmethod
    def validate_threshold(threshold: float) -> float:
        """
        Validate confidence threshold.
        
        Args:
            threshold: Threshold value
            
        Returns:
            Validated threshold
            
        Raises:
            InvalidThresholdError: If threshold is invalid
        """
        if not isinstance(threshold, (int, float)):
            raise InvalidThresholdError(threshold)
        
        if not 0.0 <= threshold <= 1.0:
            raise InvalidThresholdError(threshold)
        
        return float(threshold)
    
    @staticmethod
    def validate_report_format(format_name: str, valid_formats: list = None) -> str:
        """
        Validate report format.
        
        Args:
            format_name: Format name
            valid_formats: List of valid format names
            
        Returns:
            Validated format name
            
        Raises:
            InvalidReportFormatError: If format is invalid
        """
        valid = valid_formats or ["text", "json", "html", "csv"]
        
        if format_name.lower() not in valid:
            raise InvalidReportFormatError(format_name, valid)
        
        return format_name.lower()
