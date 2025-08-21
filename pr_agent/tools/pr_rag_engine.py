import base64
import os

from pr_agent.algo.types import EDIT_TYPE
from pr_agent.clients.kaito_rag_client import KAITORagClient
from pr_agent.config_loader import get_settings
from pr_agent.git_providers import (get_git_provider,
                                    get_git_provider_with_context)
from pr_agent.tools.pr_rag_index_manager import PRRAGIndexManager
from pr_agent.algo.token_handler import TokenHandler

from ..log import get_logger

RAG_BUFFER_TOKENS = get_settings().config.get("KAITORAGENGINE.TOKEN_BUFFER", 2500)

class PRRAGEngine:
    '''
    PRRagEngine is responsible for querying the Retrieval-Augmented Generation (RAG) Engine.
    '''
    def __init__(self, index_manager: PRRAGIndexManager, pr_url: str):
        self.index_manager = index_manager
        self.pr_url = pr_url

    async def get_pr_head_index_name(self):
        """
        Get the index name for the pull request head.

        Returns:
            str: The index name for the pull request head.

        Raises:
            ValueError: If the git provider cannot be found.
        """
        git_provider = self.index_manager._get_git_provider(self.pr_url)
        if not git_provider:
            raise ValueError(f"Git provider not found for PR URL: {self.pr_url}")

        return self.index_manager._get_pr_head_index_name(git_provider)
    
    async def is_valid_pr_base_branch(self):
        git_provider = self.index_manager._get_git_provider(self.pr_url)
        if not git_provider:
            raise ValueError(f"Git provider not found for PR URL: {self.pr_url}")

        return self.index_manager._is_valid_base_branch(git_provider)

    async def get_pr_base_index_name(self):
        """
        Get the index name for the pull request base.

        Returns:
            str: The index name for the pull request base.

        Raises:
            ValueError: If the git provider cannot be found.
        """
        git_provider = self.index_manager._get_git_provider(self.pr_url)
        if not git_provider:
            raise ValueError(f"Git provider not found for PR URL: {self.pr_url}")

        return self.index_manager._get_pr_base_index_name(git_provider)

    async def query(self, query: str, llm_temperature: float = 0.7, llm_max_tokens: int = 1000, top_k: int = 5):
        """
        Query the RAG index for a given pull request URL.

        Args:
            pr_url (str): The URL of the pull request to query against.
            query (str): The query text to search for.
            llm_temperature (float, optional): Temperature parameter for LLM generation. Defaults to 0.7.
            llm_max_tokens (int, optional): Maximum tokens for LLM response. Defaults to 1000.
            top_k (int, optional): Number of top results to return. Defaults to 5.

        Returns:
            dict: The query response from the RAG client.

        Raises:
            ValueError: If the git provider cannot be found or the index doesn't exist.
            Exception: If an error occurs during the query process.
        """
        try:
            git_provider = self.index_manager._get_git_provider(self.pr_url)
            index_name = self.index_manager._get_pr_head_index_name(git_provider)

            # Check if the index exists
            if not self.index_manager._does_index_exist(index_name):
                raise ValueError(f"Index {index_name} does not exist. Please create the index first.")

            get_logger().info(f"Querying index {index_name} for PR URL {self.pr_url} with query: {query}")

            # Call the RAG client query method
            response = await self.index_manager.query(
                index_name=index_name,
                query=query,
                llm_temperature=llm_temperature,
                llm_max_tokens=llm_max_tokens,
                top_k=top_k
            )

            get_logger().info(f"Query completed successfully for index {index_name}")
            return response

        except Exception as e:
            get_logger().error(f"Error querying index: {e}")
            raise e
