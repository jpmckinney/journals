#!/bin/sh
pdftotext -layout -f 9 -l 142 ICMPC10_absbook.pdf
# If not using -layout, the columns switch back and forth.
pdftotext -layout -f 4 -l 90 ICMPC11_ABSTRACTS.pdf
pdftotext -layout -f 5 -l 91 SMPC2009_programWithAbstract.pdf
pdftotext -layout -f 7 -l 105 SMPC2011-program.pdf
pdftotext -layout -f 15 -l 154 SMPC-2013_conference-program.pdf
