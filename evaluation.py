#!/usr/bin/env python3
"""Compute evaluation metrics from LLM judge output."""

import argparse
import json
import sys
from pathlib import Path

import anthropic

MODEL = 'claude-sonnet-4-6'
MAX_TOKENS = 512


def _load_records(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding='utf-8'))


def _summarize_rationales(
    client: anthropic.Anthropic, rationales: list[str]
) -> str:
    """Send rationales to Claude and return a concise summary."""
    numbered = '\n'.join(
        f'{i}. {r}' for i, r in enumerate(rationales, 1)
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system='Summarize the following rationales concisely.',
        messages=[{'role': 'user', 'content': numbered}],
    )
    return next(
        block.text for block in response.content if block.type == 'text'
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Compute metrics from LLM judge output.'
    )
    parser.add_argument('input', help='Path to judgements JSON file')
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Print a summary of rationales for the selected judgement',
    )
    parser.add_argument(
        '--judgement',
        type=str.upper,
        choices=['TRUE', 'FALSE', 'TIE', 'NONE'],
        help='Judgement value to filter when using --summary',
    )
    args = parser.parse_args()

    if args.summary and not args.judgement:
        parser.error('--summary requires --judgement')

    records = _load_records(Path(args.input))
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

    if args.summary:
        rationales = [
            r['Rationale']
            for r in records
            if r.get('Judgement', '').strip().upper() == args.judgement
            and r.get('Rationale')
        ]
        if not rationales:
            print(f'\nNo rationales found for Judgement={args.judgement}')
            return
        client = anthropic.Anthropic()
        print(f'\nSummary of rationales for Judgement={args.judgement}:')
        print(_summarize_rationales(client, rationales))


if __name__ == '__main__':
    main()
