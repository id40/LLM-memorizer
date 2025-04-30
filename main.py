from mcp.server.fastmcp import FastMCP, Context
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from dotenv import load_dotenv
from mem0 import Memory
import asyncio
import json
import os
import datetime 

from LLM_DB import get_LLM_Memorizer_client

load_dotenv()

DEFAULT_USER_ID = "user"

@dataclass
class LLMContext:
    """Context for the LLM Memorizer MCP server."""
    LLM_client: Memory

@asynccontextmanager
async def LLM_lifespan(server: FastMCP) -> AsyncIterator[LLMContext]:
    """
    Manages the LLM client lifecycle.
    
    Args:
        server: The FastMCP server instance
        
    Yields:
        LLmContext: The context containing the LLM client
    """
    LLM_client = get_LLM_Memorizer_client
    
    try:
        yield LLMContext(LLM_client=LLM_client)
    finally:
        pass

mcp = FastMCP(
    "mcp-LLM-Memorizer",
    description="MCP server for long term memory storage and retrieval with Mem0",
    lifespan=LLM_lifespan,
    host=os.getenv("HOST", "0.0.0.0"),
    port=os.getenv("PORT", "8050")
)        

@mcp.tool()
async def save_memory(ctx: Context, text: str) -> str:
    """
    Save information to your long-term memory.
    
    Args:
        ctx: The context containing the LLM client
        text: The content to store in memory
    """
    try:
        x=datetime.datetime.now()

        memory_client = ctx.request_context.lifespan_context.LLM_client
        
        message = [{"role": "user", "content": text}]
        
        memory_client.add(x,message, user_id=DEFAULT_USER_ID)
        
        return "Successfully saved memory: " 
            
    except Exception as e:
        return "Error saving memory: " + str(e)

@mcp.tool()
async def search_memories_by_datetime(ctx: Context, target_date: str = None, target_time: str = None) -> str:
    """
    Search memories by date and time.
    
    Args:
        ctx: The context containing the LLM client
        target_date: Date filter in YYYY-MM-DD format
        target_time: Time filter in HH:MM:SS format
    """
    try:
        # Get the memory client from context
        memory_client = ctx.request_context.lifespan_context.LLM_client
        
        # Get all memories (using an empty query string to get everything)
        memories = memory_client.search("", user_id=DEFAULT_USER_ID)
        
        # Process the results based on the memory format
        if isinstance(memories, dict) and "results" in memories:
            memory = memories["results"]
        else:
            memory = memories
        
        # Filter memories by date/time
        results = []
        for mem in memories:
            # Check if memory has timestamp info
            if "timestamp" in mem:
                datetime = mem["timestamp"]
                
                # Check date and time filters
                matches = True
                if target_date and target_date not in datetime:
                    matches = False
                if target_time and target_time not in datetime:
                    matches = False
                    
                if matches:
                    results.append(memory)
        
        return str(results)
            
    except Exception as e:
        return "Error searching memories: " 

async def main():
    transport = os.getenv("TRANSPORT", "sse")
    if transport == 'sse':
        # Run the MCP server with sse transport
        await mcp.run_sse_async()
    else:
        # Run the MCP server with stdio transport
        await mcp.run_stdio_async()

if __name__ == "__main__":
    asyncio.run(main())
