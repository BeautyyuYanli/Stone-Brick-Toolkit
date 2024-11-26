class GeneratedNotValid(Exception):
    """Generated text can't be validated.
    Paired with a validator in `generate_with_validation`.

    No message is needed."""

    pass


class GeneratedEmpty(Exception):
    """Generated text is empty.
    Paired with `oai_generate_with_retry`.

    message is the API response."""

    pass
