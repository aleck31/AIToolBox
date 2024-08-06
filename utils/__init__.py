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


def format_msg(message: dict, role: Literal["user", "assistant"]):
    '''
    Args:
    - message: Multimodal Message Dict
    {
        "text": "user input", 
        "files": ["file_path1", "file_path2", ...]
    }
    '''

    msg_content = [
        {"text": message.get('text')}
    ]

    if message.get('files'):
        for file_path in message.get('files'):
            base_name, file_extension = os.path.splitext(file_path)
            file_name = os.path.basename(base_name)
            file_extension = file_extension.lower()[1:]
            if file_extension == 'jpg':
                file_extension = 'jpeg'

            with open(file_path, "rb") as fr:
                file_bytes = fr.read()
            if file_extension in FORMAT_IMG:
                file_msg = {
                    'image': {
                        'format': file_extension,
                        'source': {
                            'bytes': file_bytes
                        }
                    }
                }
            elif file_extension in FORMAT_DOC:
                file_msg = {
                    'document': {
                        'format': file_extension,
                        'name': file_name,
                        'source': {
                            'bytes': file_bytes
                        }
                    }
                }
            else:
                raise ValueError('Unsupported extension.')

            msg_content.append(file_msg)

    return {
        'role': role,
        'content': msg_content
    }


def format_message(message: dict, role: Literal["user", "assistant"]):
    '''
    Args:
    - message : Multimodal Message Dict
    {
        "text": "user input", 
        "files": ["file_path1", "file_path2", ...]
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
        for path in file_list:
            img_msg = {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": file.path_to_base64(path)
                }
            }
            msg_content.append(img_msg)

        formated_msg = {'role': role, 'content': msg_content}

    return formated_msg


class ChatHistory(object):
    """Abstract class for storing chat message history."""

    def __init__(self, initial_history=None):
        """
        Initialize a ChatHistoryMemory instance.        
        Args:
        - initial_messages (list, optional): List of initial chat messages. Defaults to None.
        """
        self.conversation = []
        while initial_history:
            for user_msg, assistant_msg in initial_history:
                self.add_user_msg({'text': user_msg})
                self.add_bot_msg({'text': assistant_msg})

    def add_message(self, message: dict) -> None:
        """
        Add a message to the history list.
        Args:
        - message (dict): The messages send to the model.
        {
            'role': 'user'|'assistant', 
            'content': [{
                'text': 'string',
                'image': {},
                'document': {}
            }]
        }
        """
        self.conversation.append(message)

    def clear(self) -> None:
        """Clear memory"""
        self.conversation.clear()

    def add_user_msg(self, message: dict) -> None:
        self.add_message(
            format_msg(message, "user")
        )
        # print(f"FULL_History: {self.messages}")

    def add_bot_msg(self, message: dict) -> None:
        self.add_message(
            format_msg(message, "assistant")
        )

    def get_latest_message(self):
        return self.messages[-1] if self.messages else None

    def del_latest_message(self):
        self.messages.pop()
