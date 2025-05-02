from mcp.server.fastmcp import FastMCP, Context
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from dotenv import load_dotenv
from supabase import create_client, Client
import asyncio
import json
import os
import datetime 


load_dotenv()

DEFAULT_USER_ID = "user"

@dataclass
class LLMContext:
    """Context for the LLM Memorizer MCP server."""
    supabase: Client

@asynccontextmanager
async def LLM_lifespan(server: FastMCP) -> AsyncIterator[LLMContext]:
    """
    Manages the LLM client lifecycle.
    
    Args:
        server: The FastMCP server instance
        
    Yields:
        LLmContext: The context containing the LLM client and Supabase client
    """

    
    # Initialize Supabase client
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")
    
    supabase = create_client(supabase_url, supabase_key)
    
    try:
        yield LLMContext( supabase=supabase)
    finally:
        pass

mcp = FastMCP(
    "mcp-LLM-Memorizer",
    description="MCP server for long term memory storage and retrieval with Supabase",
    lifespan=LLM_lifespan,
    host=os.getenv("HOST", "0.0.0.0"),
    port=os.getenv("PORT", "8050")

)        

@mcp.tool()
async def save_memory(ctx: Context, text: str) -> str:
    """
    Save information to your long-term memory using Supabase.
    
    Args:
        ctx: The context containing the Supabase client
        text: The content to store in memory
    """
    try:
        x = datetime.datetime.now()
        supabase = ctx.request_context.lifespan_context.supabase
        
        message = [{"role": "user", "content": text}]
        
        # Save to Supabase only
        data = {
            "user_id": DEFAULT_USER_ID,
            "content": text,
            "timestamp": x.isoformat(),
            "message": json.dumps(message)
        }
        supabase.table("memories").insert(data).execute()
        
        return "Successfully saved memory to Supabase"
            
    except Exception as e:
        return f"Error saving memory: {str(e)}"

@mcp.tool()
async def search_memories(ctx: Context, date: str = None, time: str = None) -> str:
    """
    Search memories by date and time from Supabase.
    
    Args:
        ctx: The context containing the Supabase client
        date: Date filter in YYYY-MM-DD format
        time: Time filter in HH:MM:SS format
    """
    try:
        supabase = ctx.request_context.lifespan_context.supabase
        
        # Search in Supabase
        query = supabase.table("memories").select("*").eq("user_id", DEFAULT_USER_ID)
        
        if date:
            query = query.ilike("timestamp", f"%{date}%")
        if time:
            query = query.ilike("timestamp", f"%{time}%")
            
        supabase_results = query.execute()
        
        # Get results
        results = []
        
        # Add Supabase results
        if hasattr(supabase_results, 'data'):
            results.extend(supabase_results.data)
        
        return str(results)
            
    except Exception as e:
        return f"Error searching memories !"
        
        # Process Mem0 results
        for mem in memories:
            if "timestamp" in mem:
                datetime_str = mem["timestamp"]
                matches = True
                if date and date not in datetime_str:
                    matches = False
                if time and time not in datetime_str:
                    matches = False
                if matches:
                    results.append(mem)
        
        # Add Supabase results
        if hasattr(supabase_results, 'data'):
            results.extend(supabase_results.data)
        
        return str(results)
            
    except Exception as e:
        return f"Error searching memories: {str(e)}"

async def main():
    transport = os.getenv("TRANSPORT", "sse")
    if transport == 'sse':
        
        await mcp.run_sse_async()
    else:
        
        await mcp.run_stdio_async()

if __name__ == "__main__":
    asyncio.run(main())
