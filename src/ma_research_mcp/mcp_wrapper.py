#!/usr/bin/env python3
"""
MCP Wrapper to suppress non-JSON output for Claude Desktop compatibility
"""

import sys
import os
import io
from contextlib import redirect_stdout, redirect_stderr

# Redirect all output except what fastmcp sends to stdout for MCP communication
class NullWriter:
    def write(self, txt):
        pass
    def flush(self):
        pass
    def isatty(self):
        return False

def main():
    """Main wrapper that suppresses non-JSON output"""
    try:
        # Set environment for MCP mode
        os.environ['MCP_MODE'] = 'true'
        
        # Suppress all warnings and info messages
        import warnings
        warnings.filterwarnings('ignore')
        
        # Monkey patch rich console to disable banner
        try:
            from rich.console import Console
            original_print = Console.print
            def silent_print(self, *args, **kwargs):
                # Only allow JSON output, suppress decorative output
                pass
            Console.print = silent_print
        except ImportError:
            pass
        
        # Suppress stderr
        sys.stderr = NullWriter()
        
        # Import and run the main server
        from ma_research_mcp.main import main as server_main
        server_main()
    except Exception as e:
        # Log error to file since stderr is suppressed
        import logging
        logging.basicConfig(filename='mcp_wrapper_error.log', level=logging.ERROR)
        logging.error(f"Wrapper failed: {e}")
        import traceback
        logging.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    main()