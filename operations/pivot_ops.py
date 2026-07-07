def pivot_table_op(step, dfs):

    target = step.get(
        "input",
        list(dfs.keys())[-1]
    )

    df = dfs[target]

    result = df.pivot_table(

        index=step["index"],
        values=step["values"],
        aggfunc=step.get(
            "aggfunc",
            "sum"
        )
    )

    dfs[
        step.get(
            "output",
            target
        )
    ] = result

    print(
        "pivot_table done"
    )