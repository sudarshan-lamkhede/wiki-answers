#!/usr/bin/env python3
"""Standalone Wikipedia search tool."""

import html
import json
import re
import sys
import urllib.parse
import urllib.request

from pydantic import BaseModel

WIKI_API = 'https://en.wikipedia.org/w/api.php'
WIKI_BASE_URL = 'https://en.wikipedia.org/wiki/'
USER_AGENT = 'wiki-search/1.0'
TOP_N = 3
EXTENDED_SNIPPET_TOKENS = 128


class WikiSearchResult(BaseModel):
    title: str
    snippet: str
    url: str
    extended_snippet: str


def _fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _clean_snippet(text: str) -> str:
    return html.unescape(re.sub(r'<[^>]+>', '', text)).strip()


def _search(query: str) -> list[dict]:
    params = urllib.parse.urlencode({
        'action': 'query',
        'list': 'search',
        'srsearch': query,
        'srlimit': TOP_N,
        'format': 'json',
        'utf8': '1',
    })
    return _fetch_json(f'{WIKI_API}?{params}')['query']['search']


def _fetch_article_extract(title: str) -> str:
    params = urllib.parse.urlencode({
        'action': 'query',
        'titles': title,
        'prop': 'extracts',
        'explaintext': '1',
        'format': 'json',
    })
    pages = _fetch_json(f'{WIKI_API}?{params}')['query']['pages']
    return next(iter(pages.values())).get('extract', '')


def _extended_snippet(title: str) -> str:
    tokens = _fetch_article_extract(title).split()
    return ' '.join(tokens[:EXTENDED_SNIPPET_TOKENS])


def _article_url(title: str) -> str:
    return WIKI_BASE_URL + urllib.parse.quote(title.replace(' ', '_'))


def search_wikipedia(query: str) -> list[WikiSearchResult]:
    """Search Wikipedia and return the top results with enriched snippets."""
    results = []
    for item in _search(query):
        title = item['title']
        results.append(WikiSearchResult(
            title=title,
            snippet=_clean_snippet(item['snippet']),
            url=_article_url(title),
            extended_snippet=_extended_snippet(title),
        ))
    return results


def format_markdown(results: list[WikiSearchResult], query: str) -> str:
    lines: list[str] = [f'# Wikipedia Search: "{query}"', '']
    for i, r in enumerate(results, 1):
        lines += [
            f'## {i}. {r.title}',
            f'**URL:** <{r.url}>',
            '',
            '**Snippet**',
            f'> {r.snippet}',
            '',
            '**Extended Snippet**',
            f'> {r.extended_snippet}',
            '',
            '---',
            '',
        ]
    return '\n'.join(lines)


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python3 wiki-search.py <query>')
        sys.exit(1)
    query = ' '.join(sys.argv[1:])
    print(format_markdown(search_wikipedia(query), query))


if __name__ == '__main__':
    main()
