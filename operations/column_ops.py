def add_column(step, df):

    column = step["column"]

    value = step.get(
        "value",
        ""
    )

    df[
        column
    ] = value

    return df


def rename_columns(step, df):

    mapping = step["mapping"]

    return df.rename(
        columns=mapping
    )

def sort_values(step, df):

    column = step["by"]

    ascending = step.get(
        "ascending",
        True
    )

    return df.sort_values(
        by=column,
        ascending=ascending
    )

def drop_columns(step, df):

    cols = step["cols"]

    # normalize dataframe columns
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
    )

    existing = []

    for col in cols:

        if col.strip() in df.columns:

            existing.append(
                col.strip()
            )

    if not existing:

        raise Exception(
            f"Column not found. Available columns: {list(df.columns)}"
        )

    return df.drop(
        columns=existing
    )


def select_columns(step, df):

    cols = step["cols"]

    # remove spaces
    cols = [
        c.strip()
        for c in cols
    ]

    return df[
        cols
    ]