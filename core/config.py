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
    LOCAL_RAG_MAX_RESULTS: int = 5
    ARXIV_MAX_RESULTS: int = 5
    MULTI_SOURCE_PROVIDERS: str = "arxiv,openalex"
    MULTI_SOURCE_MAX_RESULTS: int = 8
    MULTI_SOURCE_RERANK_ENABLED: bool = False
    MULTI_SOURCE_METADATA_VERIFICATION_ENABLED: bool = False
    ARXIV_AUTHORITY_VERIFICATION_ENABLED: bool = False
    DOI_AUTHORITY_VERIFICATION_ENABLED: bool = False
    MULTI_SOURCE_PARALLEL_ENABLED: bool = False
    MULTI_SOURCE_MAX_WORKERS: int = 2
    MULTI_QUERY_PARALLEL_ENABLED: bool = False
    MULTI_QUERY_MAX_WORKERS: int = 2

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

    # Zotero read-only MCP
    ZOTERO_API_BASE_URL: str = "https://api.zotero.org"
    ZOTERO_LIBRARY_TYPE: str = "user"
    ZOTERO_LIBRARY_ID: str = ""
    ZOTERO_API_KEY: str = ""
    ZOTERO_MAX_RESULTS: int = 5

    # GitHub read-only MCP
    GITHUB_API_BASE_URL: str = "https://api.github.com"
    GITHUB_TOKEN: str = ""
    GITHUB_MAX_RESULTS: int = 5

    # Tool execution
    TOOL_TIMEOUT_SECONDS: float = 45.0

    # Evaluation
    EVALUATE_WITH_LLM: bool = False

    # Generation
    LLM_TIMEOUT: int = 120
    MAX_GENERATE_DOCS: int = 3
    DOC_CONTENT_LIMIT: int = 1000
    ANSWER_REFLECTION_ENABLED: bool = True

    # PDF
    PDF_MAX_CHARS: int = 12000

    # Cache
    CACHE_DIR: str = "data/cache"

    # Structured memory (kept inside the D-drive project by default)
    MEMORY_DB_PATH: str = "data/memory/paper_agent_memory.db"
    MEMORY_RECENT_MESSAGES: int = 6
    MEMORY_SUMMARY_MAX_CHARS: int = 1200
    MEMORY_CONTEXT_MAX_CHARS: int = 2400
    LLM_WIKI_DIR: str = "data/wiki"
    LLM_WIKI_AUTO_PUBLISH_ENABLED: bool = False
    LLM_WIKI_ALLOWED_TASK_TYPES: str = (
        "summarize,compare,recommend,literature_review,paper_critique"
    )
    LANGGRAPH_CHECKPOINT_ENABLED: bool = True
    LANGGRAPH_CHECKPOINT_DB_PATH: str = "data/memory/langgraph_checkpoints.db"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/paper_agent.log"

    REASON_WITH_LLM: bool = True
    REASON_CONFIDENCE_THRESHOLD: float = 0.75
    RESEARCH_ANALYSIS_WITH_LLM: bool = True
    RESEARCH_ANALYZER_PROMPT_VARIANT: str = "zero_shot"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
