import os
import logging
from typing import Union

import praw
from praw.models import Message

from .parsers.parse_copy_paste_md import has_copy_paste_table, read_copy_paste
from .parsers.parse_md import has_table_md, read_md_table
from .parsers.pcpp_links import get_pcpp_list_links
from .parsers.data_classes import Table
from .dbhandler import DBHandler


class PCPPHelperBot:
    """Posts PC Part Picker markup tables when applicable.

    This utilizes the PRAW wrapper for interacting with Reddit. It streams
    new submissions in order to look for submissions with a PC Part Picker
    list URL. If the post already has a table, no action will be taken. If
    not, or it is malformed, a reply containing the table will be posted.
    """

    def __init__(self, db_file: str, live=False):
        self.is_live = live

        # Logger setup
        self.logger = logging.getLogger('bot')

        # Database handler
        self.db_handler = DBHandler(db_file)

        # Retrieve environment vars for secret data
        username = os.environ.get('REDDIT_USERNAME')
        password = os.environ.get('REDDIT_PASSWORD')
        client_id = os.environ.get('CLIENT_ID')
        secret = os.environ.get('CLIENT_SECRET')

        version = 0.2
        user_agent = f"web:pcpp-helper-bot:v{version} (by u/pcpp-helper-bot)"

        # Utilize PRAW wrapper
        self.reddit = praw.Reddit(user_agent=user_agent,
                                  client_id=client_id, client_secret=secret,
                                  username=username, password=password)

        # Only look at submissions with one of these flairs
        # TODO: Are these the best submission flairs to use?
        self.pertinent_flairs = ['Build Complete', 'Build Upgrade',
                                 'Build Help', 'Build Ready', None]

        # Read in the templates
        templates = './reddit_table_bot/templates'
        with open(f'{templates}/replytemplate.md', 'r') as template:
            self.REPLY_TEMPLATE = template.read()

        with open(f'{templates}/idenlinkfound.md', 'r') as template:
            self.IDENTIFIABLE_TEMPLATE = template.read()

        with open(f'{templates}/tableissuetemplate.md', 'r') as template:
            self.TABLE_TEMPLATE = template.read()

    def read_hot(self, subreddit_name: str, count=15):
        """Reads only the hot submissions of the subreddit.

        Args:
            subreddit_name: Name of the subreddit to read.
            count (default=15): Number of submissions to read.
        """
        self.db_handler.start()
        subreddit = self.reddit.subreddit(subreddit_name)

        try:
            for submission in subreddit.hot(limit=count):
                self.handle_submission(submission)

        except Exception:
            self.logger.critical('Problem connecting to Reddit or'
                                 ' in creating reply')
            self.logger.critical('Exception data: ', exc_info=True)

        finally:
            self.db_handler.stop()

    def read_post(self, url: str):
        """Reads a single post at the given url.

        Args:
            url: A URL to a post.
        """

        self.db_handler.start()

        submission = self.reddit.submission(url=url)
        self.handle_submission(submission)

        self.db_handler.stop()

    def monitor_subreddit(self, subreddit_name: str):
        """Monitors the subreddit provided (mainly r/buildapc) for new
        submissions.

        Args:
            subreddit_name (str): The name of the subreddit
        """

        self.db_handler.start()

        continue_monitoring = True
        self.subreddit_name = subreddit_name

        # Will skip the posts made BEFORE the bot starts observing
        # By default, up to 100 historical submissions would be returned
        # See PRAW.reddit.SubredditStream #3147
        subreddit = self.reddit.subreddit(subreddit_name)

        # Stream in new submissions from the subreddit
        while continue_monitoring:
            try:
                for submission in subreddit.stream.submissions(
                        skip_existing=True):

                    self.handle_submission(submission)

                    stopping = self.__check_stop()
                    if stopping:
                        continue_monitoring = False
                        break

            except Exception:
                self.logger.critical('Problem connecting to Reddit or'
                                     ' in creating reply')
                self.logger.critical('Exception data: ', exc_info=True)

            # TODO: Catch any exceptions for when Reddit is down
            # or PRAW has issues

        self.db_handler.stop()

    def handle_submission(self,
                          submission: praw.reddit.Submission)\
            -> Union[praw.reddit.Comment, str, None]:
        """Reads and replies to a single submission when necessary.

        Args:
            submission: A Submission object to read and possibly reply to.
        """

        has_iden = self.has_iden_pcpp_link(
            submission.selftext_html)

        table = self.read_submission(submission)

        if table is not None or has_iden:
            return self.reply(submission, has_iden, table)

    def has_iden_pcpp_link(self, post_html: str) -> bool:
        """Checks if the post has an identifiable PCPP list link.

        Args:
            post_html: The HTML for a post.

        Returns:
            True if an identifiable PCPP list link is present.
            False otherwise.
        """
        list_links = get_pcpp_list_links(post_html)

        for list_link in list_links:
            if not list_link.is_anon:
                return True

        return False

    def read_submission(self,
                        submission:
                        praw.reddit.Submission) -> Union[Table, None]:
        """Reads a submission from Reddit.

        Args:
            submission: A PRAW Submission object.

        Returns:
            A table read from the submission, or None if no bad table
            is present.
        """

        flair = submission.link_flair_text

        if self.is_live and self._already_replied(submission.name):
            self.logger.info('Already replied to this submission.')

        # Only look at text submissions and with the appropriate flairs
        elif flair in self.pertinent_flairs and submission.is_self:
            self.logger.info(f'CHECKING SUBMISSION: {submission.url}')
            table = None

            if has_table_md(submission.selftext):
                table = read_md_table(submission.selftext)

            elif has_copy_paste_table(submission.selftext):
                table = read_copy_paste(submission.selftext)

        return table

    def reply(self, submission: praw.reddit.Submission,
              has_iden: bool,
              table: Table) -> Union[str, praw.reddit.Comment]:
        """Replies to a Reddit submission.

        Args:
            submission (`obj`: praw.Reddit.Submission): PRAW Submission object.

        Returns:
            Reply message string if NOT live, otherwise
            PRAW.reddit.Comment object.
        """

        # Create the reply with this information
        reply_message = self._make_reply(has_iden, table)

        # Only if the bot is 'live' on Reddit or not
        if self.is_live:
            # Post the reply!
            reply = submission.reply(reply_message)
            self._save_reply_db(submission.name)
            return reply
        else:
            return reply_message

    def _make_reply(self, has_iden: bool, table: Table) -> str:
        """Creates the full reply message.

        Args:
            has_iden: If the post has identifiable list urls.
            table: Table data found in the post.

        Returns:
            The entire reply message, ready to be posted.
        """

        table_markdown = self._make_table_markdown(table)
        iden_markdown = self.make_identifiable_markdown(has_iden)

        if len(table_markdown) == 0:
            self.logger.error('Failed to make table markdown')

        if has_iden and len(iden_markdown) == 0:
            self.logger.error('Failed to make identifiable markdown')

        reply_message = self._put_message_together(table_markdown,
                                                   iden_markdown)

        if len(reply_message) == 0:
            self.logger.error('Failed to create a message.')
        else:
            self.logger.info(f'Reply: {reply_message}')

        return reply_message

    def _put_message_together(self, table_markdown: str,
                              iden_markdown: str) -> str:
        """Puts together the variable data into a message.

        Args:
            table_markdown (str): Contains the markdown for the table data.
            iden_markdown (str): Contains the markdown for the identifiable
                                    message and data.

        Returns:
            A string containing the combined reply message.
        """

        reply_message = ''
        message_markdown = []

        if len(table_markdown) != 0:
            message_markdown.append(table_markdown)

        if len(iden_markdown) != 0:
            message_markdown.append(iden_markdown)

        if len(message_markdown) != 0:
            message_markdown = '\n\n'.join(message_markdown)
            reply_message = self.REPLY_TEMPLATE.replace(':message:',
                                                        message_markdown)

        return reply_message

    def _make_table_markdown(self, table: Table) -> str:
        """Put together the table markdown.

        Args:
            table: A table to create.

        Returns:
           A string containing the markdown for the tables for the PCPP lists.
        """

        if table is not None:
            table_md = table.create_md()
            table_message = self.TABLE_TEMPLATE.replace(':table:', table_md)
        else:
            table_message = ''

        return table_message

    def make_identifiable_markdown(self, has_iden: bool) -> str:
        """Creates the identifiable markdown, if necessary.

        Args:
            has_iden: If an identifiable link was found.

        Return:
            A string with the identifiable markdown, or an empty string
            if no identifiable links found.
        """

        if has_iden:
            return self.IDENTIFIABLE_TEMPLATE
        else:
            return ''

    def _check_inbox_for_stop(self):
        """Checks if a moderator messaged the bot to stop running.
        The subject must be 'stop', and the body of the message
        contains an optional reason for stopping the bot.

        Returns:
            (boolean on if to stop, a string containing the reason).
        """

        should_stop = False
        reason = ''

        for item in self.reddit.inbox.unread():
            # Check if it is a message, not a mention or something else
            if isinstance(item, Message):
                author = item.author

                # Check if the messenger is a moderator of r/buildapc
                if not author.is_suspended and author.is_mod and\
                        self.subreddit_name in author.moderated():

                    subject = item.subject

                    # Did they tell me to stop?
                    if 'stop' in subject.lower():
                        reason = item.body
                        should_stop = True
                        item.mark_read()

        return should_stop, reason

    def _already_replied(self, post_name: str) -> bool:
        """Determines if we already replied to the submission.

        Args:
            post_name: UUID string for the submission/post.

        Returns:
            True if already replied, False otherwise.
        """
        found = self.db_handler.get_reply(post_name)

        return len(found) > 0

    def _save_reply_db(self, post_name: str):
        """Saves the submission's uuid name to the database."""
        self.db_handler.add_reply(post_name)

    def __check_stop(self) -> bool:
        """Checks the bot's inbox for a stop message.

        Only will work if the sender is a moderator of the current
        subreddit.

        Returns:
            True if a stop message was found. False otherwise.
        """
        should_stop, reason = self._check_inbox_for_stop()
        if should_stop and reason is not None:
            self.logger.info(f'STOPPING BY REQUEST.'
                             'REASON: {reason}')
            return True

        return False
