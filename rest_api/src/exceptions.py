class AppError(Exception):
    def __init__(self, error_message: str):
        super().__init__(error_message)
        self.error_message = error_message


class RepoNotFoundException(AppError):
    def __init__(self, error_message: str):
        super().__init__(error_message)


class GithubUnreachableException(AppError):
    def __init__(self, error_message: str):
        super().__init__(error_message)


class GitCommandFailedException(AppError):
    def __init__(self, error_message: str):
        super().__init__(error_message)
