from unittest import TestCase

from stone_brick.parser.xml import flat_xml_tags_from_text


class TestXmlParser(TestCase):
    def test_tags_from_text(self):
        text = "<t1>Hello, world!</t1>some<t2>This is a test.</t2>"
        tags = flat_xml_tags_from_text(text, ["t1", "t2"])
        assert tags == [("t1", "Hello, world!"), "some", ("t2", "This is a test.")]
