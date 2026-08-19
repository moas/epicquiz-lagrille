import enum  # noqa: I001


class AutoName(enum.Enum):

    def _generate_next_value_(name, start, count, last_values):
        return name.lower()
