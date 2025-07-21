#!/usr/bin/env python3
"""
Welly MCP Server

A Model Context Protocol server that provides AI assistants with access to
welly's petrophysical analysis capabilities.

Compatible with:
- Any MCP-compatible client
- Cursor IDE  

Usage:
    python -m welly.mcp
    python welly/mcp/mcp_server.py
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    CallToolRequest,
    CallToolResult,
)

from .tools import WellyMCPTools
from .session import SessionManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WellyMCPServer:
    """MCP Server for welly petrophysical analysis."""
    
    def __init__(self):
        self.server = Server("welly-mcp")
        self.session_manager = SessionManager()
        self.tools = WellyMCPTools(self.session_manager)
        
        # Register MCP handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register MCP protocol handlers."""
        
        @self.server.list_tools()
        async def list_tools():
            """List available welly tools."""
            return [
                    Tool(
                        name="load_las_well",
                        description="Load a LAS (Log ASCII Standard) file from disk. Provide a file path, NOT file contents. The file must exist on the filesystem.",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "file_path": {
                                    "type": "string",
                                    "description": "Absolute or relative path to a LAS file on disk (e.g. /path/to/well.las). This is a file path, not file contents."
                                },
                                "alias_dict": {
                                    "type": "object", 
                                    "description": "Optional dictionary to map curve names (e.g., {'DEPT': 'DEPTH'})",
                                    "additionalProperties": {"type": "string"}
                                }
                            },
                            "required": ["file_path"]
                        }
                    ),
                    Tool(
                        name="get_curve_stats",
                        description="Calculate statistical summary for curves in a loaded well",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "well_id": {
                                    "type": "string",
                                    "description": "ID of the loaded well to analyze"
                                },
                                "curve_names": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "List of curve names to analyze (optional, analyzes all if not provided)"
                                }
                            },
                            "required": ["well_id"]
                        }
                    ),
                    Tool(
                        name="plot_well_log",
                        description="Generate a well log plot visualization",
                        inputSchema={
                            "type": "object", 
                            "properties": {
                                "well_id": {
                                    "type": "string",
                                    "description": "ID of the loaded well to plot"
                                },
                                "curves": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "List of curve names to include in plot"
                                },
                                "depth_range": {
                                    "type": "array",
                                    "items": {"type": "number"},
                                    "minItems": 2,
                                    "maxItems": 2,
                                    "description": "Depth range [start, end] to plot (optional)"
                                }
                            },
                            "required": ["well_id"]
                        }
                    ),
                    Tool(
                        name="get_well_info",
                        description="Get header information and metadata from a loaded well",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "well_id": {
                                    "type": "string", 
                                    "description": "ID of the loaded well"
                                }
                            },
                            "required": ["well_id"]
                        }
                    ),
                    Tool(
                        name="list_curves",
                        description="List all available curves in a loaded well",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "well_id": {
                                    "type": "string",
                                    "description": "ID of the loaded well"
                                }
                            },
                            "required": ["well_id"]
                        }
                    )
                ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]):
            """Handle tool calls."""
            try:
                # Use a consistent session ID to maintain state across tool calls
                # This ensures wells loaded in one call are available in subsequent calls
                session_id = "default_session"
                
                if name == "load_las_well":
                    result = await self.tools.load_las_well(arguments, session_id)
                elif name == "get_curve_stats":
                    result = await self.tools.get_curve_stats(arguments, session_id)
                elif name == "plot_well_log":
                    result = await self.tools.plot_well_log(arguments, session_id)
                elif name == "get_well_info":
                    result = await self.tools.get_well_info(arguments, session_id)
                elif name == "list_curves":
                    result = await self.tools.list_curves(arguments, session_id)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                # Handle different return types
                if isinstance(result, dict) and "plot_base64" in result:
                    # Return plot as image
                    return [
                        TextContent(
                            type="text",
                            text=f"Generated well log plot. {result.get('message', '')}"
                        ),
                        ImageContent(
                            type="image",
                            data=result["plot_base64"],
                            mimeType="image/png"
                        )
                    ]
                else:
                    # Format as JSON for readability
                    if isinstance(result, dict):
                        text = json.dumps(result, indent=2)
                    else:
                        text = str(result)
                    
                    return [
                        TextContent(
                            type="text", 
                            text=text
                        )
                    ]
                    
            except Exception as e:
                logger.error(f"Tool call failed: {e}")
                return [
                    TextContent(
                        type="text",
                        text=f"Error: {str(e)}"
                    )
                ]
    
    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )

async def main():
    """Main entry point for the MCP server."""
    server = WellyMCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())