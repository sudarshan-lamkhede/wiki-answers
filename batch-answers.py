#!/usr/bin/env python3
"""Generate answers for WikiQA questions using answer_question."""

import csv
import importlib.util
import sys
import time
from pathlib import Path

import anthropic

_spec = importlib.util.spec_from_file_location(
    'answer_engine', Path(__file__).parent / 'answer-engine.py'
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
answer_question = _mod.answer_question
Stats = _mod.Stats

SYSTEM_PROMPT_PATH = Path('system-prompt.md')
CLASSIFICATION_PROMPT_PATH = Path('system-prompt-is-wiki.md')
OUTPUT_COLUMNS = ('QuestionID', 'Question', 'Sentence', 'GeneratedAnswer')


def _load_rows(path: Path) -> list[dict]:
    with path.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def _write_output(
    rows: list[dict], answers: list[str], output_path: Path
) -> None:
    """Write rows augmented with GeneratedAnswer to a TSV file."""
    with output_path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(
            f, fieldnames=OUTPUT_COLUMNS, delimiter='\t'
        )
        writer.writeheader()
        for row, answer in zip(rows, answers):
            writer.writerow({
                'QuestionID': row['QuestionID'],
                'Question': row['Question'],
                'Sentence': row['Sentence'],
                'GeneratedAnswer': answer,
            })


def main() -> None:
    if len(sys.argv) != 3:
        print(f'Usage: {sys.argv[0]} <input.tsv> <output.tsv>')
        sys.exit(1)
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    try:
        system = SYSTEM_PROMPT_PATH.read_text(encoding='utf-8')
        classification_system = CLASSIFICATION_PROMPT_PATH.read_text(
            encoding='utf-8'
        )
    except OSError as e:
        print(f'Error reading system prompt: {e}')
        sys.exit(1)

    client = anthropic.Anthropic()
    stats = Stats()

    rows = _load_rows(input_path)
    print(f'Loaded {len(rows)} rows from {input_path}')

    answers = []
    for i, row in enumerate(rows, 1):
        print(f'[{i}/{len(rows)}] {row["Question"]}')
        answers.append(answer_question(
            client, classification_system, system, row['Question'], stats
        ))
        # time.sleep(2)

    _write_output(rows, answers, output_path)
    print(f'Wrote {len(rows)} rows to {output_path}')


if __name__ == '__main__':
    main()
