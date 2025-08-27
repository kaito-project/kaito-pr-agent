# Copyright (c) 2023 PR-Agent Authors
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy
import os
import uuid
from functools import partial

from pr_agent.algo.ai_handlers.base_ai_handler import BaseAiHandler
from pr_agent.algo.ai_handlers.litellm_ai_handler import LiteLLMAIHandler
from pr_agent.config_loader import get_settings
from pr_agent.git_providers import get_git_provider
from pr_agent.git_providers.git_provider import get_main_pr_language
from pr_agent.log import get_logger


class PRRagEdit:
    def __init__(self, issue_url: str, args=None, ai_handler: partial[BaseAiHandler,] = LiteLLMAIHandler):
        self.issue_url = issue_url
        self.git_provider = get_git_provider()(issue_url)
        
        # Parse arguments
        self.file_path, self.rag_prompt = self.parse_args(args)
        
        # Get repository language
        self.main_language = get_main_pr_language(
            self.git_provider.get_languages(), 
            self.git_provider.get_files(),
            is_issue_context=hasattr(self.git_provider, 'issue_main') and self.git_provider.issue_main is not None
        )
        
        # Initialize AI handler
        self.ai_handler = ai_handler()
        self.ai_handler.main_pr_language = self.main_language
        
    def normalize_file_path(self, file_path: str) -> str:
        """
        Normalize a file path to be relative to the repository root.
        - If the path starts with '/', remove it
        - If the path is empty, return empty
        """
        if not file_path:
            return ""
        # Remove leading slash if present
        if file_path.startswith('/'):
            file_path = file_path[1:]
        return file_path
        
    def parse_args(self, args):
        """
        Parse the command arguments.
        First argument is the file path, everything else is the RAG prompt.
        """
        file_path = ""
        rag_prompt = ""
        
        if args and len(args) > 0:
            file_path = self.normalize_file_path(args[0])
            if len(args) > 1:
                rag_prompt = " ".join(args[1:])
        
        return file_path, rag_prompt
        
    async def run(self):
        try:
            # Check if file path is provided
            if not self.file_path:
                if get_settings().config.publish_output:
                    self.git_provider.publish_comment("Error: File path not provided. Usage: /rag_edit <file_path> <RAG prompt>")
                return
                
            # Check if RAG prompt is provided
            if not self.rag_prompt:
                if get_settings().config.publish_output:
                    self.git_provider.publish_comment("Error: RAG prompt not provided. Usage: /rag_edit <file_path> <RAG prompt>")
                return
            
            # Log start of operation
            get_logger().info(f"Starting RAG edit for file {self.file_path}")
            
            if get_settings().config.publish_output:
                self.git_provider.publish_comment(
                    f"Processing RAG edit for file `{self.file_path}` with prompt: {self.rag_prompt}",
                    is_temporary=True
                )
            
            # Create a new branch name based on the issue
            branch_name = self._generate_branch_name()
            base_branch = self._get_default_branch()
            
            # Get the file content
            try:
                file_content = self.git_provider.get_pr_file_content(self.file_path, branch=base_branch)
                if not file_content:
                    raise FileNotFoundError(f"File {self.file_path} not found in the repository")
            except Exception as e:
                if get_settings().config.publish_output:
                    self.git_provider.publish_comment(f"Error: Could not read file {self.file_path}: {str(e)}")
                return
            
            # In the future, this would use RAG to modify the file content
            # For now, just use the original content
            edited_content = file_content
            
            # Create or update the file in the new branch
            try:
                commit_message = f"RAG edit to {self.file_path}\n\nRAG Prompt: {self.rag_prompt}"
                self._create_or_update_file(self.file_path, branch_name, base_branch, edited_content, commit_message)
                
                # Create PR
                pr_title = f"RAG edit to {self.file_path}"
                pr_body = f"This PR was automatically created by the RAG edit command.\n\nRAG prompt: {self.rag_prompt}\n\nRequested in issue: {self.issue_url}"
                pr_url = self._create_pull_request(branch_name, base_branch, pr_title, pr_body)
                
                # Post success comment
                if get_settings().config.publish_output:
                    self.git_provider.remove_initial_comment()
                    self.git_provider.publish_comment(
                        f"✅ Successfully created RAG edit PR: {pr_url}"
                    )
                    
            except Exception as e:
                if get_settings().config.publish_output:
                    self.git_provider.remove_initial_comment()
                    self.git_provider.publish_comment(f"Error creating RAG edit PR: {str(e)}")
                raise e
                
        except Exception as e:
            get_logger().error(f"Failed to perform RAG edit: {e}")
            if get_settings().config.publish_output:
                self.git_provider.remove_initial_comment()
                self.git_provider.publish_comment(f"❌ Failed to perform RAG edit: {str(e)}")
    
    def _generate_branch_name(self) -> str:
        """Generate a unique branch name for the RAG edit"""
        # Use a UUID to make the branch name unique
        unique_id = str(uuid.uuid4())[:8]
        sanitized_file = os.path.basename(self.file_path).replace('.', '-')
        return f"rag-edit-{sanitized_file}-{unique_id}"
    
    def _get_default_branch(self) -> str:
        """Get the default branch of the repository"""
        # This assumes the git provider has access to repository metadata
        try:
            return self.git_provider.repo_obj.default_branch
        except AttributeError:
            # Fallback to 'main' if we can't get the default branch
            return "main"
    
    def _create_or_update_file(self, file_path: str, branch_name: str, base_branch: str, 
                              content: str, commit_message: str) -> None:
        """Create or update a file in a specific branch"""
        # First create the branch if it doesn't exist
        try:
            # We need to create the branch from the base branch
            base_branch_ref = self.git_provider.repo_obj.get_git_ref(f"heads/{base_branch}")
            base_sha = base_branch_ref.object.sha
            
            # Try to create the branch
            try:
                self.git_provider.repo_obj.create_git_ref(f"refs/heads/{branch_name}", base_sha)
            except Exception as e:
                # Branch might already exist, which is fine
                get_logger().warning(f"Could not create branch {branch_name}, it might already exist: {e}")
            
            # Now update the file in that branch
            self.git_provider.create_or_update_pr_file(
                file_path=file_path,
                branch=branch_name,
                contents=content,
                message=commit_message
            )
        except Exception as e:
            get_logger().error(f"Failed to create or update file: {e}")
            raise e
    
    def _create_pull_request(self, head_branch: str, base_branch: str, title: str, body: str) -> str:
        """Create a pull request"""
        try:
            pr = self.git_provider.repo_obj.create_pull(
                title=title,
                body=body,
                base=base_branch,
                head=head_branch
            )
            return pr.html_url
        except Exception as e:
            get_logger().error(f"Failed to create pull request: {e}")
            raise e