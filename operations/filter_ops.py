def filter_rows(step, df):

    column = step["column"]
    op = step["operator"]
    value = step["value"]

    if op == ">":
        return df[
            df[column] > value
        ]

    elif op == "<":
        return df[
            df[column] < value
        ]

    elif op == ">=":
        return df[
            df[column] >= value
        ]

    elif op == "<=":
        return df[
            df[column] <= value
        ]

    elif op == "==":
        return df[
            df[column] == value
        ]

    return df