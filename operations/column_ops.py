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


RENAMED_COLUMNS = {}

def rename_columns(step, df):

    mapping = step["mapping"]

    df.rename(
        columns=mapping,
        inplace=True
    )

    RENAMED_COLUMNS.update(mapping)

    return df

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


def combine_columns(step, dfs):

    target = step.get(
        "input",
        list(dfs.keys())[-1]
    )

    df = dfs[target].copy()
    cols = step["columns"]
    new_col = step.get(
        "new_column",
        "_".join(cols)
    )

    df[new_col] = (
        df[cols]
        .astype(str)
        .agg(
            " ".join,
            axis=1
        )
    )

    dfs[
        step.get(
            "output",
            target
        )
    ] = df

    print(
        f"combine_columns -> {cols}"
    )