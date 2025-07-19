"""
Logging configuration for M&A Research Assistant
"""

import logging
import logging.config
import sys
from typing import Dict, Any


def setup_logging(log_level: str = "INFO") -> None:
    """Setup application logging configuration"""
    
    # Check if running as MCP server (STDIO mode)
    import os
    is_mcp_mode = os.getenv("MCP_MODE", "false").lower() == "true" or not sys.stdout.isatty()
    
    config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": "ma_research.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            }
        },
        "loggers": {
            "ma_research_mcp": {
                "level": "DEBUG",
                "handlers": ["file"],
                "propagate": False
            },
            "botocore": {
                "level": "WARNING",
                "handlers": ["file"],
                "propagate": False
            },
            "urllib3": {
                "level": "WARNING",
                "handlers": ["file"],
                "propagate": False
            }
        },
        "root": {
            "level": log_level,
            "handlers": ["file"]
        }
    }
    
    logging.config.dictConfig(config)
    
    # Set up structured logging for audit trail
    audit_logger = logging.getLogger("ma_research_mcp.audit")
    audit_handler = logging.FileHandler("audit.log")
    audit_handler.setFormatter(
        logging.Formatter("%(asctime)s [AUDIT] %(message)s")
    )
    audit_logger.addHandler(audit_handler)
    audit_logger.setLevel(logging.INFO)