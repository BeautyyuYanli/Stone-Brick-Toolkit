from logging import getLogger
from typing import Any, Awaitable, Callable, Dict, Iterable, Optional, TypeVar

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from tenacity import (
    retry,
    retry_if_exception,
    retry_if_exception_type,
    wait_exponential,
)

from stone_brick.llm.error import GeneratedEmpty, GeneratedNotValid
from stone_brick.retry import stop_after_attempt_may_inf

logger = getLogger(__name__)
T = TypeVar("T")


MAX_API_ATTEMPTS = 6
MAX_EMPTY_TEXT_ATTEMPTS = 2
MAX_VALIDATE_ATTEMPTS = 3


async def generate_with_validation(
    generator: Callable[[], Awaitable[str]],
    validator: Callable[[str], T],
    max_validate_attempts: int = MAX_VALIDATE_ATTEMPTS,
) -> T:
    """
    Call the generator until the validator returns a valid result.

    The validator should raise a GeneratedNotValid exception if the result is not valid.

    Args:
        max_validate_attempts: Maximum number of attempts to validate the text. If it
            is -1, the validation will be retried indefinitely.
    """

    @retry(
        stop=stop_after_attempt_may_inf(max_validate_attempts),
        retry=retry_if_exception_type(GeneratedNotValid),
    )
    async def _generate_with_validation() -> T:
        text = await generator()

        try:
            return validator(text)
        except Exception as e:
            logger.warning("Generated text can't be validated: %s", text)
            raise GeneratedNotValid("Generated text can't be validated: ", text) from e

    return await _generate_with_validation()


async def oai_generate_with_retry(
    oai_client: AsyncOpenAI,
    model: str,
    prompt: Iterable[ChatCompletionMessageParam],
    generate_kwargs: Optional[Dict[str, Any]] = None,
    *,
    max_api_attempts: int = MAX_API_ATTEMPTS,
    max_empty_attempts: int = MAX_EMPTY_TEXT_ATTEMPTS,
) -> str:
    """Call the OpenAI API to generate text.

    Args:
        max_api_attempts: Maximum number of attempts to call the API, with exponential
            backoff. If it is -1, the API will be called indefinitely.
        max_empty_attempts: Maximum number of attempts to call the API if the generated
            text is empty. If it is -1, the API will be called indefinitely.
    """

    generate_kwargs = generate_kwargs or {}

    @retry(
        stop=stop_after_attempt_may_inf(max_empty_attempts),
        retry=retry_if_exception_type(GeneratedEmpty),
    )
    @retry(
        stop=stop_after_attempt_may_inf(max_api_attempts),
        wait=wait_exponential(max=60),
        retry=retry_if_exception(lambda exc: not isinstance(exc, GeneratedEmpty)),
    )
    async def _oai_generate_with_retry() -> str:
        try:
            response = await oai_client.chat.completions.create(
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

    return await _oai_generate_with_retry()


async def oai_gen_with_retry_then_validate(
    validator: Callable[[str], T],
    oai_client: AsyncOpenAI,
    model: str,
    prompt: Iterable[ChatCompletionMessageParam],
    generate_kwargs: Optional[Dict[str, Any]] = None,
    *,
    max_api_attempts: int = MAX_API_ATTEMPTS,
    max_empty_attempts: int = MAX_EMPTY_TEXT_ATTEMPTS,
    max_validate_attempts: int = MAX_VALIDATE_ATTEMPTS,
) -> T:
    """Call the OpenAI API until the response is valid, and use the validator to validate it.

    It will use max_attempts to call the API to get a response,
    and max_validate_attempts to validate the text.
    That means at most max_attempts * max_validate_attempts API calls will be made.

    Args:
        max_api_attempts: Maximum number of attempts to call the API, with exponential
            backoff. -1 means infinite.
        max_empty_attempts: Maximum number of attempts to call the API if the generated
            text is empty. -1 means infinite.
        max_validate_attempts: Maximum number of attempts to validate the text. -1
            means infinite.
    """

    return await generate_with_validation(
        lambda: oai_generate_with_retry(
            oai_client,
            model,
            prompt,
            generate_kwargs,
            max_api_attempts=max_api_attempts,
            max_empty_attempts=max_empty_attempts,
        ),
        validator,
        max_validate_attempts=max_validate_attempts,
    )
