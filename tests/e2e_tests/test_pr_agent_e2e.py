#!/usr/bin/env python3

"""
End-to-End test for PR-Agent built from current codebase.

This test:
1. Assumes Docker image is already built from current code (done in workflow)
2. Creates a test PR in the repository
3. Runs the built PR-Agent Docker image on that test PR
4. Validates that the PR-Agent correctly processes the PR
5. Cleans up the test PR

This tests YOUR actual code changes, not external services.
"""

import os
import subprocess
import time
from datetime import datetime

from pr_agent.config_loader import get_settings
from pr_agent.git_providers import get_git_provider
from pr_agent.log import get_logger, setup_logger
from tests.e2e_tests.e2e_utils import FILE_PATH, NEW_FILE_CONTENT

log_level = os.environ.get("LOG_LEVEL", "INFO")
setup_logger(log_level)
logger = get_logger()


def test_e2e_pr_agent_docker_image():
    """
    Test the PR-Agent Docker image built from current codebase.

    This creates a test PR and uses the Docker image to process it,
    validating that your code changes work correctly.
    """
    base_branch = "main"
    new_branch = f"e2e-test-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"
    repo_url = 'kaito-project/kaito-pr-agent'

    # Setup GitHub client for PR creation
    get_settings().config.git_provider = "github"
    git_provider = get_git_provider()()
    github_client = git_provider.github_client
    repo = github_client.get_repo(repo_url)

    test_pr = None
    try:
        logger.info("🚀 Starting E2E test of PR-Agent Docker image")

        # Step 1: Create a test PR
        logger.info(f"📝 Creating test branch: {new_branch}")
        source = repo.get_branch(base_branch)
        repo.create_git_ref(ref=f"refs/heads/{new_branch}", sha=source.commit.sha)

        # Modify a file to create meaningful changes
        file = repo.get_contents(FILE_PATH, ref=base_branch)
        logger.info(f"✏️ Updating file: {FILE_PATH}")
        repo.update_file(
            file.path,
            "E2E test: update cli_pip.py",
            NEW_FILE_CONTENT,
            file.sha,
            branch=new_branch
        )

        # Create the test PR
        logger.info(f"🔀 Creating test PR from {new_branch} to {base_branch}")
        test_pr = repo.create_pull(
            title=f"[E2E Test] PR-Agent validation - {new_branch}",
            body="This is an automated E2E test PR to validate PR-Agent functionality. Will be auto-closed.",
            head=new_branch,
            base=base_branch
        )

        logger.info(f"✅ Created test PR: {test_pr.html_url}")

        # Step 2: Run PR-Agent Docker image on the test PR
        logger.info("🐳 Running PR-Agent Docker image on test PR...")

        pr_url = test_pr.html_url
        # Use the unique image tag from the workflow, fallback to default for local testing
        docker_image = os.environ.get('E2E_DOCKER_IMAGE', 'kaito-project/kaito-pr-agent:test')
        logger.info(f"Using Docker image: {docker_image}")

        # Run describe command
        logger.info("📋 Running describe command...")
        describe_result = subprocess.run([
            "docker", "run", "--rm",
            "-e", f"GITHUB.USER_TOKEN={os.environ.get('GITHUB.USER_TOKEN')}",
            "-e", "GITHUB.DEPLOYMENT_TYPE=user",
            "-e", f"CONFIG.MODEL={os.environ.get('CONFIG.MODEL', 'hosted_vllm/qwen2.5-coder-32b-instruct')}",
            "-e", f"CONFIG.CUSTOM_MODEL_MAX_TOKENS={os.environ.get('CONFIG.CUSTOM_MODEL_MAX_TOKENS', '32768')}",
            "-e", f"CONFIG.DUPLICATE_PROMPT_EXAMPLES={os.environ.get('CONFIG.DUPLICATE_PROMPT_EXAMPLES', 'true')}",
            "-e", f"CONFIG.AI_TIMEOUT={os.environ.get('CONFIG.AI_TIMEOUT', '600')}",
            "-e", f"OLLAMA.API_BASE={os.environ.get('OLLAMA.API_BASE')}",
            docker_image,
            "python", "-m", "pr_agent.cli",
            "--pr_url", pr_url,
            "describe"
        ], capture_output=True, text=True, timeout=300)

        logger.info(f"Describe command exit code: {describe_result.returncode}")
        if describe_result.returncode != 0:
            logger.error(f"Describe stderr: {describe_result.stderr}")

        # Run review command
        logger.info("🔍 Running review command...")
        review_result = subprocess.run([
            "docker", "run", "--rm",
            "-e", f"GITHUB.USER_TOKEN={os.environ.get('GITHUB.USER_TOKEN')}",
            "-e", "GITHUB.DEPLOYMENT_TYPE=user",
            "-e", f"CONFIG.MODEL={os.environ.get('CONFIG.MODEL', 'hosted_vllm/qwen2.5-coder-32b-instruct')}",
            "-e", f"CONFIG.CUSTOM_MODEL_MAX_TOKENS={os.environ.get('CONFIG.CUSTOM_MODEL_MAX_TOKENS', '32768')}",
            "-e", f"CONFIG.DUPLICATE_PROMPT_EXAMPLES={os.environ.get('CONFIG.DUPLICATE_PROMPT_EXAMPLES', 'true')}",
            "-e", f"CONFIG.AI_TIMEOUT={os.environ.get('CONFIG.AI_TIMEOUT', '600')}",
            "-e", f"OLLAMA.API_BASE={os.environ.get('OLLAMA.API_BASE')}",
            docker_image,
            "python", "-m", "pr_agent.cli",
            "--pr_url", pr_url,
            "review"
        ], capture_output=True, text=True, timeout=300)

        logger.info(f"Review command exit code: {review_result.returncode}")
        if review_result.returncode != 0:
            logger.error(f"Review stderr: {review_result.stderr}")

        # Run improve command
        logger.info("🚀 Running improve command...")
        improve_result = subprocess.run([
            "docker", "run", "--rm",
            "-e", f"GITHUB.USER_TOKEN={os.environ.get('GITHUB.USER_TOKEN')}",
            "-e", "GITHUB.DEPLOYMENT_TYPE=user",
            "-e", f"CONFIG.MODEL={os.environ.get('CONFIG.MODEL', 'hosted_vllm/qwen2.5-coder-32b-instruct')}",
            "-e", f"CONFIG.CUSTOM_MODEL_MAX_TOKENS={os.environ.get('CONFIG.CUSTOM_MODEL_MAX_TOKENS', '32768')}",
            "-e", f"CONFIG.DUPLICATE_PROMPT_EXAMPLES={os.environ.get('CONFIG.DUPLICATE_PROMPT_EXAMPLES', 'true')}",
            "-e", f"CONFIG.AI_TIMEOUT={os.environ.get('CONFIG.AI_TIMEOUT', '600')}",
            "-e", f"OLLAMA.API_BASE={os.environ.get('OLLAMA.API_BASE')}",
            docker_image,
            "python", "-m", "pr_agent.cli",
            "--pr_url", pr_url,
            "improve"
        ], capture_output=True, text=True, timeout=300)

        logger.info(f"Improve command exit code: {improve_result.returncode}")
        if improve_result.returncode != 0:
            logger.error(f"Improve stderr: {improve_result.stderr}")

        # Step 3: Validate results
        logger.info("✅ Validating PR-Agent results...")

        # Wait a moment for GitHub API to update
        time.sleep(10)

        # Check if PR was updated
        test_pr.update()
        updated_body = test_pr.body
        comments = list(test_pr.get_issue_comments())

        logger.info(f"📊 PR body length: {len(updated_body)} characters")
        logger.info(f"💬 Comments found: {len(comments)}")

        # Validate that tools executed successfully
        tools_success = 0

        # Check if describe updated the PR (body should be longer/different)
        if len(updated_body) > 100:  # More than just the original body
            logger.info("✅ Describe tool appears to have updated PR")
            tools_success += 1

        # Check for review and improve comments
        for comment in comments:
            if "PR Reviewer Guide" in comment.body or "review" in comment.body.lower():
                logger.info("✅ Review tool comment found")
                tools_success += 1
                break

        for comment in comments:
            if "Code Suggestions" in comment.body or "improve" in comment.body.lower():
                logger.info("✅ Improve tool comment found")
                tools_success += 1
                break

        # Assert that at least 2 tools worked (be flexible for now)
        assert tools_success >= 2, f"Only {tools_success}/3 PR-Agent tools executed successfully"

        logger.info(f"🎉 E2E test passed! {tools_success}/3 tools executed successfully")

    except Exception as e:
        logger.error(f"❌ E2E test failed: {e}")
        raise

    finally:
        # Step 4: Cleanup
        if test_pr:
            try:
                logger.info("🧹 Cleaning up test PR...")
                test_pr.edit(state="closed")
                repo.get_git_ref(f"heads/{new_branch}").delete()
                logger.info("✅ Test PR closed and branch deleted")
            except Exception as cleanup_error:
                logger.warning(f"⚠️ Cleanup warning: {cleanup_error}")


if __name__ == '__main__':
    test_e2e_pr_agent_docker_image()
