import json
import os
import re
import time
import random

# Works whether llm_parser.py lives in a llm/ subfolder (original
# project layout) or flat next to this file (e.g. after uploading
# individual files somewhere new) - tries the package form first.
try:
    from llm.llm_parser import normalize_prompt
except ModuleNotFoundError:
    from llm.llm_parser import normalize_prompt

from column_resolver import remap_pipeline_columns, _OP_COLUMN_SPEC


# ============================================================
# DYNAMIC CONFIG
#
# Everything an operation needs to be recognised - its trigger
# regex(es), how to turn a match into pipeline-step fields, and
# the "boundary" keywords that mark where the next operation in
# the sentence starts - lives in the tables below instead of
# being hand-rolled inside each parse_* function. To add or tweak
# an operation you edit a table here, not hunt through hundreds
# of lines of near-identical regex blocks.
#
# The dataframe/table name is resolved once per prompt (instead
# of being hardcoded as the literal "dataframe" in ~15 different
# places) and threaded through every parser, so a prompt like
# "read sales.csv into dataframe named sales_df" produces steps
# that all reference sales_df, not a hardcoded default.
# ============================================================

DEFAULT_TABLE = "dataframe"

NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "ten": 10, "twenty": 20, "fifty": 50,
}

# extension -> pipeline operation, for reading a source file.
READ_EXTENSION_OPS = {
    "csv": "read_csv",
    "xls": "read_excel_any",
    "xlsx": "read_excel_any",
    "json": "read_json",
}

# extension -> pipeline operation, for exporting the result.
EXPORT_EXTENSION_OPS = {
    "csv": "write_csv",
    "xls": "write_excel",
    "xlsx": "write_excel",
    "json": "to_json",
    "html": "to_html",
}

# word used in a prompt -> pandas aggregation function name.
AGG_WORD_MAP = {
    "aggregate": "sum", "sum": "sum", "total": "sum",
    "average": "mean", "mean": "mean",
    "max": "max", "min": "min", "count": "count",
}

# comparison phrase used in a prompt -> pandas/py operator.
FILTER_OPERATOR_MAP = {
    "greater than": ">", "more than": ">", "above": ">",
    "over": ">", "exceeds": ">",
    "less than": "<", "below": "<", "under": "<",
    "=": "==", "is": "==", "equals": "==", "equal to": "==",
}


def make_boundary(alternatives, spacer=r"\s+"):
    """
    Build a lookahead boundary regex from a *list* of trigger
    keywords/fragments instead of a hand-typed alternation string.
    Editing what counts as "the next operation has started" for a
    family of operations means editing a list below, not a regex
    literal buried inside a function.
    """
    return rf"(?={spacer}(?:{'|'.join(alternatives)}))"


def make_boundary_wb(alternatives):
    """
    Variant boundary used by patterns that want a word-boundary
    before the keyword OR a bare end-of-string (no trailing
    whitespace required), e.g. "...only city, department" at the
    very end of a prompt.
    """
    return rf"(?=\s+(?:{'|'.join(alternatives)})\b|$)"


# Keyword sets used to build the lookahead boundaries below. Each
# list is the *only* thing that needs to change to teach a family
# of operations about a new trigger word.
BOUNDARY_KEYWORDS = {
    "default": [
        "save", "write", "export", "sort", "filter", "keep", "select",
        "drop", "rename", "replace", "uppercase", "lowercase", "trim",
        "split", "extract", "compute", "date", "finally", "then",
        "also", "now", "add", "subtract", "multiply", "divide",
        "where", "$",
    ],
    "math": [
        "column", "columns", "sheet", "rows?", "records?", "save",
        "write", "export", "sort", "filter", "keep", "select", "drop",
        "rename", "replace", "uppercase", "lowercase", "trim", "split",
        "extract", "compute", "date", "then", "also", "finally",
        "where", "whose", "with", r"and\s+save", "$",
    ],
    "string": [
        "replace", "uppercase", "lowercase", "rename", "sort", "trim",
        "split", "extract", "save", "export", "write", "filter",
        "keep", "select", "drop", "subtract", "add", "multiply",
        "divide", "compute", "date", "finally", "$",
    ],
    "select": [
        "rename", "convert", "change", "uppercase", "lowercase",
        "replace", "trim", "split", "extract", "sort", "filter",
        "drop", "save", "export", "write", "store", "finally",
        "then", "also", r"and\s+then", "now", r"date\s+difference",
        r"extract\s+date", r"add\s+\d+\s+days?",
        r"subtract\s+\d+\s+days?", r"format\s+date",
    ],
    "duplicates": [
        ",",
        "then", "after", "if", "replace", "fill", "keep", "select",
        "rename", "sort", "save", "export", "write", "finally", "$",
    ],
}

NEXT_OP_DEFAULT = make_boundary(BOUNDARY_KEYWORDS["default"])
NEXT_OP_MATH = make_boundary(BOUNDARY_KEYWORDS["math"], spacer=r"\s*")
NEXT_OP_STRING = make_boundary(BOUNDARY_KEYWORDS["string"])
NEXT_OP_SELECT = make_boundary_wb(BOUNDARY_KEYWORDS["select"])
NEXT_OP_DUPLICATES = make_boundary(BOUNDARY_KEYWORDS["duplicates"])


def generate_id():

    return int(
        f"{int(time.time()*1000)}{random.randint(10,99)}"
    )


def add_step(pipeline, operation, position=None, **kwargs):
    """
    Add a pipeline step and remember where it appeared
    in the user's prompt.
    """

    step = {
        "id": generate_id(),
        "operation": operation,
        "__pos": position if position is not None else 999999
    }

    step.update(kwargs)

    pipeline.append(step)


def find_match(prompt, patterns):

    for pattern in patterns:

        m = re.search(
            pattern,
            prompt,
            re.I
        )

        if m:
            return m

    return None


def normalize_col(col):

    col = col.strip().lower()
    col = re.sub(r"\s+", "_", col)

    return col


def strip_quotes(text):
    """
    Strip one layer of matching surrounding quotes ('...' or "...")
    from a captured literal value. Prompts often quote the literal
    they want inserted/matched (e.g. "replace it with 'unknown'"),
    and the regexes that pull that text out have no reason to know
    the quotes aren't part of the value - so every literal-value
    capture site needs this before it lands in the pipeline JSON.
    """

    if not isinstance(text, str):
        return text

    text = text.strip()

    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1].strip()

    return text


