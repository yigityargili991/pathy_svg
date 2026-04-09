"""Data transformation utilities for pathy_svg."""

from __future__ import annotations

import bisect


def normalize_values(data: dict[str, float]) -> dict[str, float]:
    """Min-max normalise a dict of float values to the range [0, 1].

    If all values are identical the function returns all zeros to avoid division-by-zero.

    Args:
        data: A dictionary mapping identifiers to numeric values.

    Returns:
        A dictionary with the same keys, mapped to normalized values in [0, 1].

    Examples:
        >>> normalize_values({"a": 0, "b": 5, "c": 10})
        # {"a": 0.0, "b": 0.5, "c": 1.0}
    """
    if not data:
        return {}
    values = list(data.values())
    lo = min(values)
    hi = max(values)
    rng = hi - lo
    if rng == 0:
        return {k: 0.0 for k in data}
    return {k: (v - lo) / rng for k, v in data.items()}


def bin_values(data: dict[str, float], breaks: list[float]) -> dict[str, int]:
    """Assign each value in data to a bin index defined by breaks.

    Bin indices are 0-based. A value ``v`` falls into bin ``i`` when
    ``breaks[i] <= v < breaks[i+1]``. Values below the first break are
    placed in bin 0; values at or above the last break are placed in the last bin.

    Args:
        data: Mapping of key to numeric value.
        breaks: Ordered sequence of boundary values that define bins. Must contain at least two elements.

    Returns:
        A dictionary mapping the same keys to integer bin indices.

    Raises:
        ValueError: If breaks contains fewer than two values.

    Examples:
        >>> bin_values({"a": 1, "b": 5, "c": 9}, [0, 3, 6, 10])
        # {"a": 0, "b": 1, "c": 2}
    """
    if len(breaks) < 2:
        raise ValueError("breaks must contain at least two values")
    sorted_breaks = sorted(breaks)
    result: dict[str, int] = {}
    n_bins = len(sorted_breaks) - 1
    for key, val in data.items():
        idx = bisect.bisect_right(sorted_breaks, val) - 1
        idx = max(0, min(idx, n_bins - 1))
        result[key] = idx
    return result


def dataframe_to_dict(df, id_col: str, value_col: str) -> dict[str, float]:
    """Extract a data dict from a Pandas DataFrame.

    Args:
        df: A Pandas DataFrame.
        id_col: Column name for element IDs.
        value_col: Column name for numeric values.

    Returns:
        A dict mapping IDs to float values.

    Raises:
        ValueError: If required columns are missing from the DataFrame.

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"id": ["a", "b"], "value": [1.0, 2.0]})
        >>> dataframe_to_dict(df, "id", "value")
        {"a": 1.0, "b": 2.0}
    """
    import pandas as pd

    if id_col not in df.columns:
        raise ValueError(f"Column '{id_col}' not found in DataFrame")
    if value_col not in df.columns:
        raise ValueError(f"Column '{value_col}' not found in DataFrame")
    numeric = pd.to_numeric(df[value_col], errors="coerce")
    valid = numeric.dropna()
    return dict(zip(df.loc[valid.index, id_col].astype(str), valid))
