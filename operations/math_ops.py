def add_constant(step, df):

    col = step["col"]

    value = step["value"]

    df[col] = df[col] + value

    return df


def multiply_columns(step, df):

    df[
        step["result"]
    ] = (

        df[
            step["col1"]
        ]

        *

        df[
            step["col2"]
        ]

    )
    return df

def subtract_constant(step, df):

    col = step["col"]

    value = step["value"]

    df[col] = df[col] - value

    return df