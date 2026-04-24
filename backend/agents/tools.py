"""
Tools Agent — tool inventory + Florence VLM visual descriptions.

Loads two sources into memory on first call, joins them on image filename:
  1. fault_codes.db -> tools  (77 rows: Tool Name, Type, locations, Primary Use, Image)
  2. tool_descriptions_florence.json  (77 entries: image_name -> description)

Also loads KB common_tools per code so callers can ask "what tools do I
need for fault 01-02-99?".
"""
from __future__ import annotations

import json
import os
import sqlite3

from django.conf import settings

from agents.black_box import black_box


_TOOLS_CACHE: dict[str, dict] | None = None          # lowercased tool_name -> info
_KB_TOOLS_BY_CODE: dict[str, list[str]] | None = None  # code -> [tool_name, ...]


def _load_caches() -> None:
    """Lazy-load tools table joined with Florence descriptions + KB tool lists."""
    global _TOOLS_CACHE, _KB_TOOLS_BY_CODE
    if _TOOLS_CACHE is not None and _KB_TOOLS_BY_CODE is not None:
        return

    florence_path = settings.REPO_ROOT / 'tool_descriptions_florence.json'
    with open(florence_path) as f:
        florence = json.load(f)
    flor_by_basename = {e['image_name']: e['description'] for e in florence}

    tools_db = settings.DATABASES['fault_codes']['NAME']
    with sqlite3.connect(tools_db) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            'SELECT UID, "Tool Name", Type, locations, "Primary Use", Image FROM tools'
        ).fetchall()

    cache: dict[str, dict] = {}
    for r in rows:
        basename = os.path.basename(r['Image'] or '')
        cache[r['Tool Name'].lower()] = {
            'uid': r['UID'],
            'tool_name': r['Tool Name'],
            'type': r['Type'],
            'location': r['locations'],
            'primary_use': r['Primary Use'],
            'image_path': r['Image'],
            'image_basename': basename,
            'visual_description': flor_by_basename.get(basename),
        }
    _TOOLS_CACHE = cache

    kb_map: dict[str, list[str]] = {}
    for kb_name in ('engines.json', 'pumps.json', 'pipelines.json'):
        with open(settings.KB_DIR / kb_name) as f:
            data = json.load(f)
        for code, entry in data.items():
            kb_map[code] = list(entry.get('common_tools') or [])
    _KB_TOOLS_BY_CODE = kb_map


def _normalize(code: str) -> str:
    return code.replace('/', '-')


def _resolve_tool(name: str) -> dict:
    """Inner lookup — does NOT go through @black_box so nested calls don't double-log."""
    info = _TOOLS_CACHE.get(name.lower())
    if info is None:
        return {
            'tool_name': name,
            'found_in_room_8': False,
            'location': None,
            'type': None,
            'primary_use': None,
            'image_path': None,
            'visual_description': None,
        }
    return {'found_in_room_8': True, **info}


@black_box(phase='tools')
def get_tool(name: str) -> dict:
    """Look up a single tool by name (case-insensitive)."""
    _load_caches()
    return _resolve_tool(name)


@black_box(phase='tools')
def get_tools_for_code(code: str) -> list[dict]:
    """
    Return all tools listed in the KB's common_tools for this fault code.

    Each result has found_in_room_8 = True/False. Tools invented by the KB
    that don't exist in the Room 8 inventory come back with location=None
    and found_in_room_8=False so the UI can flag them as "procure".
    """
    _load_caches()
    hyph = _normalize(code)
    tool_names = _KB_TOOLS_BY_CODE.get(hyph)
    if tool_names is None:
        raise ValueError(f'No KB entry for code={code!r}')
    return [_resolve_tool(name) for name in tool_names]


@black_box(phase='tools')
def list_all_tools() -> list[dict]:
    """Full Room 8 inventory with Florence descriptions."""
    _load_caches()
    return list(_TOOLS_CACHE.values())
