#!/usr/bin/env python3
"""Extract positive-label rows from a WikiQA TSV file."""

import csv
import sys
from pathlib import Path

KEEP_COLUMNS = ('QuestionID', 'Question', 'Sentence')
OUTPUT_COLUMNS = ('QuestionID', 'Question', 'ProvidedAnswer')
LABEL_COLUMN = 'Label'
POSITIVE_LABEL = '1'


def extract_positives(input_path: Path, output_path: Path) -> int:
    """Write rows where Label==1 with only the kept columns; return row count."""
    with (
        input_path.open(encoding='utf-8', newline='') as infile,
        output_path.open('w', encoding='utf-8', newline='') as outfile,
    ):
        reader = csv.DictReader(infile, delimiter='\t')
        writer = csv.DictWriter(
            outfile,
            fieldnames=KEEP_COLUMNS,
            delimiter='\t',
            extrasaction='ignore',
        )
        writer.writeheader()
        count = 0
        for row in reader:
            if row[LABEL_COLUMN] == POSITIVE_LABEL:
                writer.writerow({col: row[col] for col in KEEP_COLUMNS})
                count += 1
    return count


def main() -> None:
    if len(sys.argv) != 3:
        print(f'Usage: {sys.argv[0]} <input.tsv> <output.tsv>')
        sys.exit(1)
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    count = extract_positives(input_path, output_path)
    print(f'Wrote {count} positive rows to {output_path}')


if __name__ == '__main__':
    main()
