from typing import cast
from unittest import TestCase

from openai import OpenAI

from stone_brick.llm.utils import generate_with_validation, oai_generate_with_retry


class TestLlmUtils(TestCase):
    def setUp(self):
        self.oai_client = OpenAI()

    def test_generate_with_validation(self):
        def generator():
            return "Hello"

        def validator1(text):
            return cast(str, text) == "Hello"

        def validator2(text):
            return cast(str, text) == "world!"

        validated = generate_with_validation(generator, validator1)
        assert validated
        validated = generate_with_validation(generator, validator2)
        assert not validated

    def test_oai_generate_with_retry(self):
        text = oai_generate_with_retry(
            oai_client=self.oai_client,
            model="gpt-4o",
            prompt=[{"role": "user", "content": "Hello, world!"}],
            generate_kwargs={
                "temperature": 0.2,
            },
        )
        assert len(text) > 0
