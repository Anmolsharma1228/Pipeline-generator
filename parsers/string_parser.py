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

   
    "employee":"fullname",
    "employees":"fullname",

    "name":"fullname",
    "names":"fullname",

    "full name":"fullname",
    "employee name":"fullname",

    "city":"city",
    "cities":"city",

    "mail":"email",
    "mails":"email",

    "email":"email",
    "emails":"email",

    "dept":"department",
    "team":"department",
    "department":"department",

    "salary":"salary"

}

    return COLUMN_MAP.get(
        col.strip(),
        col.strip()
    )

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


def parse_string(prompt):

    pipeline = []

    if not isinstance(prompt, str):
        return pipeline
    
    
    prompt = prompt.lower().strip()

    try:

        # ==========================
        # UPPERCASE
        # ==========================

        upper_patterns = [
            r"(?:convert|change)\s+(\w+)\s+to\s+uppercase",
            r"make\s+(\w+)\s+uppercase",
            r"\buppercase\s+(\w+)"
        ]

        for pattern in upper_patterns:

            for match in re.finditer(pattern, prompt, re.I):

                col = normalize_col(match.group(1))

                add_step(
                    pipeline,
                    "uppercase",
                    col=col,
                    output_col=col
                )

        # ==========================
        # LOWERCASE
        # ==========================

        lower_patterns = [
            r"(?:convert|change)\s+(\w+)\s+to\s+lowercase",
            r"make\s+(\w+)\s+lowercase",
            r"\blowercase\s+(\w+)"
        ]

        for pattern in lower_patterns:

            for match in re.finditer(pattern, prompt, re.I):

                col = normalize_col(match.group(1))

                add_step(
                    pipeline,
                    "lowercase",
                    col=col,
                    output_col=col
                )
                  
                  
        # ==========================
        # REPLACE
        # ==========================

        # Column specific replacement
        for match in re.finditer(
            r"replace\s+(\S+)\s+with\s+(\S+)\s+in\s+(\w+)",
            prompt,
            re.I
        ):

            # Ignore "replace missing salary..."
            if match.group(1).lower() == "missing":
                continue

            add_step(
                pipeline,
                "replace_str",
                old=match.group(1).strip(),
                new=match.group(2).strip(),
                col=normalize_col(match.group(3))
            )


        # Global replacement
        for match in re.finditer(
            r"replace\s+(?!missing\b)(\S+)\s+with\s+(\S+)",
            prompt,
            re.I
        ):

            # Skip if already parsed as column replacement
            if re.search(
                rf"replace\s+{re.escape(match.group(1))}\s+with\s+{re.escape(match.group(2))}\s+in\s+\w+",
                prompt,
                re.I
            ):
                continue

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
            r"split\s+(\w+)(?=\s+(?:extract|save|export|uppercase|lowercase|replace|trim|$))",
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
               r"extract\s+(\w+)(?=\s+(?:save|export|uppercase|lowercase|replace|split|trim|$))"
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