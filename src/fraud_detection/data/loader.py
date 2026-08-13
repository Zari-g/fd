"""CSV loading functions."""

from os import PathLike
from pathlib import Path

import pandas as pd


def load_card_data(path: str | PathLike[str]) -> pd.DataFrame:
    """Load card data from a CSV file.

    Parameters
    ----------
    path:
        Path to the source CSV file.

    Returns
    -------
    pandas.DataFrame
        The loaded data using pandas' standard CSV type inference. The source
        file is not modified.

    Raises
    ------
    FileNotFoundError
        If ``path`` does not exist.
    IsADirectoryError
        If ``path`` points to a directory.
    ValueError
        If the file is empty, malformed, unreadable, or not valid UTF-8.
    """
    csv_path = Path(path)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file does not exist: {csv_path}")
    if not csv_path.is_file():
        raise IsADirectoryError(f"Expected a CSV file, received a directory: {csv_path}")

    try:
        return pd.read_csv(csv_path)
    except pd.errors.EmptyDataError as exc:
        raise ValueError(f"CSV file is empty: {csv_path}") from exc
    except (pd.errors.ParserError, UnicodeDecodeError, OSError) as exc:
        raise ValueError(f"Could not read CSV file {csv_path}: {exc}") from exc
