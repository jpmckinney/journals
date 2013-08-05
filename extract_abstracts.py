# coding: utf-8
#!/usr/bin/env python

import codecs
from dumptruck import DumpTruck
from os.path import basename
import re
from unicodedata import normalize

def clean_title(lines):
  # Make the title one line and remove extra whitespace.
  return " ".join(lines).strip()

clean_authors_regex = re.compile("(\A| )\d(?=[ ,]|\Z)| (?=[,;])")
def clean_authors(lines):
  # Remove extra whitespace and the numbers that match authors to institutions.
  authors = clean_authors_regex.sub("", " ".join(lines)).strip()
  # Remove the authors' institutions, which occur after a semicolon.
  if authors.find(";") >= 0:
    authors, _ = authors.split("; ", 1)
  return authors

# Not a perfect strategy, e.g. if "down" appears at the end of a line before a
#hyphen, it may be part of "downbeat" or "down-ramp". Similarly for "tonal",
# "tonality" and "tonal-harmonic".
hyphen_regex = re.compile("(affiliation|auditory|autism|bowed|centroid|cross|cultural|decision|event|hand|human|infant|long|machine|music|nearness|non|other|pianist|point|pupil|school|second|self|small|song|source|survey|three|unexpected|university|well)-\Z", re.IGNORECASE)
def clean_abstract(lines):
  abstract = ""
  for line in lines:
    # Skip empty lines.
    if line:
      # If the hyphen is for line-wrapping:
      if line.endswith("-") and not hyphen_regex.search(line):
        abstract += line[:-1]
      else:
        abstract += line + " "
  return abstract

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

class ICMPCParser(PDFParser):
  header_regex = re.compile("\AICMPC \d+|ICMPC \d+\Z")
  page_number_regex = re.compile("\A +[0-9]{1,3}\Z")
  author_regex = re.compile("(?<!Origin of Singing);|\\b[A-Z]\.|(?<!Part) \d |(?<! and),[^,]+,(?!.* and\\b)")

class ICMPC10(ICMPCParser):
  def parse(self):
    section_start_regex = re.compile("\A\d[AP]M\d-[ARS]\d{2} ")
    section_end_regex = re.compile("\A(Atrium|Rooms?|Space)\\b")
    abstract_start_regex = re.compile("\A *(K-\d|\d[AP]M\d-[ARS]\d{2}-\d+|SUMMARY-\d+|APSCOM3)\Z")

    # Remove headers, footers and section names. Collapse whitespace around
    # headers and footers to avoid misleading whitespace within an abstract.
    text = self.lines[:]
    section_end_index = None
    top_of_page_index = None
    # Whether a title and authors were seen before a page break.
    in_title_and_authors = False
    # Whether to skip empty lines, notably before the header or footer.
    skip_empty_line = False
    # The line below the current line.
    line_below = None
    for index in xrange(len(text) - 1, -1, -1):
      line = text[index]
      # If the line is non-empty, then we are past the empty lines above the header or footer.
      if line:
        skip_empty_line = False
      if ICMPCParser.page_number_regex.search(line):
        # Skip empty lines before the footer.
        skip_empty_line = True
        del text[index]
      elif ICMPCParser.header_regex.search(line):
        # Skip empty lines before the header.
        skip_empty_line = True
        # If the last thing we saw was the title and authors, leave one empty line.
        if in_title_and_authors:
          del text[index:top_of_page_index]
        # If the last thing we saw was part of an abstract, remove all empty lines.
        else:
          del text[index:top_of_page_index + 1]
      elif section_end_regex.search(line):
        if section_end_index:
          raise Exception("Line %d: No start found for section ending on line %d" % (index, section_end_regex))
        section_end_index = index
      elif section_start_regex.search(line):
        del text[index:section_end_index + 1]
        section_end_index = None
        # A section name is always followed by a blank line.
        top_of_page_index = index
        # A section name is always followed by a title and authors.
        in_title_and_authors = True
        # Behave as if we hit a blank line.
        line_below = ""
        # Override all other logic below.
        continue
      elif line == "Keynotes":
        # Special case section name.
        del text[index]
        top_of_page_index = index
        in_title_and_authors = True
        line_below = ""
        continue
      elif abstract_start_regex.search(line):
        in_title_and_authors = True
      elif not line:
        # Skip empty lines before the footer.
        if skip_empty_line:
          del text[index]
        # Used if the next thing we hit is the header.
        elif line_below:
          top_of_page_index = index
      # If the line is non-empty and the last line was empty, then we're out of
      # the title and authors (assuming titles and authors don't span pages).
      if line and not line_below:
        in_title_and_authors = False
      line_below = line

    abstracts = []
    appending = "title"
    title = []
    authors = []
    abstract = []
    semicolon = False

    for index, line in enumerate(text):
      if not line:
        appending = "title"
        if title and authors and abstract:
          abstracts.append({
            "Title": clean_title(title),
            "Authors": clean_authors(authors),
            "Abstract": clean_abstract(abstract),
            "Place": "ICMPC",
            "Year": 2008,
          })
        elif title or authors or abstract:
          raise Exception("Line %d: Incomplete record\n\nTitle: %s\n\nAuthors: %s\n\nAbstract: %s" % (title, authors, abstract))
        title = []
        authors = []
        abstract = []
        continue # Skip empty lines.
      elif appending == "title":
        if ICMPCParser.author_regex.search(line):
          appending = "authors"
          semicolon = line.find(";") >= 0
      elif appending == "authors":
        if abstract_start_regex.search(line):
          appending = "abstract"
          continue # Skip the marker.
        elif not semicolon and line.find(";") == -1 and re.search("(\A| )and ", line):
          # We were mislead by commas. The "and" means we are still in the title.
          appending = "title"
          title += authors
          authors = []

      if appending == "title":
        title.append(line)
      elif appending == "authors":
        authors.append(line)
      else:
        abstract.append(line)

    return abstracts

class ICMPC11(ICMPCParser):
  def parse(self):
    pages = []
    page = []
    text = []

    # Group the lines into pages.
    for line in self.lines:
      # Skip empty lines.
      if line:
        # Skip header lines.
        if ICMPCParser.header_regex.search(line):
          if page: # Page 97 has no page number.
            # Add the page.
            pages.append(page)
            page = []
        # Skip page number lines.
        elif ICMPCParser.page_number_regex.search(line):
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
    for i in xrange(len(abstract_indices)):
      # Remove empty lines from the title and authors.
      title_and_authors = [line for line in text[document_indices[i]:abstract_indices[i] - 1] if line]

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
        elif ICMPCParser.author_regex.search(line):
          appending = "authors"
        if appending == "title":
          title.append(line)
        else:
          authors.append(line)

      abstracts.append({
        "Title": clean_title(title),
        "Authors": clean_authors(authors),
        "Abstract": clean_abstract(text[abstract_indices[i]:document_indices[i + 1]]),
        "Place": "ICMPC",
        "Year": 2010,
      })

    return abstracts

dt = DumpTruck(dbname="icmpc.db")
abstracts = ICMPC11("data/ICMPC11_ABSTRACTS.txt").parse()
dt.insert(abstracts)
abstracts = ICMPC10("data/ICMPC10_absbook.txt").parse()
dt.insert(abstracts)

# SMPC2011-program.pdf
# need to correct whitespace

# icmpc-escom2012_book_of_abstracts.pdf
# Work with docs version