def parse_columns(text):
    """
    Convert:
    city
    city, department
    city and department

    into

    ["city", "department"]
    """

    text = text.replace(" and ", ",")

    columns = [
        normalize_col(col.strip())
        for col in text.split(",")
        if col.strip()
    ]

    return columns


def resolve_table_name(prompt):
    """
    Figure out which dataframe/table name the pipeline should use
    for this prompt. Falls back to DEFAULT_TABLE when the user
    didn't name one - this is the single place that decides the
    table name, instead of each parse_* function hardcoding
    "dataframe" independently.
    """

    df_match = re.search(
        r"dataframe\s+(?:named|called)\s+([A-Za-z_]\w*)",
        prompt,
        re.I
    )

    if df_match:
        return df_match.group(1)

    return DEFAULT_TABLE


# ============================================================
# GENERIC RULE ENGINE
# ============================================================

def _safe_build(build, match, table, prompt, operation):
    """
    Call a rule's build() function defensively. A single unusual
    phrasing causing one build function to raise (wrong group
    index, unexpected None, etc.) must never take down the whole
    /generate request - it should just mean that ONE step gets
    skipped instead of the entire pipeline failing with a raw
    500 error for a prompt that got 90% correctly parsed.
    """

    try:
        return build(match, table, prompt)
    except Exception as e:
        print(f"parser: skipped a '{operation}' match -> {e}")
        return None


def run_pattern_rules(prompt, rules, table):
    """
    Generic driver for config-driven parsing. Each rule supplies
    its own pattern(s) and a "build" callable that turns a match
    into step kwargs (or None to skip that match). This is what
    lets adding a new operation mean adding a table entry instead
    of writing a new near-duplicate function.

    mode:
      "first"  - try each pattern in order, stop at the first one
                 that matches (mirrors the original if/elif style
                 used for mutually-exclusive phrasings).
      "each_pattern_first" - every pattern gets its own
                 independent first match (mirrors code that ran
                 several unrelated standalone regexes).
      "all"    - re.finditer over every pattern, so a prompt can
                 trigger the same operation more than once
                 (mirrors code that used finditer directly).
    """

    pipeline = []

    for rule in rules:

        mode = rule.get("mode", "first")
        flags = rule.get("flags", re.I)
        build = rule["build"]
        operation = rule["operation"]

        if mode == "first":

            for pattern in rule["patterns"]:

                match = re.search(pattern, prompt, flags)

                if match:

                    kwargs = _safe_build(build, match, table, prompt, operation)

                    if kwargs is not None:
                        add_step(
                            pipeline, operation,
                            position=match.start(), **kwargs
                        )

                    break

        elif mode == "each_pattern_first":

            for pattern in rule["patterns"]:

                match = re.search(pattern, prompt, flags)

                if match:

                    kwargs = _safe_build(build, match, table, prompt, operation)

                    if kwargs is not None:
                        add_step(
                            pipeline, operation,
                            position=match.start(), **kwargs
                        )

        elif mode == "all":

            for pattern in rule["patterns"]:

                for match in re.finditer(pattern, prompt, flags):

                    kwargs = _safe_build(build, match, table, prompt, operation)

                    if kwargs is not None:
                        add_step(
                            pipeline, operation,
                            position=match.start(), **kwargs
                        )

    return pipeline


# ============================================================
# READ
# ============================================================

READ_PRIMARY_PATTERN = (
    r"(?:file\s+name(?:d)?|named|open|read|load|import)"
    r"\s+(?:this\s+file\s+|the\s+file\s+|file\s+)?"
    r"([A-Za-z0-9_.()\-]+\.(?:csv|xlsx|xls|json))"
)

READ_FALLBACK_PATTERN = r"\b([\w()\-][\w().\- ]*\.(?:csv|xlsx|xls|json))\b"

SHEET_PATTERNS = [
    # "sheet EmployeeData", "worksheet named EmployeeData" - a
    # single identifier token right after the keyword.
    r"(?:sheet|worksheet)\s+(?:named\s+|called\s+)?([A-Za-z0-9_]+)\b",
    # "open the EmployeeData sheet" - name comes BEFORE the
    # keyword, again a single identifier token.
    r"\b(?:the\s+)?([A-Za-z0-9_]+)\s+(?:sheet|worksheet)\b",
]

# Words that can end up sitting next to "sheet"/"worksheet" without
# actually being the sheet's name - filler words from the rest of
# the sentence, or leftover filename-extension tokens.
_SHEET_STOPWORDS = {
    "first", "then", "now", "next", "also", "finally",
    "before", "after", "the", "this", "that",
    "excel", "file", "workbook", "spreadsheet",
    "xlsx", "xls", "csv", "json",
}


def _find_sheet_name(prompt):

    for pattern in SHEET_PATTERNS:

        match = re.search(pattern, prompt, re.I)

        if not match:
            continue

        candidate = match.group(1).strip()

        if candidate and candidate.lower() not in _SHEET_STOPWORDS:
            return candidate

    return None

SKIP_ROWS_PATTERN = r"skip\s+(?:the\s+)?(?:first\s+)?(\d+)\s+rows?"

PREVIEW_ROWS_PATTERN = (
    r"(?:show|display|preview|get|read)\s+(?:first|top)\s+"
    r"(\w+)\s+(?:rows|records)"
)


def parse_read(prompt, table=None):

    pipeline = []
    current_table = table if table is not None else resolve_table_name(prompt)

    # -------------------------------------------------
    # FIND FILE
    # -------------------------------------------------

    read_match = re.search(READ_PRIMARY_PATTERN, prompt, re.I)

    # If prompt doesn't start with Read/Open...
    if not read_match:

        read_match = re.search(READ_FALLBACK_PATTERN, prompt, re.I)

        if read_match:

            before = prompt[:read_match.start()].lower()

            if any(word in before for word in ("save", "store", "write", "export")):
                read_match = None

    if not read_match:
        return pipeline

    filename = read_match.group(1).strip()
    ext = filename.split(".")[-1].lower()

    if ext == "xls":
        ext = "xlsx"

    read_op = {
        "id": generate_id(),
        "operation": READ_EXTENSION_OPS[ext],
        "output": current_table,
        "path": filename
    }

    # -------------------------------------------------
    # SHEET NAME (Excel formats only - csv/json have no sheets)
    # -------------------------------------------------

    if ext in ("xlsx", "xls"):
        sheet_name = _find_sheet_name(prompt)
        read_op["sheet_name"] = sheet_name if sheet_name else "Sheet1"

    # -------------------------------------------------
    # SKIP ROWS
    # -------------------------------------------------

    skip_match = re.search(SKIP_ROWS_PATTERN, prompt, re.I)

    if skip_match:
        read_op["skip_rows"] = int(skip_match.group(1))

    # -------------------------------------------------
    # PREVIEW ROWS
    # -------------------------------------------------

    rows_match = re.search(PREVIEW_ROWS_PATTERN, prompt, re.I)

    if rows_match:

        value = rows_match.group(1)

        if value.isdigit():
            read_op["rows"] = int(value)
        elif value.lower() in NUMBER_WORDS:
            read_op["rows"] = NUMBER_WORDS[value.lower()]

        read_op["preview"] = True

    # -------------------------------------------------

    add_step(
        pipeline,
        read_op["operation"],
        position=read_match.start(),
        **{k: v for k, v in read_op.items() if k != "operation"}
    )

    return pipeline


