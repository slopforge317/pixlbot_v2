"""Authentication exceptions."""


class AuthError(Exception):
    """Base authentication error."""

    pass


class InvalidInitDataError(AuthError):
    """InitData signature validation failed."""

    pass


class ExpiredInitDataError(AuthError):
    """InitData auth_date is too old."""

    pass


class MissingInitDataError(AuthError):
    """Authorization header missing or malformed."""

    pass
