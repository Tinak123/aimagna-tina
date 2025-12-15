"""
Centralized Logging Utility for AIMagna ETL Agent.
Provides structured, color-coded logging with timestamps and log levels.
"""

import sys
import traceback
from datetime import datetime
from typing import Optional, Any
from enum import Enum


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Colors:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright colors
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    
    # Background colors
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"


# Color mapping for log levels
LEVEL_COLORS = {
    LogLevel.DEBUG: Colors.DIM + Colors.WHITE,
    LogLevel.INFO: Colors.BRIGHT_BLUE,
    LogLevel.SUCCESS: Colors.BRIGHT_GREEN,
    LogLevel.WARNING: Colors.BRIGHT_YELLOW,
    LogLevel.ERROR: Colors.BRIGHT_RED,
    LogLevel.CRITICAL: Colors.BOLD + Colors.BG_RED + Colors.WHITE,
}

# Emoji/Symbol mapping for log levels
LEVEL_SYMBOLS = {
    LogLevel.DEBUG: "🔍",
    LogLevel.INFO: "ℹ️ ",
    LogLevel.SUCCESS: "✅",
    LogLevel.WARNING: "⚠️ ",
    LogLevel.ERROR: "❌",
    LogLevel.CRITICAL: "🚨",
}


class AgentLogger:
    """
    Logger class for AIMagna agents with structured output.
    
    Usage:
        logger = AgentLogger("ProfilerAgent")
        logger.info("Starting profiling...")
        logger.success("Completed profiling", data={"tables": 5})
        logger.error("Failed to process", error=exception)
    """
    
    def __init__(self, agent_name: str, use_colors: bool = True, use_emojis: bool = True):
        """
        Initialize the agent logger.
        
        Args:
            agent_name: Name of the agent (e.g., "ProfilerAgent", "MapperAgent")
            use_colors: Whether to use ANSI colors in output
            use_emojis: Whether to use emojis in output
        """
        self.agent_name = agent_name
        self.use_colors = use_colors and sys.stdout.isatty()
        self.use_emojis = use_emojis
        self.run_id: Optional[str] = None
        self.step_count = 0
    
    def set_run_id(self, run_id: str):
        """Set the current run ID for context."""
        self.run_id = run_id
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    def _format_message(
        self, 
        level: LogLevel, 
        message: str, 
        data: Optional[dict] = None,
        step: Optional[str] = None
    ) -> str:
        """Format a log message with all metadata."""
        timestamp = self._get_timestamp()
        
        # Build the prefix
        prefix_parts = [f"[{timestamp}]"]
        
        if self.use_emojis:
            prefix_parts.append(LEVEL_SYMBOLS.get(level, ""))
        
        prefix_parts.append(f"[{level.value:8}]")
        prefix_parts.append(f"[{self.agent_name}]")
        
        if self.run_id:
            prefix_parts.append(f"[{self.run_id}]")
        
        if step:
            prefix_parts.append(f"[Step: {step}]")
        
        prefix = " ".join(prefix_parts)
        
        # Apply colors if enabled
        if self.use_colors:
            color = LEVEL_COLORS.get(level, "")
            prefix = f"{color}{prefix}{Colors.RESET}"
        
        # Build the full message
        full_message = f"{prefix} {message}"
        
        # Add data if provided
        if data:
            data_str = ", ".join(f"{k}={v}" for k, v in data.items())
            if self.use_colors:
                data_str = f"{Colors.DIM}({data_str}){Colors.RESET}"
            else:
                data_str = f"({data_str})"
            full_message += f" {data_str}"
        
        return full_message
    
    def _log(
        self, 
        level: LogLevel, 
        message: str, 
        data: Optional[dict] = None,
        step: Optional[str] = None,
        error: Optional[Exception] = None
    ):
        """Internal logging method."""
        formatted = self._format_message(level, message, data, step)
        print(formatted)
        
        # Print traceback for errors
        if error and level in (LogLevel.ERROR, LogLevel.CRITICAL):
            if self.use_colors:
                print(f"{Colors.DIM}{Colors.RED}")
            print(f"    Exception Type: {type(error).__name__}")
            print(f"    Exception Message: {str(error)}")
            print("    Traceback:")
            for line in traceback.format_tb(error.__traceback__):
                for subline in line.strip().split('\n'):
                    print(f"        {subline}")
            if self.use_colors:
                print(Colors.RESET)
    
    def debug(self, message: str, data: Optional[dict] = None, step: Optional[str] = None):
        """Log a debug message."""
        self._log(LogLevel.DEBUG, message, data, step)
    
    def info(self, message: str, data: Optional[dict] = None, step: Optional[str] = None):
        """Log an info message."""
        self._log(LogLevel.INFO, message, data, step)
    
    def success(self, message: str, data: Optional[dict] = None, step: Optional[str] = None):
        """Log a success message."""
        self._log(LogLevel.SUCCESS, message, data, step)
    
    def warning(self, message: str, data: Optional[dict] = None, step: Optional[str] = None):
        """Log a warning message."""
        self._log(LogLevel.WARNING, message, data, step)
    
    def error(self, message: str, error: Optional[Exception] = None, data: Optional[dict] = None, step: Optional[str] = None):
        """Log an error message with optional exception details."""
        self._log(LogLevel.ERROR, message, data, step, error)
    
    def critical(self, message: str, error: Optional[Exception] = None, data: Optional[dict] = None, step: Optional[str] = None):
        """Log a critical error message."""
        self._log(LogLevel.CRITICAL, message, data, step, error)
    
    def step_start(self, step_name: str, description: str = ""):
        """Log the start of a workflow step."""
        self.step_count += 1
        msg = f"▶ STEP {self.step_count} STARTED: {step_name}"
        if description:
            msg += f" - {description}"
        self.info(msg, step=step_name)
    
    def step_complete(self, step_name: str, duration_ms: Optional[int] = None, data: Optional[dict] = None):
        """Log the completion of a workflow step."""
        msg = f"◀ STEP COMPLETED: {step_name}"
        log_data = data or {}
        if duration_ms is not None:
            log_data["duration_ms"] = duration_ms
        self.success(msg, data=log_data if log_data else None, step=step_name)
    
    def step_failed(self, step_name: str, error: Exception, data: Optional[dict] = None):
        """Log the failure of a workflow step."""
        msg = f"✖ STEP FAILED: {step_name}"
        self.error(msg, error=error, data=data, step=step_name)
    
    def separator(self, char: str = "=", length: int = 80):
        """Print a separator line."""
        line = char * length
        if self.use_colors:
            print(f"{Colors.DIM}{line}{Colors.RESET}")
        else:
            print(line)
    
    def header(self, title: str):
        """Print a formatted header."""
        self.separator()
        centered = f" {title} ".center(80, "=")
        if self.use_colors:
            print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}{centered}{Colors.RESET}")
        else:
            print(centered)
        self.separator()
    
    def subheader(self, title: str):
        """Print a formatted subheader."""
        line = f"--- {title} ---"
        if self.use_colors:
            print(f"{Colors.CYAN}{line}{Colors.RESET}")
        else:
            print(line)


# Pre-configured loggers for each agent
def get_logger(agent_name: str) -> AgentLogger:
    """Get a logger instance for the specified agent."""
    return AgentLogger(agent_name)


# Convenience function for quick logging
def log_agent_activity(
    agent_name: str,
    action: str,
    status: str = "info",
    data: Optional[dict] = None,
    error: Optional[Exception] = None
):
    """
    Quick logging function for agent activities.
    
    Args:
        agent_name: Name of the agent
        action: Description of the action
        status: One of "info", "success", "warning", "error"
        data: Optional dictionary of additional data
        error: Optional exception for error logging
    """
    logger = AgentLogger(agent_name)
    
    if status == "success":
        logger.success(action, data=data)
    elif status == "warning":
        logger.warning(action, data=data)
    elif status == "error":
        logger.error(action, error=error, data=data)
    else:
        logger.info(action, data=data)

