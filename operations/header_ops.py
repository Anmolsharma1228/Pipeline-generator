def use_row_as_header(step, dfs):

    target = step.get(
        "input",
        list(dfs.keys())[-1]
    )

    df = dfs[target].copy()
    row = step.get(
        "row",
        1
    )

    # convert user row number → pandas index
    row_index = row - 1

    if row_index >= len(df):

        raise ValueError(
            f"Row {row} does not exist"
        )

    # make selected row new header
    df.columns = df.iloc[
        row_index
    ]

    # remove header row
    df = df.iloc[
        row_index + 1:
    ]

    df = df.reset_index(
        drop=True
    )

    out = step.get(
        "output",
        target
    )

    dfs[out] = df

    print(
        f"use_row_as_header -> row {row}"
    )