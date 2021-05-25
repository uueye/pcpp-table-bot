from typing import OrderedDict
from dataclasses import dataclass


class Table:
    def __init__(self):
        self.has_header = False
        self.has_column_alignments = False
        self.rows: OrderedDict[int, str] = OrderedDict()
        self.errors: int = 0
        self.guessed_url: str = None

    def add_row(self, line_num: int, row: str):
        self.rows.update({line_num: row})
        self.rows.move_to_end(line_num)

    def create_md(self) -> str:
        header = []

        if not self.has_header:
            header.append("Type|Item|Price")

        if not self.has_column_alignments:
            header.append(":----|:----|:----")

        body = list(self.rows.values())
        full_table = header + body

        markdown = '\n'.join(full_table)

        return markdown

    def should_create(self) -> bool:
        return len(self.rows) > 0 and self.errors > 0


@dataclass
class PCPP_Link:
    url: str = None
    is_anon: bool = False
