from typing import List, NamedTuple, Tuple, Union
import regex as re

from .data_classes import Table


class PartTypeInfo(NamedTuple):
    name: str
    start: int
    end: int


def create_part_type_regex() -> str:
    """Creates a regex that will identify part types that were copy pasted in.

    This expects the to be searched text is in markdown. As such, part types
    should be as follows:
        '[<part type>](<part type link>)'
        OR
        'Custom'

    Part type could be bolded, but that differs from browser to browser.
    A 📷 emoji will follow from a copy paste in fancy-pants editor, because
    each part type will have an image afterward - even if it is 'Custom.'

    Returns:
        A regex string that will match a markdown'd part type.
    """

    part_types = [
        "CPU", "CPU Cooler", "Motherboard", "Memory", "Storage",
        "Video Card", "Case", "Power Supply", "Operating System",
        "Fan Controller", "Monitor", "Sound Cards",
        "Wired Network Adapter", "Wireless Network Adapter",
        "Headphones", "Keyboard", "Mouse", "Speakers", "Webcam",
        "Case Accessory", "Case Fan", "Fan Controller",
        "Thermal Compound", "External Storage", "Optical Drive",
        "UPS System"
    ]

    # Surround all parts in capture group
    # TODO: Necessary?
    re_parts = map(lambda x: fr'(?P<part_type>\s?{x}\s?)', part_types)

    # Join the part types together with or operator |
    re_joined_parts = '|'.join(re_parts)

    # Wrap the part types in a markdown link
    re_joined_parts = fr'\[(\*{{2}})?({re_joined_parts})(\*{{2}})?\]'

    # Add the URL markdown for the parts link
    re_part_link = fr'({re_joined_parts}'\
        r'\(https:\/\/pcpartpicker.com\/products\/[a-z\-]+\/\))'

    # It could be 'Custom' which isn't a link.
    # When copy pasted into the fancy-pants editor, it will always put a
    # camera emoji after the part type.
    re_part_full = fr'(?P<part>{re_part_link}|Custom)(\s*)?📷'

    return re_part_full


re_part_type = create_part_type_regex()
re_part_type_pattern = re.compile(re_part_type)

# Matches most currencies, either starting or ending with the currency
# symbol
# Allowing any combo of numbers, commas, and periods
re_currency = r'(\*\*)?((\p{Sc}\s?[0-9,\.]+)|([0-9,\.]+\s?\p{Sc}))(\*\*)?'

# The last row ends either at:
#   a 'Buy' link, 'FREE', 'Purchased', 'Base Total' or 'Total'
# Since buying options are not necessarily present, it could be the end
# of the table.
re_last_row_end = fr'(\[(\*\*)?Buy(\*\*)?\])|FREE|Purchased|'\
    r'No Prices Available|Base Total|Total|\\n'

# Where a part name will end will relate to purchasing or the
# end of the line
re_end_name = fr'{re_currency}|FREE|Purchased|No Prices Available|'\
    r'(\[(\*\*)?Buy(\*\*)?\])'

re_total = fr'(?<!Base )Total:(\s+)?(?P<total>{re_currency})'


def remove_camera_emoji(line: str):
    """Replace all camera emojis with spaces."""
    return line.replace('📷', ' ')


def get_all_part_types(post_md: str) -> List[PartTypeInfo]:
    """Finds the starting and ending indices of all part types.

    Args:
        post_md: String of the post's markdown.

    Returns:
        A list of all the indices pertaining to part types.
        These mark the beginning of rows.
    """
    part_types: List[PartTypeInfo] = []

    # Look for all part types, whether they're links or just 'Custom'
    match = re_part_type_pattern.search(post_md)

    # Find all starting points of part types. These mark the start of rows
    while match:

        # Get where the part type starts and ends
        start = match.start('part')
        end = match.end('part')

        type = match.group('part_type')

        # If it's custom, it won't have a 'part_type'
        if type is None:
            type - match.group('part')

        part_info = PartTypeInfo(type, start, end)

        # Add this tuple to a list
        part_types.append(part_info)

        # Look for the start of the next row
        match = re_part_type_pattern.search(post_md, start + 1)

    return part_types


