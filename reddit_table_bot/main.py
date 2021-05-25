import logging
import logging.config
import json
from pathlib import Path

from .pcpphelperbot import PCPPHelperBot


def setup_logging() -> None:
    """Reads the config file and sets up logging.

    Args:
        cur_dir: Holds the absolute path to the current directory.
    """

    # Expect the logs folder to be in parent directory (root of project)
    config_file = Path('./logs/config.json').absolute()

    with open(config_file, 'r', encoding='utf-8') as file:
        try:
            config = json.load(file)
            logging.config.dictConfig(config)
        except Exception as e:
            print(e)
            print("Error reading in the logging configuration file."
                  " Ensure it is in the root of the project directory under"
                  " the logs' folder.")


if __name__ == "__main__":
    setup_logging()
    bot = PCPPHelperBot("./db/replied_to.db")
