OPERATIONS = {

    "read csv": {
        "operation": "read_csv",
        "output": "employees",
        "path": "employees.csv"
    },

    "uppercase": {
        "operation": "uppercase",
        "input": "employees",
        "output": "employees",
        "col": "name",
        "output_col": "name_upper"
    },

    "lowercase": {
        "operation": "lowercase",
        "input": "employees",
        "output": "employees",
        "col": "department",
        "output_col": "department_lower"
    },

    "export csv": {
        "operation": "write_csv",
        "input": "employees",
        "path": "output.csv"
    },

    "to json": {
        "operation": "to_json",
        "input": "employees",
        "path": "employees.json"
    },

    "html": {
        "operation": "to_html",
        "input": "employees",
        "path": "employees.html"
    },

    "filter salary": {
        "operation": "filter_rows",
        "input": "employees",
        "output": "filtered_data",
        "condition": "salary > 50000"
    }

}