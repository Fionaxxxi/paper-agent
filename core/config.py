from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LLM
    OPENAI_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    OPENAI_API_KEY: str = ""
    MODEL_NAME: str = "qwen-max"
    MODEL_INPUT_COST_PER_1M_TOKENS: float = 0.0
    MODEL_OUTPUT_COST_PER_1M_TOKENS: float = 0.0

    # Retrieval
    RETRIEVAL_MODE: str = "arxiv"
    ARXIV_MAX_RESULTS: int = 5
    MULTI_SOURCE_PROVIDERS: str = "arxiv,openalex"
    MULTI_SOURCE_MAX_RESULTS: int = 8
    MULTI_SOURCE_RERANK_ENABLED: bool = False
    MULTI_SOURCE_METADATA_VERIFICATION_ENABLED: bool = False
    ARXIV_AUTHORITY_VERIFICATION_ENABLED: bool = False

    # OpenAlex
    OPENALEX_BASE_URL: str = "https://api.openalex.org"
    OPENALEX_API_KEY: str = ""
    OPENALEX_MAILTO: str = ""
    OPENALEX_MAX_RESULTS: int = 5

    # Crossref candidate authority provider
    CROSSREF_BASE_URL: str = "https://api.crossref.org"
    CROSSREF_MAILTO: str = ""

    # Semantic Scholar candidate authority provider
    SEMANTIC_SCHOLAR_BASE_URL: str = "https://api.semanticscholar.org/graph/v1"
    SEMANTIC_SCHOLAR_API_KEY: str = ""

    # Tool execution
    TOOL_TIMEOUT_SECONDS: float = 45.0

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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
