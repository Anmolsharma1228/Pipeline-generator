import re
import time
import random


def generate_id():

    return int(
        f"{int(time.time()*1000)}{random.randint(10,99)}"
    )


def parse_read(prompt):

    pipeline = []
    current_table = "dataframe"
    number_words = {

        "one": 1,
        "two": 2,
        "three": 3,
        "five": 5,
        "ten": 10,
        "twenty": 20,
        "fifty": 50

    }

    read_match = re.search(
        r"([\w\-.]+\.(csv|xlsx|json))",
        prompt,
        re.I
    )

    if read_match:

        read_op = {

            "id": generate_id(),

            "operation": {

                "csv": "read_csv",
                "xlsx": "read_excel_any",
                "json": "read_json"

            }[
                read_match.group(2)
            ],

            "output": current_table,

            "path": read_match.group(1)

        }

        # ==========================
        # SHEET SUPPORT
        # ==========================

        sheet_match = re.search(
            r"(?:from\s+)?(sheet\s*\d+)",
            prompt,
            re.I
        )

        if sheet_match:

            read_op["sheet_name"] = (
                sheet_match
                .group(1)
                .replace(" ", "")
                .title()
            )

        # ==========================
        # ROW PREVIEW
        # ==========================

        rows_match = re.search(
            r"(?:first|top)\s+(\w+)\s+(?:rows|records)",
            prompt,
            re.I
        )

        if rows_match:

            value = rows_match.group(1)

            if value.isdigit():

                read_op["rows"] = int(value)

            elif value.lower() in number_words:

                read_op["rows"] = number_words[
                    value.lower()
                ]

            read_op["preview"] = True

        pipeline.append(
            read_op
        )

    return pipeline