import re

def uppercase(step, df):

    col = step["col"]
    output_col = step.get(
        "output_col",
        col
    )

    if col not in df.columns:

        print(
            f"WARNING: Column '{col}' not found"
        )

        return df

    df[output_col] = (

        df[col]
        .astype(str)
        .str.upper()

    )

    return df


def lowercase(step, df):

    col = step["col"]
    output_col = step.get(
        "output_col",
        col
    )

    if col not in df.columns:

        print(
            f"WARNING: Column '{col}' not found"
        )

        return df

    df[output_col] = (

        df[col]
        .astype(str)
        .str.lower()

    )

    return df


def replace_str(step, df):

    print("===== REPLACE_STR EXECUTED =====")

    old = str(step["old"]).strip()
    new = str(step["new"]).strip()

    col = step.get("col")

    print("Old:", old)
    print("New:", new)

    print("\nBefore Replace:")
    print(df.head(10))

    if col:

        df[col] = (
            df[col]
            .astype(str)
            .str.replace(old, new, case=False, regex=False)
        )

    else:

        for c in df.select_dtypes(include="object").columns:

            print(f"Checking column: {c}")

            df[c] = (
                df[c]
                .astype(str)
                .str.replace(old, new, case=False, regex=False)
            )

    print("\nAfter Replace:")
    print(df.head(10))

    return df


def trim_whitespace(step, df):

    col = step["col"]
    output_col = step.get(
        "output_col",
        col
    )

    if col not in df.columns:

        print(
            f"WARNING: Column '{col}' not found"
        )

        return df

    df[output_col] = (

        df[col]
        .astype(str)
        .str.strip()

    )

    return df

def split_column(step, df):

    col = step["col"]
    separator = step.get(
        "separator",
        " "
    )

    if col not in df.columns:

        print(
            f"WARNING: Column '{col}' not found"
        )

        return df

    split_df = (

        df[col]
        .astype(str)
        .str.split(
            separator,
            expand=True
        )

    )

    for i in range(
        split_df.shape[1]
    ):

        df[
            f"{col}_{i+1}"
        ] = split_df[i]

    return df

def extract_pattern(step, df):

    col = step["col"]
    pattern = step["pattern"]
    output_col = step.get(
        "output_col",
        f"{col}_pattern"
    )

    if col not in df.columns:

        print(
            f"WARNING: Column '{col}' not found"
        )

        return df

    df[output_col] = (

        df[col]
        .astype(str)
        .str.extract(
            pattern
        )

    )

    return df