# ============================================================
# COLUMN OPERATIONS (rename, sort, drop, select, combine,
# drop-duplicates, fill-missing)
# ============================================================

FILL_MISSING_PATTERNS = [
    # replace missing salary with 0
    r"replace\s+missing\s+(.+?)(?:\s+values?)?\s+with\s+([^\s]+)",
    # salary blank put 0
    r"(.+?)\s+blank\s+put\s+([^\s]+)",
    # salary blank replace with 0
    r"(.+?)\s+blank\s+replace\s+with\s+([^\s]+)",
    # fill missing salary with 0
    r"fill\s+missing\s+(.+?)\s+with\s+([^\s]+)",
]

_SELECT_STOPWORDS = {
    "then", "also", "now", "get", "and",
    "the", "a", "an", "please", "next"
}


def _build_rename(m, table, prompt):
    return {
        "input": table, "output": table,
        "mapping": {m.group(1).lower(): m.group(2).lower()},
    }


SORT_PATTERN = rf"sort(?:\s+by)?\s+(.+?){NEXT_OP_DEFAULT}"


def _parse_sort_segment(text):
    """Split one sort clause into (column, ascending) pairs, e.g.
    "amount descending and quantity descending" or
    "amount desc, quantity asc" -> [("amount", False), ("quantity", False)]."""

    segments = re.split(r",|\band\b", text)
    pairs = []

    for segment in segments:

        segment = segment.strip()

        if not segment:
            continue

        dir_match = re.search(
            r"\b(ascending|descending|asc|desc)\b", segment, re.I
        )
        direction = dir_match.group(1).lower() if dir_match else "ascending"

        col = re.sub(
            r"\b(ascending|descending|asc|desc|order|by)\b",
            "", segment, flags=re.I,
        ).strip()
        col = normalize_col(col)

        if col:
            pairs.append((col, direction in ("ascending", "asc")))

    return pairs


def parse_sort(prompt, table=None):
    """
    Dedicated sort parser, run once over the whole prompt, instead
    of being routed through the generic single-match COLUMN_RULES
    table. A multi-column sort instruction can arrive from the LLM
    normalizer as more than one separate "Sort ..." line (mirroring
    how multi-column renames get split into multiple "Rename X to
    Y" lines) - e.g.:

        Sort amount descending
        Sort quantity descending

    Every "sort ..." occurrence in the prompt is found and merged,
    in order, into ONE sort_values step. Emitting separate
    sort_values steps instead would be wrong: calling pandas
    sort_values() a second time just re-sorts by the newer key
    alone and throws away the earlier one, rather than doing a
    combined multi-column sort.
    """

    pipeline = []
    current_table = table if table is not None else resolve_table_name(prompt)

    by = []
    ascending = []
    first_start = None

    for match in re.finditer(SORT_PATTERN, prompt, re.I):

        if first_start is None:
            first_start = match.start()

        for col, asc in _parse_sort_segment(match.group(1)):
            if col not in by:
                by.append(col)
                ascending.append(asc)

    if not by:
        return pipeline

    add_step(
        pipeline, "sort_values",
        position=first_start,
        input=current_table, output=current_table,
        by=by, ascending=ascending,
    )

    return pipeline


def _build_drop_columns(m, table, prompt):
    print("DROP_COLUMNS MATCH:", repr(m.group(0)))
    print("COLUMN:", repr(m.group(1)))
    return {"input": table, "output": table, "cols": [m.group(1).strip()]}


def _build_select_columns(m, table, prompt):

    cols_text = m.group(1).lower()

    cols_text = re.sub(r"\bsort\b.*", "", cols_text, flags=re.I)
    cols_text = re.sub(r"\border\b.*", "", cols_text, flags=re.I)

    cols_text = re.sub(
        r"\b(?:greater\s+than|more\s+than|less\s+than|above|below|over|under)\s+\d+\b",
        "", cols_text, flags=re.I,
    )
    cols_text = re.sub(r"[><=!]=?\s*\d+", "", cols_text)

    cols_text = re.sub(
        r"\b(column|columns|whose|where|then|with|having|save|export|write|"
        r"store|download|finally|records|rows|employee|employees|"
        r"ascending|descending|asc|desc|by)\b",
        "", cols_text, flags=re.I,
    )

    cols_text = cols_text.replace(".", " ").replace("(", " ").replace(")", " ")
    cols_text = re.sub(r"\s+", " ", cols_text).strip()

    # Whether the user gave an explicit separator at all. If they
    # did (comma or "and"), each segment between separators is ONE
    # column - possibly multi-word (e.g. "customer name") - and must
    # NOT be split further, or "customer name, amount" turns into
    # four bogus single-word columns instead of two real ones.
    had_separator = bool(re.search(r",|\band\b", cols_text))

    raw_cols = re.split(r",|\band\b", cols_text)

    cols = []

    for col in raw_cols:

        col = col.strip()

        if not col:
            continue

        col = re.sub(r"\d+", "", col).strip()

        if not col:
            continue

        if had_separator:
            # One explicit column per segment - keep multi-word
            # names intact, just drop stray stopwords inside it.
            words = [
                w for w in col.split()
                if w not in _SELECT_STOPWORDS
            ]

            col_name = normalize_col(" ".join(words))

            if col_name and col_name not in cols:
                cols.append(col_name)

        else:
            # No separator at all (e.g. "keep only city
            # department") - the only signal we have is that each
            # word is probably its own column.
            for word in col.split():

                word = normalize_col(word)

                if word and word not in _SELECT_STOPWORDS and word not in cols:
                    cols.append(word)

    if not cols:
        return None

    return {"input": table, "output": table, "cols": cols}


