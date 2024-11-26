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


def generate_with_validation(
    generator: Callable[[], str],
    validator: Callable[[str], T],
    max_validate_attempts: int = 3,
) -> T:
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
    max_attempts: int = 5,
    wait_exponential_multiplier: int = 1,
    wait_exponential_max: int = 60,
) -> str:
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
