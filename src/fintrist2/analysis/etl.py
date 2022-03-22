"""Utility functions for analysis."""
import pandas as pd

def sanitize_col(df, col):
    """"""
    if isinstance(col, str) and isinstance(df, pd.DataFrame):
        return df[col]
    elif isinstance(col, pd.Series) or isinstance(col, pd.Index):
        return col
    else:
        raise TypeError(f"""Column should be str label or Series. \nReceived {col}""")

def sanitize_cols(df, *args):
    cols = [sanitize_col(df, col) for col in args]
    if len(cols) == 1:
        cols = cols[0]
    return cols