def _build_combine(m, table, prompt):
    col1, col2 = m.group(1).strip(), m.group(2).strip()
    return {
        "input": table, "output": table,
        "columns": [col1, col2],
        "new_column": f"{col1}_{col2}",
    }


def _build_drop_duplicates(m, table, prompt):
    subset = normalize_col(m.group(1).strip(" ,.;:"))
    return {
        "input": table,
        "output": table,
        "subset": [subset],
    }


def _build_fill_missing(m, table, prompt):

    value = strip_quotes(m.group(2).strip(" ,."))

    if value.isdigit():
        value = int(value)
    elif re.fullmatch(r"\d+\.\d+", value):
        value = float(value)

    return {
        "input": table, "output": table,
        "column": normalize_col(m.group(1)),
        "value": value,
    }


COLUMN_RULES = [
    {
        "operation": "rename_columns",
        "mode": "all",
        "patterns": [rf"(?:rename|change)\s+(.+?)\s+(?:to|as|into)\s+(.+?){NEXT_OP_DEFAULT}"],
        "build": _build_rename,
    },
    {
        "operation": "drop_columns",
        "patterns": [r"(?:remove|drop)\s+(?:the\s+)?columns?\s+(.+?)" + NEXT_OP_DEFAULT],
        "build": _build_drop_columns,
    },
    {
        "operation": "select_columns",
        "patterns": [
            r"(?:keep\s+only|keep\s+just|just\s+keep|need\s+only|only\s+need|"
            r"i\s+just\s+need|just\s+need|"
            r"select|retain|include\s+only|show\s+only|display\s+only|"
            r"i\s+want\s+only|only\s+give(?:\s+me)?|give\s+only|"
            r"(?:just\s+)?(?:give|gimme)(?:\s+me)?(?:\s+only)?)\s+(.+?)"
            + NEXT_OP_SELECT
        ],
        "build": _build_select_columns,
    },
    {
        "operation": "combine_columns",
        "patterns": [rf"combine\s+(.+?)\s+and\s+(.+?){NEXT_OP_DEFAULT}"],
        "build": _build_combine,
    },
    {
        "operation": "drop_duplicates",
        "patterns": [
            rf"(?:remove|drop)\s+duplicate(?:s)?(?:\s+rows)?(?:\s+based\s+on|using)?\s+(.+?){NEXT_OP_DUPLICATES}"
        ],
        "build": _build_drop_duplicates,
    },
    {
        "operation": "fill_missing",
        "mode": "all",
        "patterns": FILL_MISSING_PATTERNS,
        "build": _build_fill_missing,
    },
]


def parse_column(prompt, table=DEFAULT_TABLE):
    return run_pattern_rules(prompt, COLUMN_RULES, table)


# ============================================================
# MATH OPERATIONS
# ============================================================

def _build_multiply(m, table, prompt):

    col1, col2 = m.group(1), m.group(2)
    result = f"{col1}_x_{col2}"

    result_match = re.search(r"create\s+new\s+column\s+(\w+)", prompt, re.I)

    if result_match:
        result = result_match.group(1)

    return {
        "input": table, "output": table,
        "col1": col1, "col2": col2, "result": result,
    }


def _build_add_constant(m, table, prompt):
    return {
        "input": table, "output": table,
        "col": m.group(2).strip(), "value": int(m.group(1)),
    }


def _build_subtract_constant(m, table, prompt):
    return {
        "input": table, "output": table,
        "col": m.group(2).strip(), "value": int(m.group(1)),
    }


def _build_add_constant_referential(m, table, prompt):
    # "in the Hours Worked column, add 10 to it" - column name is
    # named up front, the operation refers back to it with "it".
    return {
        "input": table, "output": table,
        "col": m.group(1).strip(), "value": int(m.group(2)),
    }


def _build_subtract_constant_referential(m, table, prompt):
    # "in the Hours Worked column, subtract 10 from it"
    return {
        "input": table, "output": table,
        "col": m.group(1).strip(), "value": int(m.group(2)),
    }


def _build_divide(m, table, prompt):
    col1, col2 = m.group(1), m.group(2)
    return {
        "input": table, "output": table,
        "col1": col1, "col2": col2,
        "result": f"{col1}_per_{col2}",
    }


def _build_aggregate_sum(m, table, prompt):
    return {"input": table, "output": table, "column": m.group(1), "agg": "sum"}


def _build_aggregate_mean(m, table, prompt):
    return {"input": table, "output": table, "column": m.group(1), "agg": "mean"}


def _build_aggregate_max(m, table, prompt):
    return {"input": table, "output": table, "column": m.group(1), "agg": "max"}


def _build_group_aggregate(m, table, prompt):
    return {
        "input": table, "output": table,
        "column": m.group(2), "groupby": m.group(3),
        "agg": AGG_WORD_MAP[m.group(1).lower()],
    }


MATH_RULES = [
    {
        "operation": "multiply_columns",
        "patterns": [rf"multiply\s+(.+?)\s+(?:and|by)\s+(.+?){NEXT_OP_MATH}"],
        "build": _build_multiply,
    },
    {
        # "in the Hours Worked column, add 10 to it" - checked
        # before the generic pattern below so the referential
        # "it" doesn't get treated as a literal column name.
        "operation": "add_constant",
        "patterns": [
            r"in\s+the\s+(.+?)\s+column\s*,?\s*add\s+(\d+)\s+to\s+it"
        ],
        "build": _build_add_constant_referential,
    },
    {
        "operation": "subtract_constant",
        "patterns": [
            r"in\s+the\s+(.+?)\s+column\s*,?\s*subtract\s+(\d+)\s+from\s+it"
        ],
        "build": _build_subtract_constant_referential,
    },
    {
        "operation": "add_constant",
        "patterns": [
            rf"(?:add|increase)\s+(\d+)(?:\s+value)?\s+(?:to|into)"
            rf"(?:\s+the)?\s+(?!it\b)(.+?)(?:\s+column)?{NEXT_OP_MATH}"
        ],
        "build": _build_add_constant,
    },
    {
        "operation": "subtract_constant",
        "patterns": [rf"subtract\s+(\d+)\s+from\s+(?!it\b)(.+?){NEXT_OP_MATH}"],
        "build": _build_subtract_constant,
    },
    {
        "operation": "divide_columns",
        "patterns": [rf"divide\s+(.+?)\s+by\s+(.+?){NEXT_OP_MATH}"],
        "build": _build_divide,
    },
    {
        "operation": "aggregate",
        "patterns": [r"sum\s+of\s+(\w+)"],
        "build": _build_aggregate_sum,
    },
    {
        "operation": "aggregate",
        "patterns": [r"(?:average|mean)\s+(?:of\s+)?(\w+)"],
        "build": _build_aggregate_mean,
    },
    {
        "operation": "aggregate",
        "patterns": [r"max\s+(?:of\s+)?(\w+)"],
        "build": _build_aggregate_max,
    },
    {
        "operation": "aggregate",
        "patterns": [r"(aggregate|sum|total|average|mean|max|min)\s+(\w+)\s+by\s+(\w+)"],
        "build": _build_group_aggregate,
    },
]


