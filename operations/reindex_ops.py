def reindex_columns(step, dfs):

    target = step.get(
        "input",
        list(dfs.keys())[-1]
    )

    df = dfs[target]

    cols = sorted(
        df.columns
    )

    df = df.reindex(
        columns=cols
    )

    dfs[
        step.get(
            "output",
            target
        )
    ] = df

    print(
        f"reindex_columns -> {cols}"
    )