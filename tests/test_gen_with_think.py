import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.asking.handlers import AskingHandlers


# Test cases with different scenarios
test_cases = [
    # Case 1: Normal case with thinking tags
    [
        '<thinking>Let me think about this.',
        ' continues here.</thinking> Then response.'
    ],
    # Case 2: Response with thinking tags
    [
        'Here is my response. <thinking>',
        'This is my thinking process.',
        '</thinking> And my conclusion.'
    ],

    # Case 3: Multiple thinking sections
    [
        '<thinking>Start Think 1',
        '111</thinking> Then response.',
        '<thinking>Continue Think 2',
        '222</thinking>.'
    ],
    # Case 4: Split tags across chunks
    [
        'Start <think',
        'ing>Split tag thinking</think',
        'ing>.'
    ],
    # Case 5: No thinking tags
    [
        'Just a regular response ',
        'with no thinking tags.'
    ],
    # Case 6: Unclosed thinking tag
    [
        '<thinking> This is my thinking process',
        ' that never gets closed.',
        'Here is my response.'
    ]
]


def get_expected_thinking(chunks):
    # Helper to extract expected thinking content
    full_text = ''.join(chunks)
    thinking = ''
    start = 0
    while True:
        start = full_text.find('<thinking>', start)
        if start == -1:
            break
        end = full_text.find('</thinking>', start)
        if end == -1:
            break
        thinking += full_text[start+10:end] + ' '  # +10 to skip '<thinking>'
        start = end + 11  # +11 to skip '</thinking>'
    return thinking.strip()

def get_expected_response(chunks):
    # Helper to extract expected response content
    full_text = ''.join(chunks)
    result = full_text
    while '<thinking>' in result and '</thinking>' in result:
        start = result.find('<thinking>')
        end = result.find('</thinking>', start) + 11  # +11 to include '</thinking>'
        result = result[:start] + result[end:]
    return result

async def test_gen_with_think():
    
    for i, chunks in enumerate(test_cases):
        print(f'=============== Test Case {i+1} ===============')

        # Generate response with streaming
        thinking_buffer = "```thinking\n"
        response_buffer = ""
        in_thinking_mode = True  # Start in thinking mode
        
        for chunk in chunks:
            print(f'* Processing chunk: \"{chunk}\"')

            # Process each chunk immediately
            if in_thinking_mode:
                # Currently in thinking mode - look for closing tag
                if "</thinking>" in chunk:
                    # Split chunk at closing tag
                    parts = chunk.split("</thinking>", 1)
                    thinking_buffer += parts[0]  # Add content before closing tag to thinking
                    response_buffer += parts[1]  # Add content after closing to response
                    in_thinking_mode = False  # Switch to response mode
                else:
                    # No closing tag found, all content goes to thinking (removing <thinking> if present)
                    thinking_buffer += chunk.replace("<thinking>", "")
            else:
                # Currently in response mode - look for opening tag
                if "<thinking>" in chunk:
                    # Split chunk at opening tag
                    parts = chunk.split("<thinking>", 1)
                    response_buffer += parts[0]  # Add content before opening tag to response
                    thinking_buffer += parts[1]  # Add content after opening tag to thinking
                    in_thinking_mode = True  # Switch to thinking mode
                else:
                    # No opening tag found, all content goes to response
                    response_buffer += chunk.replace("</thinking>", "")
            
            print(f' -- in_thinking_mode={in_thinking_mode},\n -- thinking_buffer=\"{thinking_buffer}\",\n -- response_buffer=\"{response_buffer}\"')
        
        print(f'【Expected result for Test Case {i+1}:】')
        print(f'Expected thinking: \"{get_expected_thinking(chunks)}\"')
        print(f'Expected response: \"{get_expected_response(chunks)}\"')




async def test_gen_with_think2():
    
    for i, chunks in enumerate(test_cases):
        print(f'\\n=== Test Case {i+1} ===')
        
        # Reset buffers for each test
        thinking_buffer = ''
        response_buffer = ''
        accumulated_chunk = ''
        in_thinking_mode = False  # Start in response mode
        
        for chunk in chunks:
            print(f'\\nProcessing chunk: \"{chunk}\"')
            
            # Accumulate the chunk
            accumulated_chunk += chunk
            
            # Process accumulated chunk
            while True:
                if in_thinking_mode:
                    # Look for closing tag
                    closing_index = accumulated_chunk.find('</thinking>')
                    if closing_index >= 0:
                        # Add content before closing tag to thinking buffer
                        thinking_buffer += accumulated_chunk[:closing_index]
                        # Move past the closing tag
                        accumulated_chunk = accumulated_chunk[closing_index + 11:]  # 11 is length of '</thinking>'
                        in_thinking_mode = False
                    else:
                        # No closing tag found yet, wait for more chunks
                        break
                else:
                    # Look for opening tag
                    opening_index = accumulated_chunk.find('<thinking>')
                    if opening_index >= 0:
                        # Add content before opening tag to response buffer
                        response_buffer += accumulated_chunk[:opening_index]
                        # Move past the opening tag
                        accumulated_chunk = accumulated_chunk[opening_index + 10:]  # 10 is length of '<thinking>'
                        in_thinking_mode = True
                    else:
                        # No opening tag found, all remaining content goes to response
                        response_buffer += accumulated_chunk
                        accumulated_chunk = ''
                        break
            
            print(f'After: in_thinking_mode={in_thinking_mode}, thinking=\"{thinking_buffer}\", response=\"{response_buffer}\", accumulated=\"{accumulated_chunk}\"')
        
        # Process any remaining content
        if accumulated_chunk:
            if in_thinking_mode:
                thinking_buffer += accumulated_chunk
            else:
                response_buffer += accumulated_chunk
        
        print(f'\\nFinal result for Test Case {i+1}:')
        print(f'thinking_buffer: \"{thinking_buffer}\"')
        print(f'response_buffer: \"{response_buffer}\"')


asyncio.run(test_gen_with_think())