def parse_math(prompt, table=DEFAULT_TABLE):
    return run_pattern_rules(prompt, MATH_RULES, table)


# ============================================================
# STRING OPERATIONS
# ============================================================

UPPER_PATTERNS = [
    r"(?:convert|change)\s+(?:the\s+)?(.+?)(?:\s+column)?\s+to\s+uppercase",
    # r"(?:convert|change)\s+(.+?)\s+uppercase(?!\w)",
    r"\b(.+?)\s+(?:convert|change)\s+uppercase\b",
    r"(.+?)\s+should\s+be\s+uppercase",
    r"make\s+(.+?)\s+uppercase",
    r"\buppercase\s+(.+?)(?=\s+(?:lowercase|replace|rename|sort|trim|split|extract|save|export|write|$))",
]

LOWER_PATTERNS = [
    r"(?:convert|change)\s+(\w+)\s+to\s+lowercase",
    r"(?:convert|change)\s+(\w+)\s+lowercase",
    r"\b(\w+)\s+(?:convert|change)\s+lowercase\b",
    r"(\w+)\s+should\s+be\s+lowercase",
    r"make\s+(\w+)\s+lowercase",
    r"\blowercase\s+(\w+)",
]

REPLACE_COLUMN_PATTERN = rf"replace\s+(.+?)\s+with\s+(.+?)\s+in\s+(\w+){NEXT_OP_STRING}"

# Captures the ENTIRE tail of a "replace ..." clause (not just one
# "old with new" pair) - a prompt can list several replacements in
# ONE clause ("replace 'delhi' with 'new delhi', 'mumbai' with
# 'bombay', and 'bangalore' with 'bengaluru'"), and the LLM
# normalizer doesn't reliably split those onto separate lines the
# way it sometimes does for other operations - so a dedicated
# parser below pulls out every pair inside the span, instead of a
# single-pair regex silently dropping every pair after the first.
REPLACE_GLOBAL_SPAN_PATTERN = rf"replace\s+(?!missing\b)(.+?){NEXT_OP_STRING}"

_REPLACE_PAIR_PATTERN = re.compile(
    r"(?P<old>'[^']*'|\"[^\"]*\"|[A-Za-z0-9_]+(?:\s+[A-Za-z0-9_]+){0,2})"
    r"\s+with\s+"
    r"(?P<new>'[^']*'|\"[^\"]*\"|[A-Za-z0-9_]+(?:\s+[A-Za-z0-9_]+){0,2})"
    r"(?=\s*,|\s+and\s+|\s*$)",
    re.I,
)

TRIM_PATTERN = r"trim\s+whitespace(?:\s+from\s+(\w+))?"
SPLIT_PATTERN = r"split\s+(\w+)(?=\s+(?:extract|save|export|uppercase|lowercase|replace|trim|$))"

EXTRACT_PATTERNS = [
    r"extract\s+pattern\s+from\s+(\w+)",
    r"extract\s+email\s+from\s+(\w+)",
    r"extract\s+(\w+)(?=\s+(?:save|export|uppercase|lowercase|replace|split|trim|$))",
]


def _build_case_change(m, table, prompt):
    col = normalize_col(m.group(1))
    return {"input": table, "output": table, "col": col, "output_col": col}


def _build_replace_column(m, table, prompt):

    if m.group(1).lower() == "missing":
        return None

    return {
        "input": table, "output": table,
        "old": strip_quotes(m.group(1).strip()), "new": strip_quotes(m.group(2).strip()),
        "col": normalize_col(m.group(3)),
    }


def parse_replace_global(prompt, table=None):
    """
    Dedicated replace_str parser (non column-specific variant),
    run once over the whole prompt instead of routed through the
    generic single-pair rule table - see REPLACE_GLOBAL_SPAN_PATTERN
    for why.
    """

    pipeline = []
    current_table = table if table is not None else resolve_table_name(prompt)

    for span_match in re.finditer(REPLACE_GLOBAL_SPAN_PATTERN, prompt, re.I):

        span_text = span_match.group(1)

        # Column-specific replaces ("... with ... in city") are
        # fully handled by REPLACE_COLUMN_PATTERN elsewhere - skip
        # this span so it isn't ALSO captured here as a (wrong)
        # global replace missing its column.
        if re.search(r"\bin\s+\w+\s*$", span_text, re.I):
            continue

        for pair_match in _REPLACE_PAIR_PATTERN.finditer(span_text):

            old = strip_quotes(pair_match.group("old").strip())
            new = strip_quotes(pair_match.group("new").strip())

            if not old or not new:
                continue

            add_step(
                pipeline, "replace_str",
                position=span_match.start(),
                input=current_table, output=current_table,
                old=old, new=new,
            )

    return pipeline


def _build_trim(m, table, prompt):

    col = m.group(1)

    if not col:
        return None

    return {"input": table, "output": table, "col": col, "output_col": col}


def _build_split(m, table, prompt):
    return {"input": table, "output": table, "col": m.group(1), "separator": " "}


def _build_extract_pattern(m, table, prompt):
    col = m.group(1)
    return {
        "input": table, "output": table,
        "col": col, "pattern": r"([^@]+)",
        "output_col": f"{col}_pattern",
    }


STRING_RULES = [
    {"operation": "uppercase", "mode": "all", "patterns": UPPER_PATTERNS, "build": _build_case_change},
    {"operation": "lowercase", "mode": "all", "patterns": LOWER_PATTERNS, "build": _build_case_change},
    {"operation": "replace_str", "mode": "all", "patterns": [REPLACE_COLUMN_PATTERN], "build": _build_replace_column},
    {"operation": "trim_whitespace", "patterns": [TRIM_PATTERN], "build": _build_trim},
    {"operation": "split_column", "patterns": [SPLIT_PATTERN], "build": _build_split},
    {"operation": "extract_pattern", "patterns": EXTRACT_PATTERNS, "build": _build_extract_pattern},
]