def get_part_name(text_md: str) -> str:
    """Finds the part's name in the row.

    Args:
        text_md: Some section/row of the post's markdown.

    Returns:
        The part's name, and potentially link.
    """

    # Look for where the part name ends, if not the end of the line
    name_end = re.search(re_end_name, text_md)
    name = text_md

    # If it ends before the end, then take the substring of it
    if name_end:
        name = text_md[:name_end.start(0)]

    # Remove any bolding in the link
    name, _ = re.subn(r'(\[\*\*(.*)\*\*\])', r'[\2]', name)

    return name


def get_cost(text_md: str) -> str:
    """Finds the costs in the given markdown.

    Args:
        text_md: Some section of the post's markdown.

    Returns:
        The last currency string found in the section.
        An empty string otherwise.
    """
    # Find all costs for this product, could be promos, etc.
    costs = re.findall(re_currency, text_md)
    cost = ''

    # The main total of this part will always be the last
    # TODO: Could it have a promo with no actual cost?
    # TODO: Could just grab largest number?
    if len(costs) > 0:
        cost = costs[-1][1]

    return cost


def get_total(post_md: str) -> Union[str, None]:
    """Finds the total amount in the table.

    Args:
        post_md: The post's markdown text.

    Returns:
        Either a string with the total, or None if not found.
    """
    # Look for the total cost of the build (ensure not Base Total)
    total_match = re.search(re_total, post_md)

    # If it was included, get the amount
    return total_match.group('total')


def has_copy_paste_table(post_md: str) -> bool:
    """Look for a copy-pasted part type in the post.

    Args:
        post_md: The post's markdown text.

    Returns:
        True if a copy-pasted part type was found in the post.
        False otherwise.
    """
    match = re_part_type_pattern.search(post_md)
    return match is not None


def read_table(post_md: str,
               all_part_type_info: List[PartTypeInfo],
               part_count: int) -> Tuple[Table, int]:
    """Reads a copy-pasted table from PCPP if present.

    Args:
        post_md: String of the post's markdown.
        all_part_type_info: List of the part type indices and info.
        part_count: Count of parts (or rows).

    Returns:
        A Table with the corrected rows of the copy-pasted table,
        it was present.
    """
    table = Table()
    end = None

    # If we found at least one copy-pasted part type, it's an error
    if part_count > 1:
        table.errors += 1

    # Get all the appropriate data in each 'row' from
    # the start of one part type to the start of the next
    for idx in range(part_count):

        part_type_info = all_part_type_info[idx]
        part_type = part_type_info.name.strip()

        # Start index of this row in the post
        start = part_type_info.start

        # Start index of the row data after part type
        data_start = part_type_info.end

        if idx == part_count - 1:
            # Search for the end of the last row, since there won't
            # be a next part type
            from_last_row = post_md[start:]
            match = re.search(re_last_row_end, from_last_row)
            end = match.start(0) + start

        else:
            # End of this row index is start of next part
            end = all_part_type_info[idx + 1].start

        # Will hold the part name and potentially cost
        data = post_md[data_start:end]

        # Strip it of camera emojis and spaces
        data = remove_camera_emoji(data).strip()

        name = get_part_name(data)
        cost = get_cost(data)

        row = f"**{part_type}** | {name} | {cost}"
        table.add_row(idx, row)

    return table, end


def add_table_footer(table: Table, post_md: str, part_count: int, end: int):
    """Adds the table footer.

    Args:
        table: The table to add onto.
        post_md: String of the post's markdown.
        part_count: Number of rows.
        end: Index of where the last row ends.
    """

    total = get_total(post_md[end:])

    if total:
        price_info = '| *Prices (likely) include shipping, taxes,'\
                     ' rebates, and discounts* | '
        table.add_row(part_count, price_info)
        total_row = f"| **Total** | {total} "
        table.add_row(part_count + 1, total_row)


def read_copy_paste(post_md: str) -> Union[Table, None]:
    """Reads a post's markdown for a copy-pasted PCPP table.

    Args:
        post_md: String of the post's markdown.

    Returns:
        A Table holding a properly formatted markdown table,
        if a copy-pasted one was found. None otherwise.
    """
    # Get the ranges for the part types (beginning of rows)
    all_part_type_info = get_all_part_types(post_md)
    part_type_count = len(all_part_type_info)

    table, end = read_table(post_md, all_part_type_info, part_type_count)
    add_table_footer(table, post_md, part_type_count, end)

    if table.should_create():
        return table
