def transpose(step, dfs):

    target = step.get(
        "input",
        list(dfs.keys())[-1]
    )

    df = dfs[target]
    transposed = df.T

    out = step.get(
        "output",
        target
    )

    dfs[out] = transposed

    print(
        f"transpose -> rows={len(transposed)}"
    )