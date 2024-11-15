from utils import format_msg


class ChatMemory(object):
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


# Global memory manager instance
chat_memory = ChatMemory()
