from pathlib import Path
import unittest

from reddit_table_bot.pcpphelperbot import PCPPHelperBot


class ToySubmission:
    def __init__(self):
        self.link_flair_text = None
        self.selftext = ''
        self.selftext_html = ''
        self.is_self = True
        self.url = 'post.test'
        self.name = '123'


class Testing(unittest.TestCase):
    def test_has_identifiable_link(self):
        bot = PCPPHelperBot('./db/replied_to.db')

        post = "<a href='https://pcpartpicker.com/user/pcpp-helper-bot/saved/sH3ZJx'></a>"

        has_iden = bot.has_iden_pcpp_link(post)
        self.assertEqual(True, has_iden)

    def test_correct_table(self):
        bot = PCPPHelperBot('./db/replied_to.db')
        post_file = Path('./tests/posts/correct.md').absolute()

        with open(post_file, 'r') as f:
            post = f.read()
            submission = ToySubmission()
            submission.selftext = post
            table = bot.read_submission(submission)

            self.assertIsNone(table)

    def test_escaped_table(self):
        bot = PCPPHelperBot('./db/replied_to.db')
        post_file = Path('./tests/posts/escaped.md').absolute()

        with open(post_file, 'r') as f:
            post = f.read()
            submission = ToySubmission()
            submission.selftext = post
            table = bot.read_submission(submission)

            self.assertIsNotNone(table)
            self.assertEqual(13, len(table.rows))

            correct_fp = Path('./tests/expected/escaped_table.md').absolute()
            with open(correct_fp, 'r') as c:
                correct = c.read()
                made = table.create_md()
                self.maxDiff = None
                self.assertEqual(correct, made)

    def test_no_linebreak_header(self):
        bot = PCPPHelperBot('./db/replied_to.db')
        post_file = Path('./tests/posts/no_linebreak_header.md').absolute()

        with open(post_file, 'r') as f:
            post = f.read()
            submission = ToySubmission()
            submission.selftext = post
            table = bot.read_submission(submission)

            fp = './tests/expected/no_linebreak_table.md'
            correct_fp = Path(fp).absolute()
            with open(correct_fp, 'r') as c:
                correct = c.read()
                made = table.create_md()
                self.assertEqual(correct, made)

    def test_mid_table_linebreak(self):
        bot = PCPPHelperBot('./db/replied_to.db')
        post_file = Path('./tests/posts/mid_table_linebreak.md').absolute()

        with open(post_file, 'r') as f:
            post = f.read()
            submission = ToySubmission()
            submission.selftext = post
            table = bot.read_submission(submission)

            fp = './tests/expected/mid_table_linebreak_table.md'
            correct_fp = Path(fp).absolute()
            with open(correct_fp, 'r') as c:
                correct = c.read()
                made = table.create_md()
                self.assertEqual(correct, made)

    def test_copy_pasted_edge(self):
        bot = PCPPHelperBot('./db/replied_to.db')
        post_file = Path('./tests/posts/copy_pasted_edge.md').absolute()

        with open(post_file, 'r', encoding='utf-8') as f:
            post = f.read()
            submission = ToySubmission()
            submission.selftext = post
            table = bot.read_submission(submission)

            fp = './tests/expected/copy_pasted_edge_table.md'
            correct_file = Path(fp).absolute()
            with open(correct_file, 'r') as c:
                correct = c.read()
                made = table.create_md()
                self.assertEqual(correct, made)

    def test_copy_pasted_mozilla(self):
        bot = PCPPHelperBot('./db/replied_to.db')
        post_file = Path('./tests/posts/copy_pasted_mozilla.md').absolute()

        with open(post_file, 'r', encoding='utf-8') as f:
            post = f.read()
            submission = ToySubmission()
            submission.selftext = post
            table = bot.read_submission(submission)

            fp = './tests/expected/copy_pasted_mozilla_table.md'
            correct_file = Path(fp).absolute()
            with open(correct_file, 'r') as c:
                correct = c.read()
                made = table.create_md()
                self.assertEqual(correct, made)

    def test_iden_link_and_escaped_reply(self):
        bot = PCPPHelperBot('./db/replied_to.db')
        post_file = Path('./tests/posts/iden_link_and_escaped.md').absolute()

        with open(post_file, 'r') as f:
            post = f.read()
            submission = ToySubmission()
            submission.selftext = post
            submission.selftext_html = "<a href='https://pcpartpicker.com/user/pcpp-helper-bot/saved/sH3ZJx'></a>"

            fp = './tests/expected/iden_link_and_escaped_reply.md'
            correct_fp = Path(fp).absolute()
            with open(correct_fp, 'r') as c:
                correct = c.read()
                made = bot.handle_submission(submission)
                self.assertEqual(correct, made)


if __name__ == "__main__":
    unittest.main()
