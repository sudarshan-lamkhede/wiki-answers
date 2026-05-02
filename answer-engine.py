#!/usr/bin/env python3
"""Interactive answer engine using Claude Haiku and Wikipedia."""

import importlib.util
import sys
import threading
import time
from pathlib import Path
from typing import Literal

import anthropic
from pydantic import BaseModel

_wiki_spec = importlib.util.spec_from_file_location(
    'wiki_search', Path(__file__).parent / 'wiki-search.py'
)
_wiki_mod = importlib.util.module_from_spec(_wiki_spec)
_wiki_spec.loader.exec_module(_wiki_mod)
search_wikipedia = _wiki_mod.search_wikipedia

MODEL = 'claude-haiku-4-5'
SYSTEM_PROMPT_PATH = Path('system-prompt.md')
CLASSIFICATION_PROMPT_PATH = Path('system-prompt-is-wiki.md')
BRACKET_COLOR = '\033[38;2;185;102;72m'
RESET = '\033[0m'
ERROR_PREFIX = (
    'Unable to retrieve documents and/or generate answer because of the '
    'following error: \n\n'
)
INTRO = (
    "Interactive answer engine based on Claude and Wikipedia. "
    "Strictly single-turn i.e. response will be only based on the current "
    "question and will not consider prior conversation. "
    "Submit '/end' to stop the program."
)
DEFAULT_MESSAGE = (
    'This query is better answered with web search or Claude.ai. '
    'This tool is only for querying Wikipedia using a Claude LLM'
)
MAX_TOOL_CALLS = 3
WIKI_SEARCH_TOOL = {
    'name': 'wiki_search',
    'description': (
        'Search Wikipedia for factual information relevant to the question. '
        'Returns the top 3 matching articles with titles, snippets, URLs, '
        'and extended excerpts from the article text.'
    ),
    'input_schema': {
        'type': 'object',
        'properties': {
            'query': {
                'type': 'string',
                'description': 'The search terms to look up on Wikipedia.',
            },
        },
        'required': ['query'],
    },
}


class Classification(BaseModel):
    intent: Literal['information-seeking', 'other']
    topic: Literal['wiki', 'non-wiki']


def _colored(text: str) -> str:
    return f'{BRACKET_COLOR}{text}{RESET}'


def _prompt(label: str) -> str:
    return f'{_colored("[")}{label}{_colored("] >>> ")}'


def _load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding='utf-8')


def _run_spinner(stop_event: threading.Event) -> None:
    frames = ('|', '/', '-', '\\')
    i = 0
    while not stop_event.is_set():
        print(f'\r{frames[i % len(frames)]}', end='', flush=True)
        i += 1
        time.sleep(0.1)
    print('\r \r', end='', flush=True)


def _format_search_results(results: list) -> str:
    parts = []
    for i, r in enumerate(results, 1):
        parts.append(
            f'{i}. {r.title}\n'
            f'   URL: {r.url}\n'
            f'   Snippet: {r.snippet}\n'
            f'   Article text: {r.extended_snippet}'
        )
    return '\n\n'.join(parts)


def _classify_question(
    client: anthropic.Anthropic, system: str, question: str
) -> Classification:
    response = client.messages.parse(
        model=MODEL,
        max_tokens=64,
        system=system,
        messages=[{'role': 'user', 'content': question}],
        output_format=Classification,
    )
    return response.parsed_output


def _execute_tool(name: str, tool_input: dict) -> str:
    if name == 'wiki_search':
        return _format_search_results(search_wikipedia(tool_input['query']))
    return f'Unknown tool: {name}'


def _call_api(client: anthropic.Anthropic, system: str, question: str) -> str:
    messages: list = [{'role': 'user', 'content': question}]
    tool_calls_used = 0
    while True:
        kwargs: dict = {
            'model': MODEL,
            'max_tokens': 1024,
            'system': system,
            'messages': messages,
        }
        if tool_calls_used < MAX_TOOL_CALLS:
            kwargs['tools'] = [WIKI_SEARCH_TOOL]
        response = client.messages.create(**kwargs)
        if response.stop_reason == 'end_turn':
            return next(
                block.text for block in response.content if block.type == 'text'
            )
        messages.append({'role': 'assistant', 'content': response.content})
        tool_results = []
        for block in response.content:
            if block.type == 'tool_use':
                query = block.input.get('query', '')
                print(f"\rusing wiki-search tool with '{query}'")
                tool_results.append({
                    'type': 'tool_result',
                    'tool_use_id': block.id,
                    'content': _execute_tool(block.name, block.input),
                })
                tool_calls_used += 1
        messages.append({'role': 'user', 'content': tool_results})


def get_answer(client: anthropic.Anthropic, system: str, question: str) -> str:
    """Call the API with one automatic retry on failure."""
    stop_event = threading.Event()
    spinner = threading.Thread(target=_run_spinner, args=(stop_event,))
    spinner.start()

    try:
        for attempt in range(2):
            try:
                return _call_api(client, system, question)
            except Exception:
                if attempt == 1:
                    raise
    finally:
        stop_event.set()
        spinner.join()


def main() -> None:
    try:
        system = _load_system_prompt()
        classification_system = CLASSIFICATION_PROMPT_PATH.read_text(
            encoding='utf-8'
        )
    except OSError as e:
        print(f'{ERROR_PREFIX}{e}')
        sys.exit(1)

    client = anthropic.Anthropic()
    print(INTRO)

    while True:
        try:
            question = input(_prompt('Question'))
        except EOFError:
            break
        if question.strip() == '/end':
            break

        try:
            classification = _classify_question(
                client, classification_system, question
            )
            if (
                classification.intent == 'information-seeking'
                and classification.topic == 'wiki'
            ):
                answer = get_answer(client, system, question)
            else:
                answer = DEFAULT_MESSAGE
            print(f'{_prompt("Answer  ")}{answer}')
        except Exception as e:
            print(f'{ERROR_PREFIX}{e}')
            sys.exit(1)


if __name__ == '__main__':
    main()
