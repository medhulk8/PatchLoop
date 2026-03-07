from itertools import groupby


def group_rows(rows: list[tuple[str, int]]) -> dict[str, list[int]]:
    """Group (key, value) pairs by key, collecting values into lists.

    Key order must match first-seen order in the input.
    Value order within each key must match input order.
    """
    # BUG: groupby only groups *contiguous* runs of the same key.
    # Non-contiguous rows with the same key produce separate groups,
    # and the dict comprehension silently overwrites the earlier group.
    return {
        k: [v for _, v in group]
        for k, group in groupby(rows, key=lambda row: row[0])
    }
