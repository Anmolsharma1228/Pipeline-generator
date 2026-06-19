from operations.file_ops import *
from operations.column_ops import *
from operations.math_ops import *


OPERATIONS={

"read_excel_any":
read_excel_any,

"read_csv":
read_csv,

"write_csv":
write_csv,

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

"subtract_constant":
subtract_constant,
}