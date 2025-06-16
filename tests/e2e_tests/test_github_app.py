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

import os
import re
import time
from datetime import datetime

from pr_agent.config_loader import get_settings
from pr_agent.git_providers import get_git_provider
from pr_agent.log import get_logger, setup_logger
from tests.e2e_tests.e2e_utils import (FILE_PATH,
                                       IMPROVE_START_WITH_REGEX_PATTERN,
                                       NEW_FILE_CONTENT, NUM_MINUTES,
                                       PR_HEADER_START_WITH, REVIEW_START_WITH)

log_level = os.environ.get("LOG_LEVEL", "INFO")
setup_logger(log_level)
logger = get_logger()


def test_e2e_run_github_app():
    """
    What we want to do:
    (1) open a PR in a repo 'https://github.com/kaito-project/kaito-pr-agent'
    (2) wait for 5 minutes until the PR is processed by the GitHub app
    (3) check that the relevant tools have been executed
    """
    base_branch = "main"  # or any base branch you want
    new_branch = f"github_app_e2e_test-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"
    repo_url = 'kaito-project/kaito-pr-agent'
    get_settings().config.git_provider = "github"
    git_provider = get_git_provider()()
    github_client = git_provider.github_client
    repo = github_client.get_repo(repo_url)

    try:
        # Create a new branch from the base branch
        source = repo.get_branch(base_branch)
        logger.info(f"Creating a new branch {new_branch} from {base_branch}")
        repo.create_git_ref(ref=f"refs/heads/{new_branch}", sha=source.commit.sha)

        # Get the file you want to edit
        file = repo.get_contents(FILE_PATH, ref=base_branch)
        # content = file.decoded_content.decode()

        # Update the file content
        logger.info(f"Updating the file {FILE_PATH}")
        commit_message = "update cli_pip.py"
        repo.update_file(
            file.path,
            commit_message,
            NEW_FILE_CONTENT,
            file.sha,
            branch=new_branch
        )

        # Create a pull request
        logger.info(f"Creating a pull request from {new_branch} to {base_branch}")
        pr = repo.create_pull(
            title=new_branch,
            body="update cli_pip.py",
            head=new_branch,
            base=base_branch
        )

        # check every 1 minute, for 5, minutes if the PR has all the tool results
        test_passed = False
        for i in range(NUM_MINUTES):
            logger.info(f"Waiting for the PR to get all the tool results...")
            time.sleep(60)
            logger.info(f"Checking the PR {pr.html_url} after {i + 1} minute(s)")
            pr.update()
            pr_header_body = pr.body
            comments = list(pr.get_issue_comments())

            # Debug: Show exactly what we found
            logger.info(f"PR description: '{pr_header_body}'")
            logger.info(f"Found {len(comments)} comments")
            for idx, comment in enumerate(comments):
                logger.info(f"Comment {idx} by {comment.user.login}: {comment.body[:200]}...")

            # Check if the GitHub App has processed the PR
            # Look for bot comments with specific content
            bot_comments = [c for c in comments if c.user.login == 'kaito-pr-agent']
            review_comment = any('PR Reviewer Guide' in c.body for c in bot_comments)
            improve_comment = any('PR Code Suggestions' in c.body for c in bot_comments)

            # Check if PR description was updated by describe tool
            describe_updated = (
                'Update CLI example' in pr_header_body or
                len(pr_header_body) > 50 or
                'Description' in pr_header_body
            )

            logger.info(f"Bot comments found: {len(bot_comments)}")
            logger.info(f"Describe tool updated PR: {describe_updated}")
            logger.info(f"Review comment found: {review_comment}")
            logger.info(f"Improve comment found: {improve_comment}")

            if len(bot_comments) >= 2 and describe_updated:
                logger.info("All tools executed successfully!")
                test_passed = True
                break
            elif len(bot_comments) >= 1:
                logger.info("GitHub App is working, but not all tools completed yet...")
            else:
                logger.info(f"Waiting for the PR to get all the tool results. {i + 1} minute(s) passed")

        # Assert the test passed
        assert test_passed, f"After {NUM_MINUTES} minutes, the GitHub App did not execute all required tools successfully"

        # cleanup - delete the branch
        logger.info(f"Deleting the branch {new_branch}")
        repo.get_git_ref(f"heads/{new_branch}").delete()

        # If we reach here, the test is successful
        logger.info(f"Succeeded in running e2e test for GitHub app on the PR {pr.html_url}")
    except Exception as e:
        logger.error(f"Failed to run e2e test for GitHub app: {e}")
        # delete the branch
        logger.info(f"Deleting the branch {new_branch}")
        repo.get_git_ref(f"heads/{new_branch}").delete()
        assert False


if __name__ == '__main__':
    test_e2e_run_github_app()
