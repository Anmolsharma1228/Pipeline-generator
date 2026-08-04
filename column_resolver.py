"""
column_resolver.py

Makes the pipeline schema-agnostic.

Instead of trusting a hardcoded list of column names (fullname, city,
department, salary...), this module:

  1. Reads the ACTUAL column headers from whatever file the user
     uploaded (csv / xlsx / json) - any schema, any domain.
  2. Fuzzy-matches whatever text the regex parser pulled out of the
     prompt ("full name", "Emp Name", "customer_email") against
     those real headers.
  3. Tracks columns the PIPELINE ITSELF creates along the way
     (renames, add_column, combine_columns, extract_pattern...) so a
     brand-new column name is never wrongly fuzzy-matched back to an
     original header just because it looks similar.
  4. Never raises - if a file can't be read or nothing matches
     closely enough, it returns the original text untouched so the
     pipeline still builds instead of erroring out.
"""

import difflib
import os

import pandas as pd


def read_actual_columns(file_path):
    """
    Return the real list of column headers for a csv/xlsx/json file.
    Returns [] (never raises) if the file can't be read - callers
    should treat that as "no schema info available yet" and fall
    back to whatever text the user typed.
    """

    if not file_path or not os.path.exists(file_path):
        return []

    try:
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".csv":
            df = pd.read_csv(file_path, nrows=0)

        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(file_path, nrows=0)

        elif ext == ".json":
            df = pd.read_json(file_path)

        else:
            return []

        return list(df.columns)

    except Exception as e:
        print("column_resolver: could not read columns ->", e)
        return []


def _normalize(text):
    """Loose normalization so 'Full Name', 'full_name', 'FullName'
    all compare equal."""

    return (
        str(text)
        .strip()
        .lower()
        .replace("-", " ")
        .replace("_", " ")
        .replace(" ", "")
    )


# Per-operation spec of which keys reference an EXISTING column
# (safe to fuzzy-resolve against the real file headers) vs which
# keys DEFINE a brand-new column the pipeline itself is creating
# (must never be fuzzy-matched - only registered so later steps can
# reference it correctly).
_OP_COLUMN_SPEC = {
    "select_columns":     {"resolve_list": ["cols"]},
    "drop_columns":       {"resolve_list": ["cols"]},
    "drop_duplicates":    {"resolve_list": ["subset"]},
    "sort_values":        {"resolve": ["by"]},
    "filter_rows":        {"resolve": ["column"]},
    "fill_missing":       {"resolve": ["column"]},
    "uppercase":          {"resolve": ["col"], "mirror": [("col", "output_col")]},
    "lowercase":          {"resolve": ["col"], "mirror": [("col", "output_col")]},
    "trim_whitespace":    {"resolve": ["col"], "mirror": [("col", "output_col")]},
    "split_column":       {"resolve": ["col"]},
    "extract_pattern":    {"resolve": ["col"], "define": ["output_col"]},
    "replace_str":        {"resolve": ["col"]},
    "add_column":         {"define": ["column"]},
    "combine_columns":    {"resolve_list": ["columns"], "define": ["new_column"]},
    "multiply_columns":   {"resolve": ["col1", "col2"], "define": ["result"]},
    "divide_columns":     {"resolve": ["col1", "col2"], "define": ["result"]},
    "add_constant":       {"resolve": ["col"]},
    "subtract_constant":  {"resolve": ["col"]},
    "aggregate":          {"resolve": ["column", "groupby"]},
    "pivot_table":        {"resolve": ["index"]},
    "extract_date_parts": {"resolve": ["column"]},
    "add_days":           {"resolve": ["column"]},
    "subtract_days":      {"resolve": ["column"]},
    "format_date":        {"resolve": ["column"]},
    "date_diff":          {"resolve": ["start_col", "end_col"], "define": ["result"]},
    # rename_columns is handled specially below (mapping dict).
}


class ColumnResolver:
    """Resolves column-name text against a file's real headers,
    while tracking any new columns the pipeline creates so later
    steps referencing them resolve correctly too."""

    def __init__(self, actual_columns, cutoff=0.6):
        self.cutoff = cutoff
        # normalized -> canonical display name currently "known"
        self.known = {_normalize(c): c for c in actual_columns}

    def resolve(self, name):
        if not name or not isinstance(name, str):
            return name

        norm = _normalize(name)

        if norm in self.known:
            return self.known[norm]

        close = difflib.get_close_matches(
            norm, list(self.known.keys()), n=1, cutoff=self.cutoff
        )

        if close:
            return self.known[close[0]]

        # Nothing close enough - leave as-is rather than error out.
        return name

    def register(self, name):
        """Record a column the pipeline itself just created, so
        later steps referencing it resolve to the exact same name
        instead of being fuzzy-matched elsewhere."""

        if name and isinstance(name, str):
            self.known[_normalize(name)] = name


def remap_pipeline_columns(pipeline, file_path):
    """
    Walk every step in the pipeline (IN ORDER) and correct column-name
    references against the real headers of `file_path`, while
    tracking columns the pipeline creates along the way. Safe to call
    even if the file can't be read - it just becomes a no-op.
    """

    actual_columns = read_actual_columns(file_path)

    if not actual_columns:
        # No schema info available - leave the pipeline exactly as-is.
        return pipeline

    resolver = ColumnResolver(actual_columns)

    for step in pipeline:

        try:
            op = step.get("operation")

            # rename_columns: {"mapping": {old: new}}
            # old = existing column (resolve), new = brand new name
            # (register only, never resolve).
            if op == "rename_columns" and "mapping" in step:
                new_mapping = {}
                for old, new in step["mapping"].items():
                    resolved_old = resolver.resolve(old)
                    new_mapping[resolved_old] = new
                    resolver.register(new)
                step["mapping"] = new_mapping
                continue

            spec = _OP_COLUMN_SPEC.get(op)
            if not spec:
                continue

            for key in spec.get("resolve", []):
                if key in step and isinstance(step[key], str):
                    step[key] = resolver.resolve(step[key])

            for key in spec.get("resolve_list", []):
                if key in step and isinstance(step[key], list):
                    step[key] = [resolver.resolve(c) for c in step[key]]

            for key in spec.get("define", []):
                if key in step and isinstance(step[key], str):
                    resolver.register(step[key])

            for src_key, mirror_key in spec.get("mirror", []):
                if src_key in step and mirror_key in step:
                    step[mirror_key] = step[src_key]

        except Exception as e:
            # Never let a remap issue break the whole pipeline.
            print("column_resolver: skipped remap for step ->", e)
            continue

    return pipeline