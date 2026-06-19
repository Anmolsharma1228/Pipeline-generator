import pandas as pd
import os


def read_excel_any(step, df):

    path = (
        "uploads/"
        +
        step["path"]
    )

    rows = step.get(
        "rows"
    )

    if rows:

        return pd.read_excel(
            path
        ).head(rows)

    return pd.read_excel(
        path
    )


def read_csv(step, df):

    path = (
        "uploads/"
        +
        step["path"]
    )

    rows = step.get(
        "rows"
    )

    if rows:

        return pd.read_csv(
            path
        ).head(rows)

    return pd.read_csv(
        path
    )


def write_csv(step, df):

    os.makedirs(
        "generated",
        exist_ok=True
    )

    path = (
        "generated/"
        +
        step["path"]
    )

    df.to_csv(
        path,
        index=False
    )

    return df