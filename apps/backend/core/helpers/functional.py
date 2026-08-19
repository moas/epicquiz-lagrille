import enum  # noqa: I001
import secrets
import string


USERNAME_ALPHABET = "".join(
    character
    for character in string.ascii_uppercase + string.digits
    if character not in {"0", "O", "I", "L"}
)


def generate_username(size: int) -> str:
    """Generate a readable username without ambiguous characters."""
    if size < 1:
        message = "The username size must be positive."
        raise ValueError(message)

    return "".join(secrets.choice(USERNAME_ALPHABET) for _ in range(size))


class AutoName(enum.Enum):

    def _generate_next_value_(name, start, count, last_values):  # noqa: N805
        return name.lower()
