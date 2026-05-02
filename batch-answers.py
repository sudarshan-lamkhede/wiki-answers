#!/usr/bin/env python3
"""Generate answers for WikiQA questions via the Anthropic batch messages API."""

import csv
import sys
import time
from pathlib import Path

import anthropic

MODEL = 'claude-haiku-4-5'
MAX_TOKENS = 256
POLL_INTERVAL = 30
OUTPUT_COLUMNS = ('QuestionID', 'Question', 'Sentence', 'GeneratedAnswer')
SYSTEM_PROMPT_PATH = Path('system-prompt.md')


def _load_rows(path: Path) -> list[dict]:
    with path.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def _user_message(question: str, sentence: str) -> str:
    return f'Sentence: {sentence}\n\nQuestion: {question}'


def _submit_batch(
    client: anthropic.Anthropic, rows: list[dict], system: str
) -> str:
    """Submit one batch request per row and return the batch ID."""
    requests = [
        {
            'custom_id': f'{row["QuestionID"]}-{i}',
            'params': {
                'model': MODEL,
                'max_tokens': MAX_TOKENS,
                'system': system,
                'messages': [
                    {
                        'role': 'user',
                        'content': row['Question']
                    }
                ],
            },
        }
        for i, row in enumerate(rows)
    ]
    batch = client.messages.batches.create(requests=requests)
    return batch.id


def _poll_until_done(client: anthropic.Anthropic, batch_id: str) -> None:
    """Block until the batch processing_status reaches 'ended'."""
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        counts = batch.request_counts
        print(
            f'\r  processing={counts.processing}'
            f'  succeeded={counts.succeeded}'
            f'  errored={counts.errored}',
            end='',
            flush=True,
        )
        if batch.processing_status == 'ended':
            print()
            return
        time.sleep(POLL_INTERVAL)


def _collect_results(
    client: anthropic.Anthropic, batch_id: str
) -> dict[str, str]:
    """Return a mapping of custom_id to generated answer text."""
    answers: dict[str, str] = {}
    for result in client.messages.batches.results(batch_id):
        if result.result.type == 'succeeded':
            text = next(
                block.text
                for block in result.result.message.content
                if block.type == 'text'
            )
            answers[result.custom_id] = text
        else:
            answers[result.custom_id] = ''
    return answers


def _write_output(
    rows: list[dict], answers: dict[str, str], output_path: Path
) -> None:
    """Write rows augmented with GeneratedAnswer to a TSV file."""
    with output_path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(
            f, fieldnames=OUTPUT_COLUMNS, delimiter='\t'
        )
        writer.writeheader()
        for i, row in enumerate(rows):
            custom_id = f'{row["QuestionID"]}-{i}'
            writer.writerow({
                'QuestionID': row['QuestionID'],
                'Question': row['Question'],
                'Sentence': row['Sentence'],
                'GeneratedAnswer': answers.get(custom_id, ''),
            })


def main() -> None:
    if len(sys.argv) != 3:
        print(f'Usage: {sys.argv[0]} <input.tsv> <output.tsv>')
        sys.exit(1)
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    try:
        system = SYSTEM_PROMPT_PATH.read_text(encoding='utf-8')
    except OSError as e:
        print(f'Error reading system prompt: {e}')
        sys.exit(1)

    client = anthropic.Anthropic()

    rows = _load_rows(input_path)
    print(f'Loaded {len(rows)} rows from {input_path}')

    batch_id = _submit_batch(client, rows, system)
    print(f'Batch submitted: {batch_id}')

    print('Polling for completion (every 30 s)...')
    _poll_until_done(client, batch_id)

    answers = _collect_results(client, batch_id)
    succeeded = sum(1 for v in answers.values() if v)
    print(f'Results: {succeeded}/{len(rows)} succeeded')

    _write_output(rows, answers, output_path)
    print(f'Wrote {len(rows)} rows to {output_path}')


if __name__ == '__main__':
    main()
