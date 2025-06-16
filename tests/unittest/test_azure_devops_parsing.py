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

from pr_agent.git_providers import AzureDevopsProvider


class TestAzureDevOpsParsing():
    def test_regular_address(self):
        pr_url = "https://dev.azure.com/organization/project/_git/repo/pullrequest/1"

        # workspace_slug, repo_slug, pr_number
        assert AzureDevopsProvider._parse_pr_url(pr_url) == ("project", "repo", 1)

    def test_visualstudio_address(self):
        pr_url = "https://organization.visualstudio.com/project/_git/repo/pullrequest/1"

        # workspace_slug, repo_slug, pr_number
        assert AzureDevopsProvider._parse_pr_url(pr_url) == ("project", "repo", 1)

    def test_self_hosted_address(self):
        pr_url = "http://server.be:8080/tfs/department/project/_git/repo/pullrequest/1"

        # workspace_slug, repo_slug, pr_number
        assert AzureDevopsProvider._parse_pr_url(pr_url) == ("project", "repo", 1)
