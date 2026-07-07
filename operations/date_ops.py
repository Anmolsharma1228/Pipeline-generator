import pandas as pd


def extract_date_parts(step, dfs):

    target = step.get(
        "input",
        list(dfs.keys())[-1]
    )

    df = dfs[target].copy()

    col = step.get(
      "col",
      step.get("column")
  )

    df[col] = pd.to_datetime(
        df[col]
    )

    df[f"{col}_year"] = (
        df[col].dt.year
    )

    df[f"{col}_month"] = (
        df[col].dt.month
    )

    df[f"{col}_day"] = (
        df[col].dt.day
    )

    dfs[
        step.get(
            "output",
            target
        )
    ] = df

    print(
        f"extract_date_parts -> {col}"
    )


def add_days(step, dfs):

    target = step.get(
        "input",
        list(dfs.keys())[-1]
    )

    df = dfs[target].copy()

    col = step.get(
        "column"
    )

    days = step.get(
        "days",
        0
    )

    df[col] = pd.to_datetime(
        df[col]
    )

    df[col] = (
        df[col]
        +
        pd.Timedelta(
            days=days
        )
    )

    dfs[
        step.get(
            "output",
            target
        )
    ] = df

    print(
        f"add_days -> {days}"
    )


def subtract_days(step, dfs):

    target = step.get(
        "input",
        list(dfs.keys())[-1]
    )

    df = dfs[target].copy()

    col = step["column"]

    days = step["days"]

    df[col] = pd.to_datetime(
        df[col]
    )

    df[
        f"{col}_minus_{days}d"
    ] = (

        df[col]

        -

        pd.Timedelta(
            days=days
        )
    )

    dfs[
        step.get(
            "output",
            target
        )
    ] = df

    print(
        f"subtract_days -> {days}"
    )



def format_date(step, dfs):

    target = step.get(
        "input",
        list(dfs.keys())[-1]
    )

    df = dfs[target].copy()
    col = step["column"]
    new_col = (
        f"{col}_formatted"
    )

    # convert source column
    temp = pd.to_datetime(
        df[col]
    )

    # IMPORTANT → create STRING column
    df[new_col] = (
        temp
        .dt.strftime(
            "%d-%b-%Y"
        )
        .astype(str)
    )

    out = step.get(
        "output",
        target
    )

    dfs[out] = df

    print(
        df[
            [col, new_col]
        ].head()
    )


def date_diff(step, dfs):

      target = step.get(
          "input"
      )

      df = dfs[target].copy()

      start = step[
          "start_col"
      ]

      end = step[
          "end_col"
      ]

      result = step.get(
          "result",
          "date_diff"
      )

      df[start] = pd.to_datetime(
          df[start]
      )

      df[end] = pd.to_datetime(
          df[end]
      )

      df[result] = (
          df[end]
          -
          df[start]
      ).dt.days

      dfs[
          step["output"]
      ] = df

      print(
          f"date_diff -> {start} vs {end}"
      )