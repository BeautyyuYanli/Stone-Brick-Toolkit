from logging import getLogger
from typing import Any, Callable, Dict, Iterable, Optional, TypeVar

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from stone_brick.llm.error import GeneratedEmpty, GeneratedNotValid

logger = getLogger(__name__)

T = TypeVar("T")

MAX_API_ATTEMPTS = 5
RETRY_API_WAIT_EXP_MULTIPLIER = 1
RETRY_API_WAIT_EXP_MAX = 60
MAX_VALIDATE_ATTEMPTS = 3


def generate_with_validation(
    generator: Callable[[], str],
    validator: Callable[[str], T],
    max_validate_attempts: int = MAX_VALIDATE_ATTEMPTS,
) -> T:
    """
    Call the generator until the validator returns a valid result.

    The validator should raise a GeneratedNotValid exception if the result is not valid.

    Args:
        max_validate_attempts: Maximum number of attempts to validate the text.
    """

    @retry(
        stop=stop_after_attempt(max_validate_attempts),
        retry=retry_if_exception_type(GeneratedNotValid),
    )
    def _generate_with_validation() -> T:
        text = generator()

        try:
            return validator(text)
        except GeneratedNotValid:
            logger.info("Generated text can't be validated: %s", text)
            raise

    return _generate_with_validation()


def oai_generate_with_retry(
    oai_client: OpenAI,
    model: str,
    prompt: Iterable[ChatCompletionMessageParam],
    generate_kwargs: Optional[Dict[str, Any]] = None,
    *,
    max_attempts: int = MAX_API_ATTEMPTS,
    wait_exponential_multiplier: int = RETRY_API_WAIT_EXP_MULTIPLIER,
    wait_exponential_max: int = RETRY_API_WAIT_EXP_MAX,
) -> str:
    """Call the OpenAI API until the response is valid.

    Args:
        max_attempts: Maximum number of attempts to call the API.
        wait_exponential_multiplier: Multiplier for the exponential backoff.
        wait_exponential_max: Maximum wait time in seconds.
    """

    generate_kwargs = generate_kwargs or {}

    @retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(
            multiplier=wait_exponential_multiplier, max=wait_exponential_max
        ),
    )
    def _oai_generate_with_retry() -> str:
        try:
            response = oai_client.chat.completions.create(
                model=model,
                messages=prompt,
                stream=False,
                **generate_kwargs,
            )
            if response.choices[0].message.content is None:
                raise GeneratedEmpty(str(response))
            else:
                return response.choices[0].message.content
        except GeneratedEmpty:
            logger.warning("Generated empty text response", exc_info=True)
            raise
        except Exception:
            logger.warning("OpenAI API call failed", exc_info=True)
            raise

    return _oai_generate_with_retry()


def oai_gen_with_retry_then_validate(
    validator: Callable[[str], T],
    oai_client: OpenAI,
    model: str,
    prompt: Iterable[ChatCompletionMessageParam],
    generate_kwargs: Optional[Dict[str, Any]] = None,
    *,
    max_api_attempts: int = MAX_API_ATTEMPTS,
    retry_api_wait_exp_multiplier: int = RETRY_API_WAIT_EXP_MULTIPLIER,
    retry_api_wait_exp_max: int = RETRY_API_WAIT_EXP_MAX,
    max_validate_attempts: int = MAX_VALIDATE_ATTEMPTS,
) -> T:
    """Call the OpenAI API until the response is valid, and use the validator to validate it.

    It will use max_attempts to call the API to get a response,
    and max_validate_attempts to validate the text.
    That means at most max_attempts * max_validate_attempts API calls will be made.

    Args:
        max_api_attempts: Maximum number of attempts to call the API.
        retry_api_wait_exp_multiplier: Multiplier for the exponential backoff.
        retry_api_wait_exp_max: Maximum wait time in seconds.
        max_validate_attempts: Maximum number of attempts to validate the text.
    """

    return generate_with_validation(
        lambda: oai_generate_with_retry(
            oai_client,
            model,
            prompt,
            generate_kwargs,
            max_attempts=max_api_attempts,
            wait_exponential_multiplier=retry_api_wait_exp_multiplier,
            wait_exponential_max=retry_api_wait_exp_max,
        ),
        validator,
        max_validate_attempts=max_validate_attempts,
    )
