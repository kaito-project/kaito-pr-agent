docker run --rm -it \
 -e CONFIG.MODEL="hosted_vllm/qwen2.5-coder-7b-instruct" \
 -e CONFIG.FALLBACK_MODELS="hosted_vllm/qwen2.5-coder-7b-instruct" \
 -e CONFIG.CUSTOM_MODEL_MAX_TOKENS="32768" \
 -e CONFIG.DUPLICATE_EXAMPLES="true" \
 -e GITHUB.USER_TOKEN="<GITHUB_TOKEN>" \
 -e GITHUB.DEPLOYMENT_TYPE="user" \
 -e OLLAMA.API_BASE="http://host.docker.internal:5000/v1" \
 codiumai/pr-agent:latest --pr_url <PR_URL_HERE> review
