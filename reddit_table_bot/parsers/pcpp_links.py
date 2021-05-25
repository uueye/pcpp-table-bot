from typing import List
import regex as re
from bs4 import BeautifulSoup

from .data_classes import PCPP_Link


def get_pcpp_list_links(post_html: str) -> List[PCPP_Link]:
    """Gets all PCPP list links if present in the provided post html.

    Args:
        post_html: The post's html data.

    Returns:
        A list of tuples of the PCPP link and if it is an anonymous link.
        An empty list if no PCPP links w ere found.
    """

    soup = BeautifulSoup(post_html, 'html.parser')
    re_pcpp_link = r'(?P<full>https:\/\/pcpartpicker.com\/((?P<iden>user)'\
                   r'\/[A-Za-z\-\_]+\/saved\/\w+|(list)\/\w*))'

    pcpp_a_tags = soup.find_all(href=re.compile(re_pcpp_link))

    pcpp_links = []
    for tag in pcpp_a_tags:
        match = re.search(re_pcpp_link, tag['href'])
        pcpp_link = PCPP_Link(match.group('full'),
                              match.group('iden') is None)

        pcpp_links.append(pcpp_link)

    return pcpp_links


def get_pcpp_product_links(post_html: str) -> List:
    soup = BeautifulSoup(post_html, 'html.parser')
    re_product_link = r'http[s?]:\/\/pcpartpicker.com\/product\/'

    product_tags = soup.find_all(href=re.compile(re_product_link))
    return product_tags
