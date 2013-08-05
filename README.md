# ICMPC and SMPC proceedings parser

Convert the PDFs to text files:

    cd data
    ./pdftotext.sh
    cd ..

In `ICMPC10_absbook.txt`, correct the words that are broken onto two lines:

    Psychoacoustical and Cognitive Basis of Sutartin...
    Marek Fran...

Extract the abstracts from the text files:

    python extract_abstracts.py
