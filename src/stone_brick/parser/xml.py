import re
from typing import List, Tuple, Union


def flat_xml_tags_from_text(
    text: str, tags: list[str]
) -> List[Union[Tuple[str, str], str]]:
    """Support extract tags from text, without nested

    Ouput would be like: ["some text", ("Tag1", "content"), "some text", ("Tag2", "content2")]
    """
    last_end = 0
    parts = []
    combined_pattern = "|".join(f"(<{tag}>(.*?)</{tag}>)" for tag in tags)
    # Process all matches in a single pass
    for match in re.finditer(combined_pattern, text, re.DOTALL):
        if match.start() > last_end:
            # Add normal text before the match
            normal_text = text[last_end : match.start()]
            if normal_text:
                parts.append(normal_text)

        # Find which group matched (which tag)
        matched_groups = [
            (i, g) for i, g in enumerate(match.groups()[1::2]) if g is not None
        ]
        if matched_groups:
            group_index, matched_text = matched_groups[0]
            tag = tags[group_index]
            parts.append((tag, matched_text))

        last_end = match.end()

    # Add any remaining normal text
    if last_end < len(text):
        normal_text = text[last_end:]
        if normal_text:
            parts.append(normal_text)
    return parts
