from typing import List, Tuple, Union

import regex as re

from .data_classes import Table


def is_table_header(line: str) -> bool:
    """Determines if the line is a PCPP table header.

    Args:
        line: A line from the post/submission.

    Returns:
        True if it is, False otherwise.
    """

    header = r"\W*type\W*\|\W*item\W*\|\W*price\W*"

    m = re.search(header, line.lower())

    return m is not None


def is_column_alignments(line: str) -> bool:
    """Determines if the line is a table's column alignments.

    :----, :----:, ----: with varying - amounts.

    Args:
        line: A line from the post/submission.

    Returns:
        True if it is, False otherwise.
    """

    line = line.strip()
    alignment_pattern = r'(\|?:\-+:?)|(\|?\-+:)'
    matches = re.search(alignment_pattern, line)

    return matches is not None


def fix_escaped_seq(line: str) -> Tuple[str, int]:
    """Fixes typical escaped sequences found in tables.

    Args:
        line: A line from the post/submission.

    Returns:
        A tuple of the fixed line and number of changes.
    """

    escaped_seq = r"\\(\[|\*|\])"

    return re.subn(escaped_seq, r"\1", line)


def fix_double_link(line: str):
    """Removes double links from a row.

    Occurs when the links get escaped.

    Args:
        line: String of a line of the table.

    Returns:
        Line without a double link present.
    """
    double_link = r'\(\[.*\]\((.*)\)\)'
    return re.subn(double_link, r'(\1)', line)


def is_table_row(line: str):
    """Determines if the line is the expected table row.
    Uses vertical bars as an indicator.

    NOTE: Currently checking if between 2 and 4, since PCPP tables
    have 3 columns.

    Args:
        line: A line from the post/submission.

    Returns:
        True if it is, False otherwise.
    """

    bar_count = line.count('|')
    return 2 <= bar_count <= 4


def has_table_md(post_text: str) -> bool:
    """Determines if a post has a markdown table.

    Only checks if there is a column alignment present in
    the post.

    Args:
        post_text: String of the post's markdown.

    Returns:
        True if column alignments found, False otherwise.
    """
    alignment_pattern = r'(\|?:\-+:?)|(\|?\-+:)'

    match = re.search(alignment_pattern, post_text)

    return match is not None


def read_table_header(idx: int, lines: List[str], table: Table):
    """Reads and checks for errors in the table header.

    Args:
        idx: Line number we are on.
        lines: All lines in the post.
        table: Table object for holding the fixed row.
    """
    table.has_header = True
    table.add_row(idx, lines[idx])

    # If not the first line, check if the previous line to the
    # header is empty. Otherwise the markdown won't work.
    if idx != 0:
        prev_line = lines[idx - 1].strip()
        if len(prev_line) != 0:
            table.errors += 1


def read_table_row(idx: int, line: str, table: Table):
    """Reads a single table row and corrects it.

    Args:
        idx: Line number we are on.
        line: Row of the table
        table: Table object for holding the fixed row.
    """

    # Fix the escaped sequences, if any
    fixed, err_count = fix_escaped_seq(line)
    table.errors += err_count

    fixed, _ = fix_double_link(fixed)

    # Insert this row into the table
    table.add_row(idx, fixed)

    # If the previous row wasn't on the previous line, then
    # there are erronous line breaks between rows
    if len(table.rows) > 1 and \
            table.rows.get(idx - 1, None) is None:

        table.has_err_line_break = True
        table.errors += 1

    if is_column_alignments(line):
        table.has_column_alignments = True


def fix_footer_columns(table: Table):
    to_fix = []
    last_rows = min(len(table.rows), 3)

    for idx in range(last_rows):
        to_fix.append(table.rows.popitem())

    to_fix.reverse()
    for idx, line in to_fix:
        updated_line = line + ' '
        table.add_row(idx, updated_line)


def read_md_table(post_md: str) -> Union[Table, None]:
    """Reads and fixes a markdown table in a post.

    Args:
        post_md: String of the post's markdown.

    Returns:
        A Table with correct markdown, if a broken table
        was present. None otherwise.
    """
    table = Table()
    lines = post_md.splitlines()
    in_table = False

    # Read through the rest of the table
    for idx in range(len(lines)):
        line = lines[idx]
        line = line.strip()

        # Check if this line is part of a table
        if is_table_row(line):

            if is_table_header(line):
                # If we somehow hit another table header, break out
                if in_table:
                    break
                else:
                    in_table = True
                    read_table_header(idx, lines, table)

            else:
                read_table_row(idx, line, table)

        # If we found a line that isn't a row and isn't empty
        # then it likely means the table ended
        elif in_table and len(line) > 0:
            break

    if len(table.rows) > 0:
        if not table.has_header:
            table.errors += 1

        if not table.has_column_alignments:
            table.errors += 1

    if table.should_create():
        fix_footer_columns(table)
        return table
