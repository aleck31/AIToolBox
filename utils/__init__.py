# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""General helper utilities here"""
# Python Built-Ins:
import re
import os
import sys
import textwrap
from io import StringIO
from typing import Literal
from utils import file


FORMAT_IMG = ['png', 'jpeg', 'gif', 'webp']
FORMAT_DOC = ['pdf', 'csv', 'doc', 'docx', 'xls', 'xlsx', 'html', 'txt', 'md']


def print_ww(*args, width: int = 100, **kwargs):
    """Like print(), but wraps output to `width` characters (default 100)"""
    buffer = StringIO()
    try:
        _stdout = sys.stdout
        sys.stdout = buffer
        print(*args, **kwargs)
        output = buffer.getvalue()
    finally:
        sys.stdout = _stdout
    for line in output.splitlines():
        print("\n".join(textwrap.wrap(line, width=width)))


def format_resp(response: str):
    """Format the output content, remove xml tags"""
    # Trims leading whitespace using regular expressions
    pattern = '^\\s+'
    response = re.sub(pattern, '', response)
    # Remove XML tags using regular expressions
    # response = response[response.index('\n')+1:]
    match = response.startswith('<')
    if match:
        return re.sub(r'<[^>]+>', '', response)
    else:
        return response
