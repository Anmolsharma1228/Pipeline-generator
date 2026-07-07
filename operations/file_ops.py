import pandas as pd
import os
import json

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

    output_folder = r"C:\Users\abc\Desktop\testing"

    os.makedirs(
        output_folder,
        exist_ok=True
    )

    path = os.path.join(
        output_folder,
        step["path"]
    )

    df.to_csv(
        path,
        index=False
    )


def to_json(step, df):

    output_folder = r"C:\Users\abc\Desktop\testing"

    os.makedirs(
        output_folder,
        exist_ok=True
    )

    path = os.path.join(
        output_folder,
        step.get(
            "path",
            "output.json"
        )
    )

    df.to_json(
        path,
        orient="records",
        indent=4
    )

    print(
        f"to_json -> {path}"
    )

    return df



def to_html(step, df):

    output_folder = r"C:\Users\abc\Desktop\testing"

    os.makedirs(
        output_folder,
        exist_ok=True
    )

    path = os.path.join(
        output_folder,
        step.get(
            "path",
            "output.html"
        )
    )

    df.to_html(
        path,
        index=False
    )

    print(
        f"to_html -> {path}"
    )


    return df