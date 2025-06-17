# KAITO PR-Agent

<div align="center">

**AI-powered code review automation using KAITO as the backend**

This is a fork of [qodo-ai/pr-agent](https://github.com/qodo-ai/pr-agent) modified for the KAITO project.
See [NOTICE](NOTICE) for attribution details.

</div>

## Why We Forked PR-Agent

We forked [qodo-ai/pr-agent](https://github.com/qodo-ai/pr-agent) to integrate **KAITO RAGEngine** as the backend, improving PR-Agent's performance by gathering additional context from your codebase. This enhanced contextual understanding allows for more accurate code reviews, better suggestions, and smarter PR descriptions.

---

## 🚀 Quick Start

Get started in minutes with GitHub integration:

> **Prerequisites:** You'll need a [KAITO inference workspace](https://github.com/kaito-project/kaito) running with your preferred model.

### GitHub Action (Recommended)
Easy setup, no infrastructure needed. **[Setup Guide →](docs/docs/installation/github.md#run-as-a-github-action)**

### GitHub App (Advanced)
More control, runs in your infrastructure. **[Setup Guide →](docs/docs/installation/github.md#run-as-a-github-app)**

**📚 Essential KAITO Documentation:**
- **[KAITO Inference Workspaces](https://github.com/kaito-project/kaito#quick-start)** - Setup and configure inference workspaces
- **[KAITO RAG Engine](https://github.com/kaito-project/kaito/blob/main/docs/RAG/README.md)** - RAG capabilities and configuration (open-source release coming soon in v0.5.0)

> **Live Example:** The kaito-pr-agent GitHub App with Qwen2.5-Coder-32B model is actively reviewing all PRs in the [KAITO repository](https://github.com/Azure/kaito).

---

### Architecture Diagram
This diagram illustrates how the PR-Agent GitHub app works with KAITO.

![Architecture Diagram](kaito-pr-agent-diagram.png)

**Key Components & Their Significance:**

- **🔄 GitHub App** - Receives PR events, manages comments, and handles authentication
- **🤖 PR-Agent Pod** - Orchestrates the analysis workflow and manages tool execution (`/review`, `/describe`, `/improve`)
- **⚡ KAITO Workspace** - Provides scalable Kubernetes-native AI model serving with automatic GPU provisioning
- **🧠 KAITO RAGEngine** - Enriches context by retrieving relevant code snippets and documentation from your codebase

---

## Setup & Usage

### 1. Run with Docker
For quick testing, use the script below:

```bash
chmod +x scripts/run_docker.sh
./scripts/run_docker.sh
```

### 2. Run in Kubernetes
Apply the job manifest:
```bash
kubectl apply -f config/pr-agent-job.yaml
```

### 3. Run in GitHub Actions

Use the provided workflow in `.github/pr-review.yaml` to automate PR reviews.

---

## Configuration

In all setups, replace the following placeholders with your actual values:

- **OLLAMA_API_BASE** → Your KAITO inference workspace URL
- **GITHUB_USER_TOKEN** → Your GitHub API token
- **PR_URL** → The pull request URL to review

Ensure these values are correctly set in your Docker environment, Kubernetes job, or GitHub Actions workflow before running.

## Supported Features

- **Auto Review** (`/review`): AI-powered code review with security and quality feedback
- **Auto Description** (`/describe`): Generate PR titles, summaries, and labels
- **Code Suggestions** (`/improve`): Get improvement suggestions for your code
- **Question Answering** (`/ask`): Ask questions about the PR changes

## Links

- **Original Project**: [qodo-ai/pr-agent](https://github.com/qodo-ai/pr-agent)
- **KAITO Project**: [kaito-project/kaito](https://github.com/kaito-project/kaito)
- **Documentation**: [KAITO Docs](https://github.com/kaito-project/kaito/tree/main/docs)
- **Support**: Open an issue in this repository

## License

See [LICENSE](LICENSE) for license information.

## Credits

This project is a fork of [qodo-ai/pr-agent](https://github.com/qodo-ai/pr-agent). All credit for the original work and core functionality goes to the qodo-ai/pr-agent authors and contributors. We are grateful for their excellent work that made this fork possible.

For detailed attribution information, see [NOTICE](NOTICE).

## Contact

"KAITO devs" <kaito-dev@microsoft.com>
