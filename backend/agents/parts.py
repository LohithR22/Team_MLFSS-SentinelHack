"""
Parts Agent — lookups over fault_codes.db.

Sources:
- fault_codes.fault_codes  (15 rows)  — Code -> Part Code mapping
- fault_codes.parts        (15 rows)  — part_number, part_required, location, availability

Codes are stored with hyphens ("01-02-99"). We normalize any slash form to
hyphen defensively on input so callers don't have to worry about it.
"""
from __future__ import annotations

import sqlite3

from django.conf import settings

from agents.black_box import black_box


def _db_path():
    return settings.DATABASES['fault_codes']['NAME']


def _normalize(code: str) -> str:
    return code.replace('/', '-')


@black_box(phase='parts')
def get_part_for_code(code: str) -> dict:
    """
    Return the replacement part for a fault code.

    Returns a dict with:
      code, part_code, part_name, location, availability, machine, severity
    """
    hyph = _normalize(code)

    with sqlite3.connect(_db_path()) as con:
        con.row_factory = sqlite3.Row
        fault = con.execute(
            'SELECT "Code","Part Code","Part Required","Machine","Severity" '
            'FROM fault_codes WHERE "Code"=?',
            (hyph,),
        ).fetchone()
        if fault is None:
            raise ValueError(f'No fault_codes row for code={code!r}')

        part_code = fault['Part Code']
        part = con.execute(
            'SELECT part_number, part_required, location, availability '
            'FROM parts WHERE part_number=?',
            (part_code,),
        ).fetchone()

    if part is None:
        return {
            'code': hyph,
            'part_code': part_code,
            'part_name': fault['Part Required'],
            'location': None,
            'availability': 'unknown',
            'machine': fault['Machine'],
            'severity': fault['Severity'],
        }

    return {
        'code': hyph,
        'part_code': part['part_number'],
        'part_name': part['part_required'],
        'location': part['location'],
        'availability': part['availability'],
        'machine': fault['Machine'],
        'severity': fault['Severity'],
    }


@black_box(phase='parts')
def check_availability(part_number: str) -> dict:
    """Direct stock check by part_number."""
    with sqlite3.connect(_db_path()) as con:
        con.row_factory = sqlite3.Row
        row = con.execute(
            'SELECT part_number, part_required, location, availability '
            'FROM parts WHERE part_number=?',
            (part_number,),
        ).fetchone()
    if row is None:
        raise ValueError(f'Unknown part_number={part_number!r}')
    return dict(row)


@black_box(phase='parts')
def list_unavailable() -> list[dict]:
    """All parts currently marked availability='No'."""
    with sqlite3.connect(_db_path()) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            'SELECT part_number, part_required, location, availability '
            "FROM parts WHERE availability='No' ORDER BY part_number"
        ).fetchall()
    return [dict(r) for r in rows]
