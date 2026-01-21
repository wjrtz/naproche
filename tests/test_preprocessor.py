import unittest
from naproche.parser.preprocessor import extract_forthel_blocks, ForthelBlock

class TestPreprocessor(unittest.TestCase):
    def test_single_block(self):
        content = r"""
\documentclass{article}
\begin{document}
\begin{forthel}
Let $x$ be a number.
\end{forthel}
\end{document}
"""
        blocks = extract_forthel_blocks(content)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].content, "Let $x$ be a number.")

        # Verify offset
        # \begin{forthel} is at index 40
        # \begin{forthel} length is 15. So content starts at 55.
        # But there is a newline after \begin{forthel}, so content starts at 56?
        # Let's check regex: r'\\begin\{forthel\}(.*?)\\end\{forthel\}'
        # The content matches "\nLet $x$ be a number.\n"
        # strip() removes leading \n.
        # So effective content is "Let $x$ be a number."
        # Leading whitespace in captured group is "\n". Length 1.
        # start(1) is index of "\nLet...".
        # start_offset should be start(1) + 1.

        start_idx = content.find("Let $x$")
        self.assertEqual(blocks[0].start_offset, start_idx)
        self.assertEqual(blocks[0].end_offset, start_idx + len("Let $x$ be a number."))

    def test_multiple_blocks(self):
        content = r"""
\begin{forthel}
A
\end{forthel}
Text
\begin{forthel}
B
\end{forthel}
"""
        blocks = extract_forthel_blocks(content)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0].content, "A")
        self.assertEqual(blocks[1].content, "B")

        self.assertEqual(blocks[0].start_offset, content.find("A"))
        self.assertEqual(blocks[1].start_offset, content.find("B"))

    def test_indented_block(self):
        content = r"""
    \begin{forthel}
      Let $x$.
    \end{forthel}
"""
        blocks = extract_forthel_blocks(content)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].content, "Let $x$.")

        # Captured group is "\n      Let $x$.\n    "
        # Strip removes "\n      " from start.
        # Leading whitespace len: 1 (\n) + 6 (spaces) = 7.
        # start_offset = start(1) + 7.

        expected_start = content.find("Let $x$.")
        self.assertEqual(blocks[0].start_offset, expected_start)

if __name__ == '__main__':
    unittest.main()
