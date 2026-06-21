from errors.error_codes import ErrorCode


class PaperAgentError(Exception):
    """
    PaperAgent 项目基础异常。
    所有自定义异常都可以继承这个类。
    """

    def __init__(
        self,
        message: str,
        code: str = ErrorCode.INTERNAL_ERROR,
    ):
        self.message = message
        self.code = code
        super().__init__(message)


class InvalidQueryError(PaperAgentError):
    def __init__(self, message: str = "query 不能为空"):
        super().__init__(
            message=message,
            code=ErrorCode.INVALID_QUERY,
        )


class AgentExecutionError(PaperAgentError):
    def __init__(self, message: str = "PaperAgent 执行失败"):
        super().__init__(
            message=message,
            code=ErrorCode.AGENT_EXECUTION_ERROR,
        )


class SkillExecutionError(PaperAgentError):
    def __init__(self, message: str = "Skill 执行失败"):
        super().__init__(
            message=message,
            code=ErrorCode.SKILL_ERROR,
        )