def parse_string(prompt, table=DEFAULT_TABLE):

    if not isinstance(prompt, str):
        return []

    prompt = prompt.lower().strip()

    try:
        return run_pattern_rules(prompt, STRING_RULES, table)
    except Exception as e:
        print("Parser Error:", str(e))
        return []


# ============================================================
# FILTER
# ============================================================

FILTER_PATTERNS = [
    # Filter salary > 40000 / Filter employment_status != PENDING
    r"filter\s+(\w+)\s*(>=|<=|>|<|==|=|!=)\s*([^\s,]+)",
    # where salary > 40000
    r"where\s+(\w+)\s*(>=|<=|>|<|==|=|!=)\s*([^\s,]+)",
    # Filter employment_status is ACTIVE / equals ACTIVE
    r"(?:filter|where)\s+(\w+)\s+(?:is|equals?|equal\s+to)\s+([^\s,]+)",
    # whose employment_status is ACTIVE (in case "whose" survives
    # normalization instead of being rewritten to "Filter ...")
    r"whose\s+(\w+)\s+is\s+([^\s,]+)",
    # salary greater than 40000
    r"(.+?)\s+(greater than|more than|above|over|exceeds)\s+([^\s,]+)",
    # salary less than 40000
    r"(.+?)\s+(less than|below|under)\s+([^\s,]+)",
]


_NEGATE_OPERATOR = {
    "==": "!=", "!=": "==",
    ">": "<=", "<=": ">",
    "<": ">=", ">=": "<",
}


def _is_negated_filter(prompt, match_start):
    """
    "Filter/keep only/where X is Y" means KEEP rows matching the
    condition. "Remove/delete/exclude rows where X is Y" means the
    OPPOSITE - keep rows that do NOT match. Both phrasings can
    contain the word "where" ("remove rows WHERE status is
    cancelled" vs "filter WHERE status is cancelled"), so the
    keyword a pattern matched on isn't enough by itself - look at
    which verb actually introduced this clause: whichever of
    remove/delete/exclude vs keep/filter/select/retain appears
    LAST (closest to the match) in the text just before it.
    """

    window = prompt[max(0, match_start - 60):match_start].lower()

    def _last_of(words):
        positions = [window.rfind(w) for w in words]
        positions = [p for p in positions if p != -1]
        return max(positions) if positions else -1

    last_negate = _last_of(("remove", "delete", "exclude"))
    last_keep = _last_of(("keep", "filter", "select", "retain"))

    return last_negate != -1 and last_negate > last_keep


def _build_filter(m, table, prompt):

    # The "is"/"whose ... is" patterns have only 2 groups (column,
    # value) - the operator is implied ("=="), not captured.
    if m.lastindex == 2:
        operator = "=="
        raw_value = m.group(2)
    else:
        operator = FILTER_OPERATOR_MAP.get(m.group(2).lower(), m.group(2))
        raw_value = m.group(3)

    if _is_negated_filter(prompt, m.start()):
        operator = _NEGATE_OPERATOR.get(operator, operator)

    value = strip_quotes(raw_value.strip(" ,.;:"))

    if value.isdigit():
        value = int(value)
    elif re.fullmatch(r"\d+\.\d+", value):
        value = float(value)

    return {
        "input": table, "output": table,
        "column": normalize_col(m.group(1)), "operator": operator,
        "value": value,
    }


FILTER_RULES = [
    {
        "operation": "filter_rows",
        "mode": "all",
        "patterns": FILTER_PATTERNS,
        "build": _build_filter,
    },
]


def parse_filter(prompt, table=DEFAULT_TABLE):
    # NOTE: do NOT lowercase the whole prompt here (as before) - by
    # the time filter_rows runs, an earlier uppercase/lowercase
    # step may already have changed the real column's casing (e.g.
    # employment_status -> "ACTIVE"), so the literal captured here
    # must keep its original case to match. re.I on the patterns
    # already makes the *keyword* matching case-insensitive.
    return run_pattern_rules(prompt, FILTER_RULES, table)


# ============================================================
# EXPORT
# ============================================================

EXPORT_WITH_EXT_PATTERN = (
    r"(?:save|store|write|export)"
    r".*?"
    r"([A-Za-z0-9_.-]+\.(?:csv|xlsx|xls|json|html))"
)

EXPORT_AS_NAME_PATTERN = (
    r"(?:save|store|write|export)"
    r"(?:\s+the)?"
    r"(?:\s+final)?"
    r"(?:\s+output)?"
    r"(?:\s+dataframe)?"
    r"\s+as\s+([A-Za-z0-9_-]+)"
)

EXPORT_BARE_NAME_PATTERN = r"(?:save|store|write|export)\s+([A-Za-z0-9_-]+)"


def parse_export(prompt, table=None):

    pipeline = []
    current_table = table if table is not None else resolve_table_name(prompt)

    # Filename WITH extension.
    export_match = re.search(EXPORT_WITH_EXT_PATTERN, prompt, re.I)

    # Filename WITHOUT extension.
    # Case 1: "save the final output as result"
    if not export_match:
        export_match = re.search(EXPORT_AS_NAME_PATTERN, prompt, re.I)

    # Case 2: "save result"
    if not export_match:
        export_match = re.search(EXPORT_BARE_NAME_PATTERN, prompt, re.I)

    if not export_match:
        return pipeline

    filename = export_match.group(1).strip().strip("\"'")

    if "." not in filename:
        filename += ".csv"

    ext = filename.rsplit(".", 1)[1].lower()
    operation = EXPORT_EXTENSION_OPS.get(ext)

    if operation:
        add_step(
            pipeline,
            operation,
            position=export_match.start(),
            input=current_table,
            path=filename,
        )

    return pipeline


# ============================================================
# TRANSFORM / REINDEX / HEADER / DROP-ROWS / PIVOT
# ============================================================

def _build_transpose(m, table, prompt):
    return {"input": table, "output": table}


TRANSFORM_RULES = [
    {"operation": "transpose", "patterns": [r"transpose\s+(?:data|table)?"], "build": _build_transpose},
]


def parse_transform(prompt, table=DEFAULT_TABLE):
    return run_pattern_rules(prompt, TRANSFORM_RULES, table)


def _build_reindex(m, table, prompt):
    return {"input": table, "output": table}


REINDEX_RULES = [
    {"operation": "reindex_columns", "patterns": [r"reindex\s+columns"], "build": _build_reindex},
]


def parse_reindex(prompt, table=DEFAULT_TABLE):
    return run_pattern_rules(prompt, REINDEX_RULES, table)


def _build_use_row_as_header(m, table, prompt):
    return {"input": table, "output": table, "row": int(m.group(1))}


