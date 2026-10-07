"""Calendar dates must not be inferred from Unix timestamps or numeric strings."""
import re
from datetime import date, datetime
from typing import Annotated

from pydantic import BeforeValidator


def calendar_date(value):
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    raise ValueError('Capture una fecha válida con formato AAAA-MM-DD.')


CalendarDate = Annotated[date, BeforeValidator(calendar_date)]
