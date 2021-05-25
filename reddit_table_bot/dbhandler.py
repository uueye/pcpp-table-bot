import logging
from pathlib import Path
import sqlite3
from sqlite3 import Error
from typing import List


class DBHandler:
    """Handles all interactions with the SQLite3 database.

    Only will track the post id's that the bot has responded
    to, so that accidental re-replies do not occur.

    Attributes:
        conn: A connection to the database.
        db_file: Absolute filepath to the database file.
    """

    def __init__(self, db_file: str):
        self.conn = None
        abs_fp = Path(db_file)
        self.db_file = abs_fp.absolute()

        self.logger = logging.getLogger("db")

    def start(self):
        """Connect to the db file and create table if neccessary."""

        try:
            self.conn = sqlite3.connect(f'{self.db_file}')

            table_sql = """ CREATE TABLE IF NOT EXISTS replied_to (
                                id integer PRIMARY KEY,
                                submission_id integer
                            ); """

            cursor = self.conn.cursor()
            cursor.execute(table_sql)

        except Error:
            self.logger.exception("Error connecting to the database file.")

    def stop(self):
        """Closes connection to the database."""
        self.conn.close()

    def add_reply(self, post_name: str):
        """Given a post name, convert to integer and add to table.

        Args:
            post_name: A post's uuid with a 3 character prefix.
        """

        only_id = post_name[3:]
        submission_id = int(only_id, 36)

        insert_sql = """ INSERT INTO replied_to(submission_id)
                        VALUES (?) """

        cursor = self.conn.cursor()
        cursor.execute(insert_sql, (submission_id,))
        self.conn.commit()

    def get_reply(self, post_name: str) -> List[int]:
        """Selects a reply with the given post_name, if it exists.

        Args:
            post_name: A post's uuid with a 3 character prefix.

        Returns:
            A list of submission ids matching the post name.
        """

        only_id = post_name[3:]
        submission_id = int(only_id, 36)

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM replied_to WHERE submission_id=?",
                       (submission_id,))

        rows = cursor.fetchall()
        return rows

    def clear_table(self):
        """Drops the table tracking posts we have replied to."""
        cursor = self.conn.cursor()
        cursor.execute("DROP TABLE replied_to")