HEADER_RULES = [
    {
        "operation": "use_row_as_header",
        "patterns": [r"use\s+row\s+(\d+)\s+as\s+header"],
        "build": _build_use_row_as_header,
    },
]


def parse_use_row_as_header(prompt, table=DEFAULT_TABLE):
    return run_pattern_rules(prompt, HEADER_RULES, table)


def _build_drop_rows(m, table, prompt):

    # The "range" pattern has 2 groups, the "single list" pattern
    # has 1 - use that to tell which one matched instead of two
    # separate mutually-unaware code paths.
    if m.lastindex == 2:
        start, end = int(m.group(1)), int(m.group(2))
        return {"input": table, "output": table, "rows": list(range(start, end + 1))}

    rows = [int(x.strip()) for x in m.group(1).split(",") if x.strip()]

    return {"input": table, "output": table, "rows": rows}


DROP_ROWS_RULES = [
    {
        "operation": "drop_rows_by_index",
        "patterns": [
            r"drop\s+rows?\s+(\d+)\s+to\s+(\d+)",
            r"drop\s+rows?\s+([\d,\s]+)",
        ],
        "build": _build_drop_rows,
    },
]


def parse_drop_rows(prompt, table=DEFAULT_TABLE):
    return run_pattern_rules(prompt, DROP_ROWS_RULES, table)


def _build_pivot(m, table, prompt):

    index_col = m.group(1)

    # values column: use whatever the user named; if they didn't
    # name one, fall back to the index column itself rather than
    # guessing an unrelated business field.
    values_col = m.group(2) or index_col
    aggfunc = AGG_WORD_MAP.get((m.group(3) or "sum").lower(), "sum")

    return {
        "input": table, "output": table,
        "index": index_col, "values": values_col, "aggfunc": aggfunc,
    }


PIVOT_RULES = [
    {
        "operation": "pivot_table",
        "patterns": [
            r"pivot\s+table\s+by\s+(\w+)"
            r"(?:\s+values?\s+(\w+))?"
            r"(?:\s+(?:aggfunc|using|agg)\s+(\w+))?"
        ],
        "build": _build_pivot,
    },
]


def parse_pivot(prompt, table=DEFAULT_TABLE):
    return run_pattern_rules(prompt, PIVOT_RULES, table)


# ============================================================
# DATE OPERATIONS
# ============================================================

def _build_extract_date_parts(m, table, prompt):
    return {"input": table, "output": table, "column": m.group(1)}


def _build_add_days(m, table, prompt):
    return {"input": table, "output": table, "column": m.group(2), "days": int(m.group(1))}


def _build_subtract_days(m, table, prompt):
    return {"input": table, "output": table, "column": m.group(2), "days": int(m.group(1))}


def _build_format_date(m, table, prompt):
    date_col = m.group(1) or m.group(2) or m.group(3)
    return {"input": table, "output": table, "column": date_col}


def _build_date_diff(m, table, prompt):
    result_col = m.group(3) or "days_difference"
    return {
        "input": table, "output": table,
        "start_col": m.group(1), "end_col": m.group(2),
        "result": result_col,
    }


DATE_RULES = [
    {
        "operation": "extract_date_parts",
        "patterns": [rf"extract\s+date\s+parts\s+from\s+(.+?){NEXT_OP_DEFAULT}"],
        "build": _build_extract_date_parts,
    },
    {
        "operation": "add_days",
        "patterns": [r"add\s+(\d+)\s+days?\s+to\s+(\w+)"],
        "build": _build_add_days,
    },
    {
        "operation": "subtract_days",
        "patterns": [r"subtract\s+(\d+)\s+days?\s+from\s+(\w+)"],
        "build": _build_subtract_days,
    },
    {
        "operation": "format_date",
        "patterns": [r"format\s+(?:date\s+column\s+(\w+)|(\w+)\s+as\s+date|(\w+)\s+date\s+column)"],
        "build": _build_format_date,
    },
    {
        "operation": "date_diff",
        # Supports:
        # date difference between start and end
        # date difference between start and end as/into/called/named delivery_days
        "patterns": [
            r"""
            date\s+difference\s+between\s+
            (\w+)\s+
            and\s+
            (\w+)
            (?:\s+
                (?:as|into|called|named)
                \s+
                (\w+)
            )?
            """
        ],
        "flags": re.I | re.X,
        "build": _build_date_diff,
    },
]


def parse_date(prompt, table=DEFAULT_TABLE):
    return run_pattern_rules(prompt, DATE_RULES, table)


# ============================================================
# SQL / DATABASE
# ============================================================

def _build_write_sql(m, table, prompt):

    sql_table = m.group(1)

    if not sql_table:
        # No table name given - fall back to the source filename
        # (e.g. "sales.xlsx" -> "sales") rather than guessing an
        # unrelated business table name.
        file_match = re.search(r"([\w\-]+)\.(csv|xlsx|json)", prompt, re.I)
        sql_table = file_match.group(1) if file_match else "output_table"

    return {
        "input": table, "output": table,
        "connection": "sqlite:///database.db",
        "table": sql_table,
    }


SQL_RULES = [
    {
        "operation": "write_sql",
        "patterns": [r"write\s+to\s+sql(?:\s+table\s+(\w+))?"],
        "build": _build_write_sql,
    },
]


def parse_sql(prompt, table=DEFAULT_TABLE):
    return run_pattern_rules(prompt, SQL_RULES, table)


def _build_read_database(m, table, prompt):
    return {"output": table, "table": m.group(1) or "source_table"}


READ_DB_RULES = [
    {
        "operation": "read_database",
        "patterns": [r"read\s+database(?:\s+table\s+(\w+))?"],
        "build": _build_read_database,
    },
]


def parse_read_database(prompt, table=DEFAULT_TABLE):
    return run_pattern_rules(prompt, READ_DB_RULES, table)


# ============================================================
# PIPELINE POST-PROCESSING (unchanged logic; already config/data
# driven via the PRIORITY / _OP_COLUMN_SPEC tables)
# ============================================================

def validate_pipeline(pipeline):

    if not pipeline:
        return "No valid operations found!"

    read_ops = {
        "read_csv",
        "read_excel_any",
        "read_json",
        "read_database"
    }

    has_read = any(
        step["operation"] in read_ops
        for step in pipeline
    )

    if not has_read:
        return "Please specify an input source."

    return None


def remove_duplicate_steps(pipeline):

    unique = []
    seen = set()

    for step in pipeline:

        key = (
            step["operation"],
            str(step)
        )

        if key not in seen:
            seen.add(key)
            unique.append(step)

    return unique


