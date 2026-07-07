def drop_rows_by_index(step, dfs):

    target = step.get(
        "input",
        list(dfs.keys())[-1]
    )

    df = dfs[target].copy()

    rows = step["rows"]

    # convert human rows → pandas index
    rows = [r - 1 for r in rows]

    df = df.drop(
        index=rows,
        errors="ignore"
    )

    df = df.reset_index(
        drop=True
    )

    dfs[
        step.get(
            "output",
            target
        )
    ] = df

    print(
        f"drop_rows_by_index -> removed {step['rows']}"
    )