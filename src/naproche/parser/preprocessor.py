import re

def extract_forthel_blocks(latex_content):
    """
    Extracts the content of 'forthel' environments from a LaTeX file.
    Returns a list of strings, where each string is the content of a forthel block.
    """
    # Regex to capture content between \begin{forthel} and \end{forthel}
    # re.DOTALL makes . match newlines
    pattern = re.compile(r'\\begin\{forthel\}(.*?)\\end\{forthel\}', re.DOTALL)

    matches = pattern.findall(latex_content)

    # Strip whitespace
    return [m.strip() for m in matches]
