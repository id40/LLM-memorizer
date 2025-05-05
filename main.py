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
import traceback
import uuid


load_dotenv()

DEFAULT_USER_ID = 1

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
    
    print(f"Connecting to Supabase at URL: {supabase_url}")
    supabase = create_client(supabase_url, supabase_key)
    print("Supabase client created successfully")
    
    try:
        yield LLMContext(supabase=supabase)
    finally:
        print("Shutting down LLM Memorizer MCP server")

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
        current_time = datetime.datetime.now()
        supabase = ctx.request_context.lifespan_context.supabase
        
        message = [{"role": "user", "content": text}]
        
        # Use a UUID as a unique identifier instead of relying on user_id as primary key
        memory_data = {
            "user_id": DEFAULT_USER_ID,
            "content": text,
            "timestamp": current_time.isoformat(),
            "message": json.dumps(message),
            # If your table doesn't have an auto-incrementing id, add a unique id
            "id": str(uuid.uuid4()) if "id" in ctx.request_context.lifespan_context.supabase.table("memories").select("id").limit(1).execute().data else None
        }
        
        # Remove id if it's None (for auto-incrementing tables)
        if memory_data.get("id") is None:
            del memory_data["id"]
        
        # Debug info
        print(f"Attempting to save memory with data: {json.dumps(memory_data)}")
        
        # Execute insert with upsert option to avoid conflicts
        result = supabase.table("memories").upsert(memory_data).execute()
        
        print(f"Supabase result: {result}")
        return f"Successfully saved memory to Supabase at {current_time.isoformat()}"
            
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Detailed error in save_memory: {str(e)}")
        print(error_details)
        return f"Error saving memory: {str(e)}"

@mcp.tool()
async def search_memories(ctx: Context, date: str = None, time: str = None) -> str:
    """
    Search memories by date and/or time from Supabase.
    Returns results as a JSON string.

    Args:
        ctx: The context containing the Supabase client.
        date: Date filter in YYYY-MM-DD format.
        time: Time filter in HH:MM:SS format (matches start of time).
    """
    try:
        # Access Supabase client from the lifespan context
        supabase = ctx.request_context.lifespan_context.supabase
        print(f"Starting search with date={date}, time={time}")

        # Start with the base query - first testing without filters to ensure it works
        base_query = supabase.table("memories").select("*").eq("user_id", DEFAULT_USER_ID)
        print("Base query created")
        
        # First, try executing the base query to ensure it works
        try:
            print("Testing base query execution...")
            test_response = base_query.execute()
            print(f"Base query test successful, found {len(test_response.data)} records")
        except Exception as e:
            print(f"Base query test failed: {str(e)}")
            return json.dumps({"error": f"Database connection error: {str(e)}"}, indent=2)
        
        # If we get here, base query works, now build the actual query
        query = supabase.table("memories").select("*").eq("user_id", DEFAULT_USER_ID)

        # Apply date filter using a more compatible approach
        if date:
            try:
                # Validate date format
                datetime.datetime.strptime(date, '%Y-%m-%d')
                print(f"Date format valid: {date}")
                
                # Use a more standard PostgreSQL approach
                # Extract date portion and compare directly
                date_start = f"{date}T00:00:00"
                date_end = f"{date}T23:59:59"
                
                query = query.gte("timestamp", date_start).lte("timestamp", date_end)
                print(f"Applied date range filter: {date_start} to {date_end}")
            except ValueError as e:
                print(f"Date format error: {e}")
                return json.dumps({"error": "Invalid date format. Use YYYY-MM-DD."}, indent=2)

        # Apply time filter using a more compatible approach
        if time:
            try:
                # Validate time format
                datetime.datetime.strptime(time, '%H:%M:%S')
                print(f"Time format valid: {time}")
                
                # Extract hour and minute for comparison
                time_parts = time.split(':')
                hour = time_parts[0]
                minute = time_parts[1] if len(time_parts) > 1 else "00"
                
                # Create a date-agnostic time filter using string operations
                # This is a more reliable approach than timestamp::text
                time_filter = f"{hour}:{minute}"
                
                # For time, we'll fall back to a more manual filtering approach
                # First get all records (already filtered by date if applicable)
                response = query.execute()
                filtered_data = []
                
                # Then manually filter by time
                for record in response.data:
                    timestamp = record.get('timestamp', '')
                    # Extract time portion from the timestamp
                    if 'T' in timestamp:
                        record_time = timestamp.split('T')[1][:5]  # Get HH:MM
                        if record_time == time_filter:
                            filtered_data.append(record)
                
                # Return the manually filtered data
                print(f"Applied manual time filter, found {len(filtered_data)} matching records")
                return json.dumps(filtered_data, indent=2)
                
            except ValueError as e:
                print(f"Time format error: {e}")
                return json.dumps({"error": "Invalid time format. Use HH:MM:SS."}, indent=2)

        print("Executing final query...")
        # Execute the query, order results chronologically
        response = query.order("timestamp", desc=True).execute()
        
        # Format and return results
        if hasattr(response, 'data'):
            print(f"Found {len(response.data)} memories matching criteria.")
            return json.dumps(response.data, indent=2)
        else:
            print("No data attribute in response")
            return json.dumps([], indent=2)

    except Exception as e:
        # Log the detailed error server-side for debugging
        error_trace = traceback.format_exc()
        print(f"ERROR in search_memories: {type(e).__name__} - {str(e)}")
        print(error_trace)
        # Return a JSON error message to the client
        return json.dumps({"error": f"Server error searching memories: {str(e)}"}, indent=2)

async def main():
    transport = os.getenv("TRANSPORT", "sse")
    if transport == 'sse':
        await mcp.run_sse_async()
    else:
        await mcp.run_stdio_async()

if __name__ == "__main__":
    asyncio.run(main())