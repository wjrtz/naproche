import unittest
import sys
import os
from naproche.parser.cnl_parser import parse_cnl
from naproche.logic.translator import Translator
from naproche.logic.models import Sentence

class TestNaproche(unittest.TestCase):
    def test_parser(self):
        text = "Let $X$ be a set."
        parsed = parse_cnl(text)
        self.assertIsInstance(parsed, list)
        self.assertTrue(len(parsed) > 0)
        self.assertEqual(parsed[0]['type'], 'sentence')

    def test_translator(self):
        t = Translator()
        s = Sentence(text="Let $X$ be a set", atoms=["Let", "$X$", "be", "a", "set"])
        f = t.translate_sentence(s)
        self.assertEqual(str(f), "set(X)")

if __name__ == '__main__':
    unittest.main()
