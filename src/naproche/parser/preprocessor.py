import re


class ForthelBlock:
    def __init__(self, content, start_offset, end_offset):
        self.content = content
        self.start_offset = start_offset
        self.end_offset = end_offset

    def __repr__(self):
        return f"ForthelBlock(start={self.start_offset}, end={self.end_offset})"


def extract_forthel_blocks(latex_content):
    """
    Extracts the content of 'forthel' environments from a LaTeX file.
    Returns a list of ForthelBlock objects.
    """
    # Regex to capture content between \begin{forthel} and \end{forthel}
    # re.DOTALL makes . match newlines
    pattern = re.compile(r"\\begin\{forthel\}(.*?)\\end\{forthel\}", re.DOTALL)

    matches = pattern.finditer(latex_content)
    blocks = []

    for m in matches:
        full_content = m.group(1)
        stripped_content = full_content.strip()

        if not stripped_content:
            continue

        # Calculate offset adjustment for leading whitespace
        leading_whitespace_len = len(full_content) - len(full_content.lstrip())

        start_offset = m.start(1) + leading_whitespace_len
        end_offset = start_offset + len(stripped_content)

        blocks.append(ForthelBlock(stripped_content, start_offset, end_offset))

    return blocks
