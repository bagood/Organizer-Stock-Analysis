class ApplicationError(Exception):
    """Base exception for expected application failures."""


class UsernameAlreadyExistsError(ApplicationError):
    pass


class InvalidCredentialsError(ApplicationError):
    pass


class InactiveUserError(ApplicationError):
    pass


class InvalidTokenError(ApplicationError):
    pass


class PortfolioNotFoundError(ApplicationError):
    pass


class DuplicateTickerError(ApplicationError):
    pass
