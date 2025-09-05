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

from starlette_context import context

from pr_agent.config_loader import get_settings
from pr_agent.git_providers.azuredevops_provider import AzureDevopsProvider
from pr_agent.git_providers.bitbucket_provider import BitbucketProvider
from pr_agent.git_providers.bitbucket_server_provider import \
    BitbucketServerProvider
from pr_agent.git_providers.codecommit_provider import CodeCommitProvider
from pr_agent.git_providers.gerrit_provider import GerritProvider
from pr_agent.git_providers.git_provider import GitProvider
from pr_agent.git_providers.gitea_provider import GiteaProvider
from pr_agent.git_providers.github_provider import GithubProvider
from pr_agent.git_providers.gitlab_provider import GitLabProvider
from pr_agent.git_providers.local_git_provider import LocalGitProvider

_GIT_PROVIDERS = {
    'github': GithubProvider,
    'gitlab': GitLabProvider,
    'bitbucket': BitbucketProvider,
    'bitbucket_server': BitbucketServerProvider,
    'azure': AzureDevopsProvider,
    'codecommit': CodeCommitProvider,
    'local': LocalGitProvider,
    'gerrit': GerritProvider,
    'gitea': GiteaProvider,
}


def get_git_provider():
    try:
        provider_id = get_settings().config.git_provider
    except AttributeError as e:
        raise ValueError("git_provider is a required attribute in the configuration file") from e
    if provider_id not in _GIT_PROVIDERS:
        raise ValueError(f"Unknown git provider: {provider_id}")
    return _GIT_PROVIDERS[provider_id]


def get_git_provider_with_context(pr_url) -> GitProvider:
    """
    Get a GitProvider instance for the given PR URL. If the GitProvider instance is already in the context, return it.
    """

    is_context_env = None
    try:
        is_context_env = context.get("settings", None)
    except Exception:
        pass  # we are not in a context environment (CLI)

    # check if context["git_provider"]["pr_url"] exists
    if is_context_env and context.get("git_provider", {}).get("pr_url", {}):
        git_provider = context["git_provider"]["pr_url"]
        # possibly check if the git_provider is still valid, or if some reset is needed
        # ...
        return git_provider
    else:
        try:
            provider_id = get_settings().config.git_provider
            if provider_id not in _GIT_PROVIDERS:
                raise ValueError(f"Unknown git provider: {provider_id}")
            git_provider = _GIT_PROVIDERS[provider_id](pr_url)
            if is_context_env:
                context["git_provider"] = {pr_url: git_provider}
            return git_provider
        except Exception as e:
            raise ValueError(f"Failed to get git provider for {pr_url}") from e
            
            
def get_git_provider_for_repo(url: str) -> GitProvider:
    """
    Get a GitProvider instance for a repository URL, PR URL, or issue URL.
    
    If the URL is an issue URL or API URL, it will extract the repository information
    and properly initialize the provider with the repository name and object.
    This ensures that when working with issues or API URLs, we properly set up the provider
    with all necessary repository information.
    
    Args:
        url: The URL of the repository, PR, or issue.
    
    Returns:
        A GitProvider instance initialized with the repository information.
    """
    from urllib.parse import urlparse
    from pr_agent.log import get_logger
    
    # Get the appropriate provider class
    provider_class = get_git_provider()
    
    try:
        # Initialize the provider with the URL
        provider = provider_class(url)
        
        # If this is an issue URL, handle repository extraction
        if '/issues/' in url:
            # Extract the repository URL from the issue URL
            repo_url = url.split('/issues/')[0]
            get_logger().info(f"Extracted repository URL {repo_url} from issue URL")
            
            # For API URLs, extract repository name from path
            parsed_url = urlparse(url)
            path_parts = parsed_url.path.strip('/').split('/')
            
            # Handle different URL formats
            repo_name = None
            if 'api.github.com' in parsed_url.netloc and len(path_parts) >= 3 and path_parts[0] == 'repos':
                # API URL format: https://api.github.com/repos/{owner}/{repo}
                repo_name = '/'.join(path_parts[1:3])  # owner/repo format
            elif len(path_parts) >= 2 and '/issues/' in url:
                # Regular URL format: https://github.com/{owner}/{repo}/issues/{num}
                repo_name = '/'.join(path_parts[:2])
                
            # Set repository properties if we extracted a name
            if repo_name and hasattr(provider, 'repo') and hasattr(provider, 'github_client'):
                # Set repository properties properly
                provider.repo = repo_name
                provider.repo_obj = provider.github_client.get_repo(repo_name)
                
        return provider
    except Exception as e:
        get_logger().error(f"Failed to initialize git provider with URL {url}: {str(e)}")
        # If initialization fails completely, re-raise the exception
        raise e
