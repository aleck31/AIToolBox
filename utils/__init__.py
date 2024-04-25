# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""General helper utilities here"""
# Python Built-Ins:
from io import StringIO
import re
import sys
import textwrap
from . import image



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


def format_message(message: dict, role):
    '''
    :input: Multimodal Message Dict
    {
        "text": "user input", 
        "files": [
            {'path': "file_path1", 'url': '/file=file_path1', 'size': 123},
            {'path': "file_path2", 'url': '/file=file_path2', 'size': 123}, 
            ...
        ]
    }    
    '''

    if not message.get('files'):
        formated_msg = {'role': role, 'content': message.get('text')}
    else:
        msg_content = [
            {
                "type": "text",
                "text": message.get('text')
            }
        ]        
        file_list = message.get('files')
        for file in file_list:  
            img_msg = {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image.path_to_base64(file['path'])
                }
            }
            msg_content.append(img_msg)

        formated_msg = { 'role': role, 'content': msg_content }

    return formated_msg


class ChatHistory(object):
    """Abstract class for storing chat message history."""

    def __init__(self, initial_history=None):
        """
        Initialize a ChatHistoryMemory instance.        
        Args:
            initial_messages (list, optional): List of initial chat messages. Defaults to None.
        """
        self.messages = []
        while initial_history:
            for user_msg, assistant_msg in initial_history:
                self.add_user_msg({'text': user_msg})
                self.add_bot_msg({'text': assistant_msg})

    def add_message(self, message) -> None:
        """Add a message to the history list"""
        self.messages.append(message)

    def clear(self) -> None:
        """Clear memory"""
        self.messages.clear()

    def add_user_msg(self, message: dict) -> None:
        self.add_message(
            format_message(message, "user")
        )
        # print(f"FULL_History: {self.messages}")

    def add_bot_msg(self, message: dict) -> None:
        self.add_message(
            format_message(message, "assistant")
        )

    def get_latest_message(self):
        return self.messages[-1] if self.messages else None

    def del_latest_message(self):
        self.messages.pop()
