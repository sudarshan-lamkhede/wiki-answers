#!/usr/bin/env python3
"""Interactive answer engine using Claude Haiku and Wikipedia."""

import argparse
import importlib.util
import json
import sys
import termios
import threading
import time
import tty
from dataclasses import dataclass, field
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
TEMPERATURE = 0.0
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


@dataclass
class Stats:
    tool_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    ttft_ms: list[float] = field(default_factory=list)


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


def _debug(label: str, data: dict) -> None:
    print(f'\n=== {label} ===')
    print(json.dumps(data, indent=2, default=str))


def _classify_question(
    client: anthropic.Anthropic,
    system: str,
    question: str,
    stats: Stats,
    debug: bool = False,
) -> Classification:
    if debug:
        _debug('CLASSIFY REQUEST', {
            'model': MODEL,
            'max_tokens': 64,
            'temperature': TEMPERATURE,
            'system': system,
            'messages': [{'role': 'user', 'content': question}],
            'output_format': 'Classification',
        })
    start = time.perf_counter()
    response = client.messages.parse(
        model=MODEL,
        max_tokens=64,
        temperature=TEMPERATURE,
        system=system,
        messages=[{'role': 'user', 'content': question}],
        output_format=Classification,
    )
    stats.ttft_ms.append((time.perf_counter() - start) * 1000)
    stats.input_tokens += response.usage.input_tokens
    stats.output_tokens += response.usage.output_tokens
    if debug:
        _debug('CLASSIFY RESPONSE', response.model_dump())
    return response.parsed_output


def _execute_tool(name: str, tool_input: dict) -> str:
    if name == 'wiki_search':
        return _format_search_results(search_wikipedia(tool_input['query']))
    return f'Unknown tool: {name}'


def _call_api(
    client: anthropic.Anthropic, system: str, question: str, stats: Stats,
    debug: bool = False,
) -> str:
    messages: list = [{'role': 'user', 'content': question}]
    tool_calls_used = 0
    while True:
        kwargs: dict = {
            'model': MODEL,
            'max_tokens': 1024,
            'temperature': TEMPERATURE,
            'system': system,
            'messages': messages,
        }
        if tool_calls_used < MAX_TOOL_CALLS:
            kwargs['tools'] = [WIKI_SEARCH_TOOL]
        if debug:
            _debug('API REQUEST', kwargs)
        start = time.perf_counter()
        ttft_recorded = False
        with client.messages.stream(**kwargs) as stream:
            for event in stream:
                if not ttft_recorded and event.type == 'content_block_delta':
                    stats.ttft_ms.append(
                        (time.perf_counter() - start) * 1000
                    )
                    ttft_recorded = True
            response = stream.get_final_message()
        stats.input_tokens += response.usage.input_tokens
        stats.output_tokens += response.usage.output_tokens
        if debug:
            _debug('API RESPONSE', response.model_dump())
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
                stats.tool_calls += 1
        messages.append({'role': 'user', 'content': tool_results})


def get_answer(
    client: anthropic.Anthropic, system: str, question: str, stats: Stats,
    debug: bool = False,
) -> str:
    """Call the API with one automatic retry on failure."""
    stop_event = threading.Event()
    spinner = threading.Thread(target=_run_spinner, args=(stop_event,))
    spinner.start()

    try:
        for attempt in range(2):
            try:
                return _call_api(client, system, question, stats, debug)
            except Exception:
                if attempt == 1:
                    raise
    finally:
        stop_event.set()
        spinner.join()


def _print_stats(stats: Stats) -> None:
    avg_ttft = (
        sum(stats.ttft_ms) / len(stats.ttft_ms) if stats.ttft_ms else 0.0
    )
    print(
        f'\nTotal tool invocations  : {stats.tool_calls}\n'
        f'Total request tokens    : {stats.input_tokens}\n'
        f'Total response tokens   : {stats.output_tokens}\n'
        f'Avg time to first token : {avg_ttft:.1f} ms'
    )


def answer_question(
    client: anthropic.Anthropic,
    classification_system: str,
    system: str,
    question: str,
    stats: Stats,
    cache: dict[str, str],
    debug: bool = False,
) -> str:
    """Classify then answer, or return the default rejection message."""
    if question in cache:
        return cache[question]
    classification = _classify_question(
        client, classification_system, question, stats, debug
    )
    if (
        classification.intent == 'information-seeking'
        and classification.topic == 'wiki'
    ):
        answer = get_answer(client, system, question, stats, debug)
    else:
        answer = DEFAULT_MESSAGE
    cache[question] = answer
    return answer


def _read_single_key() -> str:
    fd = sys.stdin.fileno()
    try:
        old = termios.tcgetattr(fd)
    except termios.error:
        return sys.stdin.read(1)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _ask_feedback() -> str:
    prompt = (
        f'{_colored("[")}'
        'Feedback'
        f'{_colored("] >>> ")}'
        'y: Yes, n: No, SPACE: no opinion / skip  '
    )
    print(prompt, end='', flush=True)
    key = _read_single_key()
    print()
    return key if key in ('y', 'n') else ''


def main() -> None:
    parser = argparse.ArgumentParser(description='Wikipedia answer engine.')
    parser.add_argument(
        '--feedback',
        action='store_true',
        help='Ask for feedback after each answer',
    )
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run a single demo question non-interactively and exit',
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Print API requests and responses',
    )
    args = parser.parse_args()

    try:
        system = _load_system_prompt()
        classification_system = CLASSIFICATION_PROMPT_PATH.read_text(
            encoding='utf-8'
        )
    except OSError as e:
        print(f'{ERROR_PREFIX}{e}')
        sys.exit(1)

    client = anthropic.Anthropic()
    stats = Stats()
    cache: dict[str, str] = {}
    total_questions = 0
    positive_feedback = 0
    negative_feedback = 0
    demo_answered = False
    print(INTRO)

    while True:
        if args.demo:
            if demo_answered:
                print(f'{_prompt("Question")}/end')
                break
            question = "what's the goldilocks zone?"
            print(f'{_prompt("Question")}{question}')
        else:
            try:
                question = input(_prompt('Question'))
            except EOFError:
                break
            if question.strip() == '/end':
                break

        try:
            answer = answer_question(
                client, classification_system, system, question, stats,
                cache, args.debug,
            )
            print(f'{_prompt("Answer  ")}{answer}')
            total_questions += 1
            if args.feedback:
                fb = _ask_feedback()
                if fb == 'y':
                    positive_feedback += 1
                elif fb == 'n':
                    negative_feedback += 1
        except Exception as e:
            print(f'{ERROR_PREFIX}{e}')
            sys.exit(1)

        if args.demo:
            demo_answered = True

    _print_stats(stats)
    if args.feedback:
        print(
            '\nfeedback metrics from the current interactive Q&A session\n'
            f'Total questions  : {total_questions}\n'
            f'Positive (y)     : {positive_feedback}\n'
            f'Negative (n)     : {negative_feedback}'
        )


if __name__ == '__main__':
    main()
