from mem0 import Memory
import os


CUSTOM_INSTRUCTIONS = """
Extract the Following Information:  
- Key Information: Identify and save the most important details.
- Context: Capture the surrounding context to understand the memory's relevance.
- Connections: Note any relationships to other topics or memories.
- Importance: Highlight why this information might be valuable in the future.
- Source: Record where this information came from when applicable.
"""

def get_LLM_Memorizer_client():

    llm_provider = os.getenv('LLM_PROVIDER')
    llm_api_key = os.getenv('LLM_API_KEY')
    llm_model = os.getenv('LLM_CHOICE')
    embedding_model = os.getenv('EMBEDDING_MODEL_CHOICE')
    

    config = {}
    
    
    if llm_provider == 'openai':
        config["llm"] = {
            "provider": "openai",
            "config": {
                "model": llm_model,
                "temperature": 0.2,
                "max_tokens": 2000,
            }
        }
        if llm_api_key and not os.environ.get("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = llm_api_key
            
    elif llm_provider == 'openrouter':
        config["llm"] = {
            "provider": "openrouter",
            "config": {
                "model": llm_model,
                "temperature": 0.2,
                "max_tokens": 2000,
            }
        }
        if llm_api_key:
            os.environ["OPENROUTER_API_KEY"] = llm_api_key
    
    elif llm_provider == 'anthropic':
        config["llm"] = {
            "provider": "anthropic",
            "config": {
                "model": llm_model or "claude-3-haiku-20240307",
                "temperature": 0.2,
                "max_tokens": 2000,
            }
        }
        if llm_api_key:
            os.environ["ANTHROPIC_API_KEY"] = llm_api_key
    
    elif llm_provider == 'google':
        config["llm"] = {
            "provider": "google",
            "config": {
                "model": llm_model or "gemini-pro",
                "temperature": 0.2,
                "max_tokens": 2000,
            }
        }
        if llm_api_key:
            os.environ["GOOGLE_API_KEY"] = llm_api_key
    
    # Configure embedder based on provider
    if embedding_model == 'openai':
        config["embedder"] = {
            "provider": "openai",
            "config": {
                "model": "text-embedding-3-small",
                "embedding_dims": 1536
            }
        }
        if llm_api_key and not os.environ.get("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = llm_api_key
    
    elif embedding_model == 'cohere':
        config["embedder"] = {
            "provider": "cohere",
            "config": {
                "model": "embed-english-v3.0",
                "embedding_dims": 1024
            }
        }
        if os.getenv('COHERE_API_KEY'):
            os.environ["COHERE_API_KEY"] = os.getenv('COHERE_API_KEY')
    
    # Configure Supabase vector store
    config["vector_store"] = {
        "provider": "supabase",
        "config": {
            "connection_string": os.environ.get('DATABASE_URL', ''),
            "collection_name": "LLM_memories",
            "embedding_model_dims": config["embedder"]["config"]["embedding_dims"]
        }
    }
    # config["custom_fact_extraction_prompt"] = CUSTOM_INSTRUCTIONS
    
    # Create and return the Memory client
    return Memory.from_config(config)