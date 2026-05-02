#!/usr/bin/env python3
"""Compute evaluation metrics from LLM judge output."""

import json
import sys
from pathlib import Path


def _load_records(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding='utf-8'))


def main() -> None:
    if len(sys.argv) != 2:
        print(f'Usage: {sys.argv[0]} <judgements.json>')
        sys.exit(1)

    records = _load_records(Path(sys.argv[1]))
    total = len(records)
    if total == 0:
        print('No records found.')
        sys.exit(0)

    counts = {'TRUE': 0, 'FALSE': 0, 'TIE': 0, 'NONE': 0}
    for record in records:
        key = record.get('Judgement', '').strip().upper()
        if key in counts:
            counts[key] += 1

    print(
        f'Total records              : {total}\n'
        f'GeneratedAnswerPreferred   : {counts["TRUE"] / total:.2%}'
        f'  ({counts["TRUE"]})\n'
        f'ProvidedAnswersPreferred   : {counts["FALSE"] / total:.2%}'
        f'  ({counts["FALSE"]})\n'
        f'Tie                        : {counts["TIE"] / total:.2%}'
        f'  ({counts["TIE"]})\n'
        f'Neither                    : {counts["NONE"] / total:.2%}'
        f'  ({counts["NONE"]})'
    )


if __name__ == '__main__':
    main()