def reorder_pipeline(pipeline):

    PRIORITY = {

        # READ
        "read_csv": 1,
        "read_excel_any": 1,
        "read_database": 1,

        # CLEANING
        "drop_duplicates": 5,
        "fill_missing": 6,

        # FILTER
        "filter_rows": 48,

        # RENAME
        "rename_columns": 20,

        # STRING
        "uppercase": 25,
        "lowercase": 26,
        "replace_str": 27,
        "trim_whitespace": 28,
        "split_column": 29,
        "extract_pattern": 30,

        # MATH
        "add_constant": 35,
        "subtract_constant": 36,
        "multiply_columns": 37,
        "divide_columns": 38,

        # DATE - must run BEFORE select_columns/drop_columns, since
        # these read source columns (e.g. admitdate, dischargedate)
        # that the user's final column selection may not keep.
        "extract_date_parts": 39,
        "add_days": 40,
        "subtract_days": 41,
        "format_date": 42,
        "date_diff": 43,

        # COLUMN - runs AFTER all derived-value computations above,
        # so it's safe to narrow down to just the requested output
        # columns without breaking a later step that needed the
        # original source columns.
        "combine_columns": 44,
        "add_column": 45,
        "drop_columns": 46,
        "select_columns": 50,

        # SORT
        "sort_values": 49,

        # OTHER
        "transpose": 80,
        "pivot_table": 81,
        "reindex_columns": 82,
        "use_row_as_header": 83,
        "drop_rows_by_index": 84,

        # DATABASE
        "write_sql": 98,

        # EXPORT
        "write_csv": 100,
        "to_json": 101,
        "to_html": 102
    }

    return sorted(
        pipeline,
        key=lambda step: PRIORITY.get(
            step["operation"],
            999
        )
    )


def _step_requires_and_produces(step):
    """
    Return (requires, produces) sets of column names for a step,
    reusing the same operation spec used for column resolution
    (_OP_COLUMN_SPEC) so this logic never drifts out of sync with it.
    """

    op = step.get("operation")
    requires = set()
    produces = set()

    if op == "rename_columns" and "mapping" in step:
        for old, new in step["mapping"].items():
            if isinstance(old, str):
                requires.add(old)
            if isinstance(new, str):
                produces.add(new)
        return requires, produces

    spec = _OP_COLUMN_SPEC.get(op)

    if not spec:
        return requires, produces

    for key in spec.get("resolve", []):
        val = step.get(key)
        if isinstance(val, str):
            requires.add(val)

    for key in spec.get("resolve_list", []):
        val = step.get(key)
        if isinstance(val, list):
            requires.update(v for v in val if isinstance(v, str))

    for key in spec.get("define", []):
        val = step.get(key)
        if isinstance(val, str):
            produces.add(val)

    return requires, produces


def enforce_dependency_order(pipeline):
    """
    Move any step that depends on a column created later.
    Export operations are always kept at the end.
    """

    EXPORT_OPS = {
        "write_csv",
        "write_sql",
        "to_json",
        "to_html"
    }

    changed = True

    while changed:

        changed = False

        for i in range(len(pipeline)):

            step = pipeline[i]

            requires, _ = _step_requires_and_produces(step)

            if not requires:
                continue

            producer = None

            for j in range(i + 1, len(pipeline)):

                _, produces = _step_requires_and_produces(pipeline[j])

                if requires.intersection(produces):
                    producer = j

            if producer is not None:

                item = pipeline.pop(i)

                if producer > i:
                    producer -= 1

                pipeline.insert(producer + 1, item)

                changed = True
                break

    exports = [
        s for s in pipeline
        if s.get("operation") in EXPORT_OPS
    ]

    others = [
        s for s in pipeline
        if s.get("operation") not in EXPORT_OPS
    ]

    return others + exports


# ============================================================
# TOP-LEVEL DRIVERS
# ============================================================

# name -> parser function. Adding a whole new *family* of
# operations means adding one entry here (and a RULES table +
# parse_* function above) - build_regex_pipeline itself never
# needs to change.
PARSERS = [
    ("read", parse_read),
    ("column", parse_column),
    ("sort", parse_sort),
    ("replace", parse_replace_global),
    ("math", parse_math),
    ("string", parse_string),
    ("filter", parse_filter),
    ("transform", parse_transform),
    ("pivot", parse_pivot),
    ("reindex", parse_reindex),
    ("header", parse_use_row_as_header),
    ("drop", parse_drop_rows),
    ("date", parse_date),
    ("sql", parse_sql),
    ("database", parse_read_database),
    ("export", parse_export),
]


def build_regex_pipeline(prompt):

    # Resolve the dataframe/table name ONCE per prompt and hand it
    # to every parser, instead of each one hardcoding "dataframe".
    table = resolve_table_name(prompt)

    pipeline = []

    for name, parser in PARSERS:
        try:
            steps = parser(prompt, table)
        except Exception as e:
            # One parser family failing on an unusual phrasing must
            # not cost the user every OTHER operation in their
            # prompt too - log it and keep going with the rest.
            print(f"parser: '{name}' parser failed on this prompt -> {e}")
            steps = []
        pipeline.extend(steps)

    return pipeline


def generate_pipeline(prompt, file_path=None):

    try:
        normalized_prompt = normalize_prompt(prompt)
    except Exception as e:
        print("LLM Error:", e)
        normalized_prompt = prompt

    # Build pipeline (ALWAYS)
    pipeline = build_regex_pipeline(normalized_prompt)

    # Remove duplicate steps
    pipeline = remove_duplicate_steps(pipeline)

    pipeline.sort(key=lambda step: step.get("__pos", 999999))
    # pipeline = reorder_pipeline(pipeline)
    pipeline = enforce_dependency_order(pipeline)

    for step in pipeline:
        step.pop("__pos", None)

    # Resolve/correct column references against the REAL uploaded
    # file's headers, whatever the schema is. If no file is
    # available or reading fails, this is a safe no-op - it never
    # raises, so the user never sees an error from this step.
    if file_path:
        pipeline = remap_pipeline_columns(pipeline, file_path)

    error = validate_pipeline(pipeline)

    if error:
        return json.dumps(
            {
                "error": error
            },
            indent=4
        )

    os.makedirs("generated", exist_ok=True)

    with open(
        "generated/pipeline.json",
        "w"
    ) as file:

        json.dump(
            pipeline,
            file,
            indent=4
        )

    return json.dumps(
        pipeline,
        indent=4
    )