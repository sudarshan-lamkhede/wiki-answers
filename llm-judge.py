#!/usr/bin/env python3
"""Evaluate generated answers using Claude Sonnet as an LLM judge."""

import csv
import json
import sys
import time
from pathlib import Path

import anthropic

MODEL = 'claude-sonnet-4-6'
MAX_TOKENS = 512
POLL_INTERVAL = 30
SYSTEM_PROMPT_PATH = Path('llm-judge-system-prompt.md')
JUDGEMENT_SCHEMA = {
    'type': 'object',
    'properties': {
        'Judgement': {'type': 'string'},
        'Rationale': {'type': 'string'},
    },
    'required': ['Judgement', 'Rationale'],
    'additionalProperties': False,
}


def _load_rows(path: Path) -> list[dict]:
    with path.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def _user_message(row: dict) -> str:
    return json.dumps({
        'Question': row['Question'],
        'ProvidedAnswer': row['ProvidedAnswer'],
        'GeneratedAnswer': row['GeneratedAnswer'],
    }, ensure_ascii=False)


def _submit_batch(
    client: anthropic.Anthropic, rows: list[dict], system: str
) -> str:
    """Submit one batch judgement request per row and return the batch ID."""
    requests = [
        {
            'custom_id': f'{row["QuestionID"]}-{i}',
            'params': {
                'model': MODEL,
                'max_tokens': MAX_TOKENS,
                'system': system,
                'output_config': {
                    'format': {
                        'type': 'json_schema',
                        'schema': JUDGEMENT_SCHEMA,
                    },
                },
                'messages': [
                    {'role': 'user', 'content': _user_message(row)},
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
) -> dict[str, dict]:
    """Return a mapping of custom_id to parsed Judgement and Rationale."""
    results: dict[str, dict] = {}
    for result in client.messages.batches.results(batch_id):
        if result.result.type == 'succeeded':
            text = next(
                block.text
                for block in result.result.message.content
                if block.type == 'text'
            )
            results[result.custom_id] = json.loads(text)
        else:
            results[result.custom_id] = {'Judgement': '', 'Rationale': ''}
    return results


def _write_output(
    rows: list[dict], judgements: dict[str, dict], output_path: Path
) -> None:
    """Write evaluation results as a JSON array."""
    records = []
    for i, row in enumerate(rows):
        custom_id = f'{row["QuestionID"]}-{i}'
        j = judgements.get(custom_id, {})
        records.append({
            'Question': row['Question'],
            'ProvidedAnswer': row['ProvidedAnswer'],
            'GeneratedAnswer': row['GeneratedAnswer'],
            'Judgement': j.get('Judgement', ''),
            'Rationale': j.get('Rationale', ''),
        })
    output_path.write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )


def main() -> None:
    if len(sys.argv) != 3:
        print(f'Usage: {sys.argv[0]} <input.tsv> <output.json>')
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

    judgements = _collect_results(client, batch_id)
    succeeded = sum(1 for j in judgements.values() if j.get('Judgement'))
    print(f'Results: {succeeded}/{len(rows)} succeeded')

    _write_output(rows, judgements, output_path)
    print(f'Wrote {len(rows)} records to {output_path}')


if __name__ == '__main__':
    main()
