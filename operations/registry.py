from operations.file_ops import *
from operations.column_ops import *
from operations.math_ops import *
from operations.string_ops import *
from operations.filter_ops import *
from operations.transform_ops import *
from operations.reindex_ops import *
from operations.drop_ops import *
from operations.header_ops import use_row_as_header
from operations.column_ops import *
from operations.pivot_ops import pivot_table_op
from operations.date_ops import *
from operations.date_ops import add_days
from operations.sql_ops import *

OPERATIONS={

"read_excel_any":
read_excel_any,

"read_csv":
read_csv,

"write_csv":
write_csv,

"to_json":
to_json,

"to_html":
to_html,

"add_column":
add_column,

# MATH

"add_constant":
add_constant,


"multiply_columns":
multiply_columns,

"rename_columns":
rename_columns,

"sort_values":
sort_values,

"drop_columns":
drop_columns,

"select_columns":
select_columns,

"combine_columns":
combine_columns,

"subtract_constant":
subtract_constant,

"divide_columns":
divide_columns,

"aggregate":
aggregate,


# STRING
"uppercase":
uppercase,

"lowercase":
lowercase,

"replace_str":
replace_str,

"trim_whitespace":
trim_whitespace,

"split_column":
split_column,

"extract_pattern":
extract_pattern,

# FILTER
"filter_rows":
filter_rows,

# TRANSFORM
"transpose":
transpose,

"pivot_table":
 pivot_table_op,

# REINDEX
"reindex_columns":
reindex_columns,

# DROP
"drop_rows_by_index":
drop_rows_by_index,

"combine_columns":
 combine_columns,

"use_row_as_header": 
use_row_as_header,

# DATE
"extract_date_parts":
extract_date_parts,

"add_days":
add_days,

"subtract_days":
subtract_days,

"format_date":
format_date,

"date_diff":
date_diff,


# SQL
"write_sql":
write_sql,

"read_database":
read_database,

}
