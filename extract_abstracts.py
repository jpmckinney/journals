#!/usr/bin/env python

import codecs
from os.path import basename
from unicodedata import normalize

class PDFParser:
  table = {
    ord(u"\u2019"): ord(u"'"),
    ord(u"\u2018"): ord(u"'"),
    ord(u"\u201c"): ord(u'"'),
    ord(u"\u201d"): ord(u'"'),
  }

  def __init__(self, filepath):
    self.filename = basename(filepath)
    # Transform ligatures and curly quotes.
    self.text = normalize("NFKD", codecs.open(filepath, encoding="utf-8").read()).translate(PDFParser.table)

  def parse(self):
    raise NotImplementedError

class ICMPC2011(PDFParser):
  def parse(self):
    

# SMPC2011-program.pdf
# need to correct whitespace

# icmpc-escom2012_book_of_abstracts.pdf
# Work with docs version
