import os
from typing import Any
from datetime import datetime


def get_env_var(var_name: str, default: Any = None, required: bool = False) -> Any:
    value = os.environ.get(var_name, default=default)
    if not value and not (not required or default):
        raise ValueError(
            f'You must specify environment variable named {var_name}. '
            'In Heroku go to App settings -> Config Vars -> Reveal Config Vars -> Add. '
            f'In Bash type \"export {var_name}=your_value\".'
        )

    return value


def time_str_from_timestamp(timestamp: int):
    d = datetime.fromtimestamp(timestamp)
    return d.strftime('%H:%M %d/%m/%Y')
