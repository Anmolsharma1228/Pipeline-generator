import pandas as pd

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


def divide_columns(step, df):

    col1 = step["col1"]
    col2 = step["col2"]
    result = step["result"]

    df[result] = (

        df[col1]

        /

        df[col2].replace(
            0,
            None
        )
    )
    
    return df


def aggregate(step, df):

    column = step["column"]
    agg = step["agg"]
    groupby = step.get("groupby")


    if groupby:

        result = (

            df
            .groupby(groupby)[column]
            .agg(agg)
            .reset_index()

        )

        return result


    if agg == "sum":
        value = df[column].sum()

    elif agg == "mean":
        value = df[column].mean()

    elif agg == "max":
        value = df[column].max()

    elif agg == "min":
        value = df[column].min()

    else:
        raise Exception(
            f"Unsupported aggregate {agg}"
        )

    return pd.DataFrame([
        {
            column: value
        }
    ])