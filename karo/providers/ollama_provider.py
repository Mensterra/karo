from typing import List, Optional
from pydantic import BaseModel, Field, SecretStr
import os
import logging
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OllamaProviderConfig(BaseModel):
    """Configuration for the Ollama provider."""
    type: str = Field("ollama", description="Discriminator field for provider type.")
    base_url: str = Field("http://localhost:11434", description="Base URL for the Ollama API.")
    model: str = Field("llama2", description="Name of the Ollama model to use.")

class OllamaEmbeddingFunction:
    """
    Embedding function for Ollama models.
    """
    def __init__(self, config: OllamaProviderConfig):
        self.config = config

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embeds a list of documents using the Ollama API.
        """
        embeddings = []
        for text in texts:
            try:
                response = httpx.post(
                    f"{self.config.base_url}/api/embeddings",
                    json={"model": self.config.model, "prompt": text},
                    timeout=60  # Adjust timeout as needed
                )
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
                result = response.json()
                embeddings.append(result["embedding"])
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error embedding document: {e}")
                raise
            except httpx.RequestError as e:
                logger.error(f"Request error embedding document: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error embedding document: {e}", exc_info=True)
                raise
        return embeddings

class OllamaProvider:
    """
    Karo provider implementation for Ollama models.
    """
    def __init__(self, config: OllamaProviderConfig):
        self.config = config
        self.embedding_function = OllamaEmbeddingFunction(config)

    def get_model_name(self) -> str:
        """
        Returns the name of the Ollama model.
        """
        return self.config.model

    def get_embedding_function(self):
        """
        Returns the Ollama embedding function.
        """
        return self.embedding_function