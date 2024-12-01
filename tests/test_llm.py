import os
from typing import cast
from unittest import IsolatedAsyncioTestCase

from openai import AsyncOpenAI

from stone_brick.llm.utils import (
    generate_with_validation,
    oai_gen_with_retry_then_validate,
    oai_generate_with_retry,
)


class TestLlmUtils(IsolatedAsyncioTestCase):
    def setUp(self):
        self.oai_client = AsyncOpenAI()
        self.model = os.environ["TEST_OPENAI_MODEL"]

    async def test_generate_with_validation(self):
        async def generator():
            return "Hello"

        def validator1(text):
            return cast(str, text) == "Hello"

        def validator2(text):
            return cast(str, text) == "world!"

        validated = await generate_with_validation(generator, validator1)
        assert validated
        validated = await generate_with_validation(generator, validator2)
        assert not validated

    async def test_oai_generate_with_retry(self):
        text = await oai_generate_with_retry(
            oai_client=self.oai_client,
            model=self.model,
            prompt=[{"role": "user", "content": "Hello, world!"}],
            generate_kwargs={
                "temperature": 0.2,
            },
        )
        assert len(text) > 0

    async def test_oai_gen_with_retry_then_validate(self):
        text = await oai_gen_with_retry_then_validate(
            oai_client=self.oai_client,
            model=self.model,
            prompt=[{"role": "user", "content": "Hello, world!"}],
            validator=lambda text: text,
        )
        assert len(text) > 0
