import base64
import os

from pr_agent.algo.types import EDIT_TYPE
from pr_agent.clients.kaito_rag_client import KAITORagClient
from pr_agent.git_providers import (get_git_provider,
                                    get_git_provider_with_context)

from ..log import get_logger


class PRRagEngine:
    '''
    PRRagEngine is responsible for managing Retrieval-Augmented Generation (RAG) indexes for pull requests (PRs) and their associated branches in a Git repository.
    It interacts with a RAG client to create, update, and manage document indexes based on the state of files in the repository and the changes introduced by PRs.
    '''
    def __init__(self, base_url: str):
        self.rag_client = KAITORagClient(base_url)
        # these are the languages that are supported by tree sitter
        self.valid_languages = ['bash', 'c', 'c_sharp','commonlisp', 'cpp', 'css', 'dockerfile', 'dot', 'elisp', 'elixir', 'elm', 'embedded_template', 'erlang', 'fixed_form_fortran', 'fortran', 'go', 'gomod', 'hack', 'haskell', 'hcl', 'html', 'java', 'javascript', 'jsdoc', 'json', 'julia', 'kotlin', 'lua', 'make', 'markdown', 'objc', 'ocaml', 'perl', 'php', 'python', 'ql', 'r', 'regex', 'rst', 'ruby', 'rust', 'scala', 'sql', 'sqlite', 'toml', 'tsq', 'typescript', 'yaml']
        self.file_extension_to_language_map = { ".sh": "bash", ".bash": "bash", ".c": "c", ".cs": "c_sharp", ".lisp": "commonlisp", ".lsp": "commonlisp", ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".h": "c", ".css": "css", ".dockerfile": "dockerfile", "Dockerfile": "dockerfile", ".dot": "dot", ".el": "elisp", ".ex": "elixir", ".exs": "elixir", ".elm": "elm", ".ejs": "embedded_template", ".erl": "erlang", ".hrl": "erlang", ".f": "fixed_form_fortran", ".for": "fixed_form_fortran", ".f90": "fortran", ".f95": "fortran", ".go": "go", ".mod": "gomod", "go.mod": "gomod", ".hack": "hack", ".hs": "haskell", ".hcl": "hcl", ".tf": "hcl", ".html": "html", ".htm": "html", ".java": "java", ".js": "javascript", ".jsx": "javascript", ".jsdoc": "jsdoc", ".json": "json", ".jl": "julia", ".kt": "kotlin", ".kts": "kotlin", ".lua": "lua", ".mk": "make", "Makefile": "make", ".md": "markdown", ".m": "objc", ".mm": "objc", ".ml": "ocaml", ".mli": "ocaml", ".pl": "perl", ".pm": "perl", ".php": "php", ".py": "python", ".ql": "ql", ".r": "r", ".regex": "regex", ".rst": "rst", ".rb": "ruby", ".rs": "rust", ".scala": "scala", ".sc": "scala", ".sql": "sql", ".sqlite": "sqlite", ".db": "sqlite", ".toml": "toml", ".tsq": "tsq", ".ts": "typescript", ".tsx": "typescript", ".yaml": "yaml", ".yml": "yaml"}

    def _get_git_provider(self, pr_url: str):
        git_provider = get_git_provider_with_context(pr_url)
        if not git_provider:
            get_logger().error(f"Git provider not found for PR URL {pr_url}.")
            raise ValueError("Git provider not found for the given PR URL.")
        return git_provider

    def _get_pr_head_index_name(self, git_provider):
        if not git_provider:
            raise ValueError("Git provider not found for the given PR URL.")

        # Build index_name from repo and branch
        repo_name = git_provider.repo.replace('/', '_')
        branch_name = git_provider.get_pr_branch().replace('/', '_')
        index_name = f"{repo_name}_{branch_name}"
        return index_name

    def _get_pr_base_index_name(self, git_provider):
        if not git_provider:
            raise ValueError("Git provider not found for the given PR URL.")

        # Build index_name from repo and branch
        repo_name = git_provider.repo.replace('/', '_')
        branch_name = git_provider.pr.base.ref.replace('/', '_')
        index_name = f"{repo_name}_{branch_name}"
        return index_name

    def _get_repo_default_branch_index_name(self, git_provider):
        if not git_provider:
            raise ValueError("Git provider not found for the given PR URL.")

        # Build index_name from repo and branch
        repo_name = git_provider.repo.replace('/', '_')
        branch_name = git_provider.repo_obj.default_branch.replace('/', '_')
        index_name = f"{repo_name}_{branch_name}"
        return index_name

    def _does_index_exist(self, index_name: str):
        try:
            resp = self.rag_client.list_indexes()
            if resp and index_name in resp:
                return True
        except Exception as e:
            get_logger().error(f"Error checking index existence: {e}")
            raise e
        return False

    def _get_pr_docs_for_rag(self, git_provider):
        """
        Processes the pull request files and determines which documents need to be created, updated, or deleted
        in the RAG index based on the file changes in the PR.
        Args:
            git_provider: An object that provides access to the git repository and PR diff information.
        Returns:
            tuple: A tuple containing three lists:
                - create_docs (list): Documents to be created for newly added files.
                - update_docs (list): Documents to be updated for modified or renamed files.
                - deleted_docs (list): Documents to be deleted for removed files.
        """
        index_name = self._get_pr_head_index_name(git_provider)

        diff_files = git_provider.get_diff_files()
        deleted_docs = []
        update_docs = []
        create_docs = []
        existing_docs = {}
        for file_info in diff_files:
            curr_filename = file_info.filename
            if file_info.edit_type == EDIT_TYPE.RENAMED and file_info.old_filename:
                curr_filename = file_info.old_filename
            resp = self.rag_client.list_documents(index_name, metadata_filter={"file_name": curr_filename})
            if resp and resp.get("documents"):
                existing_docs[curr_filename] = resp["documents"][0]

        for file_info in diff_files:
            curr_doc = None
            if file_info.edit_type == EDIT_TYPE.RENAMED and file_info.old_filename and file_info.old_filename in existing_docs:
                curr_doc = existing_docs[file_info.old_filename]
            elif file_info.filename in existing_docs:
                curr_doc = existing_docs[file_info.filename]

            if not curr_doc:
                if file_info.edit_type == EDIT_TYPE.DELETED:
                    # If the file is deleted and we don't have a current document, skip it
                    get_logger().info(f"skipping deleted file with no exisitng index document {file_info.filename}.")
                    continue


            if file_info.edit_type == EDIT_TYPE.ADDED or not curr_doc:
                # Added files will be created
                doc = {
                    "text": file_info.head_file,
                    "metadata": {
                        "file_name": file_info.filename,
                    }
                }

                language = self.file_extension_to_language(file_info.filename)
                if language and language in self.valid_languages:
                    doc["metadata"]["language"] = language
                    doc["metadata"]["split_type"] = "code"

                create_docs.append(doc)
            elif file_info.edit_type == EDIT_TYPE.DELETED:
                # Deleted files will be marked for deletion
                deleted_docs.append(curr_doc)
            elif file_info.edit_type == EDIT_TYPE.MODIFIED:
                # Modified files will be updated
                curr_doc["text"] = file_info.head_file
                update_docs.append(curr_doc)
            elif file_info.edit_type == EDIT_TYPE.RENAMED:
                curr_doc["text"] = file_info.head_file
                curr_doc["metadata"]["file_name"] = file_info.filename
                update_docs.append(curr_doc)
            else:
                # Unknown edit type, handle as needed
                get_logger().warning(f"Unknown edit type for file {file_info.filename}: {file_info.edit_type}")
                continue
        return create_docs, update_docs, deleted_docs

    def create_base_branch_index(self, pr_url: str):
        """
        Creates an index of the base (default) branch files for a given pull request URL.
        This method retrieves the default branch from the repository associated with the provided PR URL,
        iterates through the files in the branch, and indexes their contents using the RAG client.

        Args:
            pr_url (str): The URL of the pull request for which to create the base branch index.
        Raises:
            ValueError: If the default branch cannot be found for the given PR URL.
            Exception: If an error occurs during document indexing.
        """
        git_provider = self._get_git_provider(pr_url)

        index_name = self._get_pr_base_index_name(git_provider)
        get_logger().info(f"Creating base branch index {index_name} for PR URL {pr_url}.")

        # Check if the index already exists
        if self._does_index_exist(index_name):
            get_logger().info(f"Index {index_name} already exists. Skipping creation.")
            return

        default_branch = git_provider.repo_obj.get_branch(git_provider.repo_obj.default_branch)
        if not default_branch:
            get_logger().error(f"Default branch {git_provider.repo_obj.default_branch} not found.")
            raise ValueError("Default branch not found for the given PR URL.")

        base_branch_tree = git_provider.repo_obj.get_git_tree(default_branch.commit.sha, recursive=True)
        batch_docs = []
        for file_info in base_branch_tree.tree:
            if file_info.type == "blob":
                # Might want to check file size / or other attributes here for filtering
                doc = {
                    "text": base64.b64decode(git_provider.repo_obj.get_git_blob(file_info.sha).content).decode(),
                    "metadata": {
                        "file_name": file_info.path,
                    }
                }
                language = self.file_extension_to_language(file_info.path)
                if language and language in self.valid_languages:
                    doc["metadata"]["language"] = language
                    doc["metadata"]["split_type"] = "code"

                batch_docs.append(doc)
            if len(batch_docs) >= 10:
                try:
                    self.rag_client.index_documents(index_name, batch_docs)
                except Exception as e:
                    get_logger().error(f"Error indexing documents: {e}")
                batch_docs = []
        if batch_docs:
            try:
                resp = self.rag_client.index_documents(index_name, batch_docs)
            except Exception as e:
                get_logger().error(f"Error indexing documents: {e}")
                raise e

    def update_base_branch_index(self, pr_url: str):
        """
        Updates the index for the base branch of a pull request.
        This method attempts to update the index associated with the base branch of the specified pull request URL.

        Args:
            pr_url (str): The URL of the pull request whose base branch index should be updated.
        Raises:
            Exception: Propagates any exception encountered during the update process.
        """
        try:
            git_provider = self._get_git_provider(pr_url)
            base_index_name = self._get_pr_base_index_name(git_provider)
            git_provider.p
            if not self._does_index_exist(base_index_name):
                return self.create_base_branch_index(pr_url)

            create_docs, update_docs, deleted_docs = self._get_pr_docs_for_rag(git_provider)

            if not deleted_docs and not update_docs and not create_docs:
                get_logger().info(f"No changes detected for PR URL {pr_url}.")
                return

            get_logger().info(f"Updating base index {base_index_name} for merged PR URL {pr_url}.")
            if deleted_docs:
                get_logger().info(f"Deleting documents in base index {base_index_name} for merged PR URL {pr_url}.")
                resp = self.rag_client.delete_documents(base_index_name, [doc["doc_id"] for doc in deleted_docs])
                get_logger().info(f"Deleted documents: {resp}")
            if update_docs:
                get_logger().info(f"Updating documents in base index {base_index_name} for merged PR URL {pr_url}.")
                resp = self.rag_client.update_documents(base_index_name, update_docs)
                get_logger().info(f"Updated documents: {resp}")
            if create_docs:
                get_logger().info(f"Creating documents in base index {base_index_name} for merged PR URL {pr_url}.")
                resp = self.rag_client.index_documents(base_index_name, create_docs)
                get_logger().info(f"Created documents: {resp}")
        except Exception as e:
            get_logger().error(f"Error updating documents: {e}")
            raise e

    def create_new_pr_index(self, pr_url: str):
        """
        Creates a new index for a pull request (PR) using the RAG (Retrieval-Augmented Generation) client.
        This method performs the following steps:
            1. Determines the git provider and computes the index names for the PR and the base branch.
            2. Checks if the base branch index exists; if not, it creates it.
            3. Persists the base branch index to a temporary path.
            4. Loads the base branch index into a new PR-specific index, overwriting any existing index with the same name.
            5. Updates the new PR index with PR-specific data.
        Args:
            pr_url (str): The URL of the pull request for which to create the index.
        Raises:
            Exception: If any error occurs during the index creation process, it is logged and re-raised.
        """
        git_provider = self._get_git_provider(pr_url)

        index_name = self._get_pr_head_index_name(git_provider)
        base_index_name = self._get_pr_base_index_name(git_provider)

        try:
            # Check if the base branch index already exists
            if not self._does_index_exist(base_index_name):
                self.create_base_branch_index(pr_url)

            # On create calls we will always overwrite the index in case of branch reusage
            get_logger().info(f"Creating new index {index_name} for PR URL {pr_url}.")
            self.rag_client.persist_index(base_index_name, path=f"/tmp/{base_index_name}")
            self.rag_client.load_index(index_name, path=f"/tmp/{base_index_name}", overwrite=True)

            self.update_pr_index(pr_url)

        except Exception as e:
            get_logger().error(f"Error creating new pr index: {e}")
            raise e

    def update_pr_index(self, pr_url: str):
        """
        Updates the RAG index for a given PR URL by synchronizing document changes based on file diffs.
        This method processes the files changed in the PR and updates the corresponding index by:
            - Creating documents for newly added files.
            - Updating documents for modified or renamed files.
            - Deleting documents for removed files.
        If `for_base_branch` is True, updates are applied to the base branch index instead of the PR-specific index.
        Args:
            pr_url (str): The URL of the pull request to update the index for.
            for_base_branch (bool, optional): If True, updates the base branch index. Defaults to False.
        Raises:
            Exception: If any error occurs during the update process.
        """
        try:
            git_provider = self._get_git_provider(pr_url)
            index_name = self._get_pr_head_index_name(git_provider)
            if not self._does_index_exist(index_name):
                return self.create_new_pr_index(pr_url)

            create_docs, update_docs, deleted_docs = self._get_pr_docs_for_rag(git_provider)

            if not deleted_docs and not update_docs and not create_docs:
                get_logger().info(f"No changes detected for PR URL {pr_url}.")
                return

            get_logger().info(f"Updating index {index_name} for PR URL {pr_url}.")
            if deleted_docs:
                get_logger().info(f"Deleting documents from index {index_name} for PR URL {pr_url}.")
                resp = self.rag_client.delete_documents(index_name, [doc["doc_id"] for doc in deleted_docs])
                get_logger().info(f"Deleted documents: {resp}")
            if update_docs:
                get_logger().info(f"Updating documents in index {index_name} for PR URL {pr_url}.")
                resp = self.rag_client.update_documents(index_name, update_docs)
                get_logger().info(f"Updated documents: {resp}")
            if create_docs:
                get_logger().info(f"Creating documents in index {index_name} for PR URL {pr_url}.")
                resp = self.rag_client.index_documents(index_name, create_docs)
                get_logger().info(f"Created documents: {resp}")
        except Exception as e:
            get_logger().error(f"Error updating documents: {e}")
            raise e

    def delete_pr_index(self, pr_url: str):
        """
        Deletes the RAG index for a given pull request (PR) URL.
        This method retrieves the git provider for the PR URL, constructs the index name,
        and deletes the index using the RAG client.
        Args:
            pr_url (str): The URL of the pull request whose index should be deleted.
        Raises:
            Exception: If an error occurs during the deletion process.
        """
        try:
            git_provider = self._get_git_provider(pr_url)
            index_name = self._get_pr_head_index_name(git_provider)
            if not self._does_index_exist(index_name):
                get_logger().info(f"Index {index_name} does not exist. No action taken.")
                return
            get_logger().info(f"Deleting index {index_name} for PR URL {pr_url}.")
            self.rag_client.delete_index(index_name)
        except Exception as e:
            get_logger().error(f"Error deleting PR index: {e}")
            raise e

    def file_extension_to_language(self, filename: str):
        """
        Given a filename, returns the programming language associated with its extension or special name.
        This method checks for special filenames (e.g., 'Makefile', 'Dockerfile') and standard file extensions
        and returns the corresponding language.
        Args:
            filename (str): The name of the file to check.
        Returns:
            str or None: The programming language associated with the file, or None if not found.
        """
        # check for things like Makefile, Dockerfile, etc.
        if filename in self.file_extension_to_language_map:
            return self.file_extension_to_language_map[filename]

        _, extension = os.path.splitext(filename)
        if extension in self.file_extension_to_language_map:
            return self.file_extension_to_language_map[extension]
        else:
            return None
