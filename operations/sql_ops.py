import pandas as pd
import sqlite3


def write_sql(step, dfs):

    df = dfs[
        step["input"]
    ]

    table = step.get(
        "table",
        "employees"
    )

    conn = sqlite3.connect(
        "database.db"
    )

    df.to_sql(
        table,
        conn,
        if_exists="replace",
        index=False
    )

    conn.close()

    print(
        f"write_sql -> {table}"
    )



def read_database(step, dfs):

    table = step.get(
        "table",
        "employees"
    )

    conn = sqlite3.connect(
        "database.db"
    )

    df = pd.read_sql(
        f"SELECT * FROM {table}",
        conn
    )

    conn.close()

    dfs[
        step["output"]
    ] = df

    print(
        f"read_database -> {len(df)} rows"
    )