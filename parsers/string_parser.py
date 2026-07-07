import re
from parsers.read_parser import generate_id


def add_step(pipeline, operation, **kwargs):

    step = {
        "id": generate_id(),
        "operation": operation
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

    COLUMN_MAP = {

        "employee": "fullname",
        "employees": "fullname",

        "name": "fullname",
        "names": "fullname",

        "city": "city",
        "cities": "city",

        "emails": "email"
    }

    return COLUMN_MAP.get(
        col.strip(),
        col.strip()
    )


def parse_string(prompt):

    pipeline = []

    if not isinstance(prompt, str):
        return pipeline

    prompt = prompt.lower().strip()

    try:

        # ==========================
        # UPPERCASE
        # ==========================

        upper = find_match(
                    prompt,
        [

            r"(?:convert|change)\s+([\w\s]+?)(?:\s+to)?\s+uppercase\b",
            r"make\s+([\w\s]+?)\s+uppercase\b",
            r"uppercase\s+([\w\s]+)\b"

        ]
    )

        if upper:

            col = normalize_col(
                upper.group(1)
            )

            add_step(
                pipeline,
                "uppercase",
                col=col,
                output_col=col
            )

        # ==========================
        # LOWERCASE
        # ==========================

        lower = find_match(
                     prompt,
    [
        r"(?:convert|change)\s+([\w\s]+?)(?:\s+to)?\s+lowercase\b",
        r"make\s+([\w\s]+?)\s+lowercase\b",
        r"lowercase\s+([\w\s]+)\b"
    ]
)

        if lower:

            col = normalize_col(
                lower.group(1)
            )

            add_step(
                pipeline,
                "lowercase",
                col=col,
                output_col=col
            )

        # ==========================
        # REPLACE
        # ==========================

        replace_matches = re.finditer(
            r"replace\s+(\w+)\s+with\s+(\w+)",
            prompt,
            re.I
        )

        for match in replace_matches:

            add_step(
                pipeline,
                "replace_str",
                old=match.group(1).strip(),
                new=match.group(2).strip()
            )

        # ==========================
        # TRIM
        # ==========================

        trim = re.search(
            r"trim\s+whitespace(?:\s+from\s+(\w+))?",
            prompt,
            re.I
        )

        if trim:

            col = trim.group(1)

            if col:

                add_step(
                    pipeline,
                    "trim_whitespace",
                    col=col,
                    output_col=col
                )

        # ==========================
        # SPLIT
        # ==========================

        split = re.search(
            r"split\s+(\w+)(?:\s+column)?",
            prompt,
            re.I
        )

        if split:

            add_step(
                pipeline,
                "split_column",
                col=split.group(1),
                separator=" "
            )

        # ==========================
        # EXTRACT
        # ==========================

        extract = find_match(
            prompt,
            [

                r"extract\s+pattern\s+from\s+(\w+)",

                r"extract\s+email\s+from\s+(\w+)",

                r"extract\s+(\w+)"

            ]
        )

        if extract:

            col = extract.group(1)

            add_step(
                pipeline,
                "extract_pattern",
                col=col,
                pattern=r"([^@]+)",
                output_col=f"{col}_pattern"
            )

    except Exception as e:

        print(
            "Parser Error:",
            str(e)
        )

        return []

    return pipeline