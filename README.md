# ICMPC and SMPC proceedings parser

## Getting Started

Clone the repository:

    git clone https://github.com/jpmckinney/journals.git

## Convert PDFs to text

Convert the PDFs to text files. The PDFs are not distributed with this repository.

    cd data
    ./pdftotext.sh
    cd ..

## Correct text

`pdftotext` sometimes chokes on diacritics including `˙`, `´` and `ˇ`.

In `ICMPC10_absbook.txt`, correct the text near:

    Sutartin...
    Marek Fran...

In `ICMPC11_ABSTRACTS.txt`, correct the text near:

    Simone Dalla Bella, Jakub Sowi...

## Parse text

Extract the abstracts from the text files:

    python extract_abstracts.py
