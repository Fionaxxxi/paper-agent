from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LLM
    OPENAI_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    OPENAI_API_KEY: str = "sk-ws-H.RPMPEDD.Cuj7.MEUCIQCUwAgrylE4oGBFLwZSzfULXmKPHejwn7IDVoFyC4-2oQIgcQUtnVqQrvHcJUoIjS8JfTnsdDVOMG9B_WYWdl9J54o"
    MODEL_NAME: str = "qwen-max"

    # Retrieval
    RETRIEVAL_MODE: str = "arxiv"
    ARXIV_MAX_RESULTS: int = 5

    # Evaluation
    EVALUATE_WITH_LLM: bool = False

    # Generation
    LLM_TIMEOUT: int = 120
    MAX_GENERATE_DOCS: int = 3
    DOC_CONTENT_LIMIT: int = 1000

    # PDF
    PDF_MAX_CHARS: int = 12000

    # Cache
    CACHE_DIR: str = "data/cache"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/paper_agent.log"

    REASON_WITH_LLM: bool = True
    REASON_CONFIDENCE_THRESHOLD: float = 0.75

    # Cache
    CACHE_DIR: str = "data/cache"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()