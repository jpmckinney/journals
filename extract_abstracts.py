# coding: utf-8
#!/usr/bin/env python

import codecs
from dumptruck import DumpTruck
from os.path import basename
import re
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
    self.lines = normalize("NFKD", codecs.open(filepath, encoding="utf-8").read()).translate(PDFParser.table).splitlines()

  def parse(self):
    raise NotImplementedError

class ICMPC2011(PDFParser):
  def parse(self):
    pages = []
    page = []
    text = []

    # Group the lines into pages.
    header_regex = re.compile("\AICMPC 11 +(Poster Session [1-3] +)?(Mon|Tues|Wednes|Thurs|Fri)day 2[3-7] Aug 2010\Z")
    page_number_regex = re.compile("\A +[0-9]{2,3}\Z")
    for line in self.lines:
      # Skip empty lines.
      if line:
        # Skip header lines.
        if header_regex.search(line):
          if page: # Page 97 has no page number.
            # Add the page.
            pages.append(page)
            page = []
        # Skip page number lines.
        elif page_number_regex.search(line):
          # Add the page.
          pages.append(page)
          page = []
        else:
          # Append the line to the page.
          page.append(line)

    # Transform the text of each page into a single column.
    column_divider_regex = re.compile("(?<=   )\S")
    for page in pages:
      # Find the index for the start of the second column.
      index = 200 # The longest line is 150.
      for line in page:
        match = column_divider_regex.search(line, 70) # False indices occur up to 68. True indices first appear at 72.
        if match:
          start = match.start(0)
          if start < index:
            index = start

      column1 = []
      column2 = []
      for line in page:
        column1.append(line[:index].strip())
        column2.append(line[index:].strip())
      text.extend(column1)
      text.extend(column2)

    # Loop through the lines backwards to remove section headers.
    end_index = None
    for index in xrange(len(text) - 1, -1, -1):
      line = text[index]
      # Find the end of a section header.
      if re.search(" Aug 2010\Z", line):
        if end_index:
          raise Exception("No section start index found for end index %d: %s" % (end_index, "\n".join(text[index:end_index + 1])))
        end_index = index
      # Remove the section header.
      elif end_index and (index == 0 or line.endswith(".")):
        # If the first line weren't empty, we'd have to adjust the start of the range when index == 0.
        del text[index + 1:end_index + 1]
        end_index = None

    # Loop through the lines backwards to find abstracts.
    document_indices = []
    abstract_indices = []
    end_index = None
    for index in xrange(len(text) - 1, -1, -1):
      line = text[index]
      # Find the end of the title and authors and the start of the abstract.
      if re.search(" Time: [0-9]{2}:[0-9]{2}\Z|, Poster( +CANCELLED)?\Z|, Introduction\Z", line):
        if end_index:
          # Cancelled events have no abstract.
          document_indices.insert(0, index + 1)
        # Don't include the line with the time.
        abstract_indices.insert(0, index + 1)
        end_index = index
      # Find the start of the title and authors.
      elif end_index and (index == 0 or re.search('(?<![ .][A-Z])\."?\Z|\(SSHRC\)\Z|\Ahttp:\/\/\S+\Z', line)):
        # If the first line weren't empty, we'd have to adjust the start of the range when index == 0.
        document_indices.insert(0, index + 1)
        end_index = None

    # The last abstract ends on the last line.
    document_indices.append(len(text))

    # Collect the abstracts.
    abstracts = []
    author_regex = re.compile(";|\b[A-Z]\.|(?<!Part) \d |(?<! and),[^,]+,(?! and)")
    hyphen_regex = re.compile("(affiliation|auditory|bowed|centroid|cross|cultural|decision|event|hand|human|infant|long|machine|music|nearness|non|other|pianist|point|pupil|school|second|self|small|song|source|survey|three|unexpected|university|well)-\Z", re.IGNORECASE)
    for i in xrange(len(abstract_indices)):
      # Remove empty lines from the title and authors.
      title_and_authors = [line for line in text[document_indices[i]:abstract_indices[i] - 1] if line]

      # Special case. Jakub Sowiński's last name is split onto two lines.
      index = next((index for index, line in enumerate(title_and_authors) if re.search(u" ́\Z", line)), None)
      if index:
        title_and_authors[index] = title_and_authors[index][:-2] + title_and_authors[index + 1]
        del title_and_authors[index + 1]

      # @note We can't use line length as a criteria, because the shortest first
      # line of a multiline title is 33 characters ("Are Bodily Responses
      # Pre-Musical?"), and the longest one-line titles are 53 characters
      # ("Diatonic Categorization in the Perception of Melodies" and "Sonata
      # Analgesica: Pain, Music and the Placebo Effect").

      title = []
      authors = []

      # The author line will have a semicolon, an initial, a single digit, or commas without the word "and".
      appending = "title"
      for line in title_and_authors:
        if re.search("(\A| )and ", line) and appending == "authors":
          # We were mislead by commas. The "and" means we are still in the title.
          appending = "title"
          title += authors
          authors = []
        elif author_regex.search(line):
          appending = "authors"
        if appending == "title":
          title.append(line)
        else:
          authors.append(line)

      # Make the title one line and remove extra whitespace.
      title = " ".join(title).strip()
      # Remove extra whitespace and the numbers that match authors to institutions.
      authors = re.sub("(\A| )\d(?=[ ,]|\Z)| (?=[,;])", "", " ".join(authors)).strip()
      # Remove the authors' institutions, which occur after a semicolon.
      if authors.find(";") >= 0:
        authors, _ = authors.split("; ", 1)

      # Not a perfect strategy, e.g. if "down" appears at the end of a line
      # before a hyphen, it may be part of "downbeat" or "down-ramp". Similarly
      # for "tonal", "tonality" and "tonal-harmonic".
      abstract = ""
      for line in text[abstract_indices[i]:document_indices[i + 1]]:
        # Skip empty lines.
        if line:
          # If the hyphen is for line-wrapping:
          if line.endswith("-") and not hyphen_regex.search(line):
            abstract += line[:-1]
          else:
            abstract += line + " "

      abstracts.append({
        "Title": title,
        "Authors": authors,
        "Abstract": abstract,
        "Place": "ICMPC",
        "Year": 2010,
      })

    return abstracts

dt = DumpTruck(dbname="icmpc.db")

abstracts = ICMPC2011("data/ICMPC11_ABSTRACTS.txt").parse()

dt.insert(abstracts)

# Next, ICMPC 2010

# SMPC2011-program.pdf
# need to correct whitespace

# icmpc-escom2012_book_of_abstracts.pdf
# Work with docs version
