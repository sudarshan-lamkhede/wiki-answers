#!/usr/bin/env python3
"""Interactive answer engine based on Claude and Wikipedia."""

import threading
import time

BRACKET_COLOR = '\033[38;2;185;102;72m'
RESET = '\033[0m'
INTRO = (
    "Interactive answer engine based on Claude and Wikipedia. "
    "Strictly single-turn i.e. response will be only based on the current "
    "question and will not consider prior conversation. "
    "Submit '/end' to stop the program."
)


def _colored(text: str) -> str:
    return f'{BRACKET_COLOR}{text}{RESET}'


def _prompt(label: str) -> str:
    return f'{_colored("[")}{label}{_colored("] >>> ")}'


def dummy_answer(question: str) -> str:
    return f'You asked: {question}'


def _run_spinner(stop_event: threading.Event) -> None:
    frames = ('|', '/', '-', '\\')
    i = 0
    while not stop_event.is_set():
        print(f'\r{frames[i % len(frames)]}', end='', flush=True)
        i += 1
        time.sleep(0.1)
    print('\r \r', end='', flush=True)


def get_answer(question: str) -> str:
    stop_event = threading.Event()
    spinner = threading.Thread(target=_run_spinner, args=(stop_event,))
    spinner.start()
    time.sleep(3)
    stop_event.set()
    spinner.join()
    return dummy_answer(question)


def main() -> None:
    print(INTRO)
    while True:
        try:
            question = input(_prompt('Question'))
        except EOFError:
            break
        if question.strip() == '/end':
            break
        answer = get_answer(question)
        print(f'{_prompt("Answer")}{answer}')


if __name__ == '__main__':
    main()
