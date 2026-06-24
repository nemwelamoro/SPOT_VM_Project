# model_registry.py

MODEL_REGISTRY = {
    "t5-small": {
        "gcs_path": "t5-small/v1.0.0/",
        "description": "T5 Small - Lightweight summarization model",
        "engine": "transformers"          # We'll use vLLM later for LLMs
    # },
    # "llama3-8b": {
    #     "gcs_path": "llama3-8b-instruct/",
    #     "description": "Meta Llama 3 8B Instruct",
    #     "engine": "vllm"
    # },
    # "qwen2.5-7b": {
    #     "gcs_path": "qwen2.5-7b-instruct/",
    #     "description": "Qwen 2.5 7B Instruct",
    #     "engine": "vllm"
    # },
    # "deepseek-v3": {
    #     "gcs_path": "deepseek-v3/",
    #     "description": "DeepSeek V3",
    #     "engine": "vllm"
    }
}
