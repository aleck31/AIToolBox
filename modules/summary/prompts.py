"""Prompts for the summary module"""

SYSTEM_PROMPT = """
You are a text summarization expert. Output ONLY the summary content - no explanations, no meta-commentary about what you're going to do.

Guidelines:
- If input contains URL starting with @, use get_text_from_url tool first
- Begin with overview sentence
- Use clear structure with sections/bullet points as needed
- Keep ~20-25% of original length
- Preserve technical terms
- Maintain factual accuracy and tone
- Use target language as specified while preserving technical terms

IMPORTANT: Output ONLY the final summary content. Do not include any explanatory text about your process.
"""

def build_user_prompt(text: str, target_lang: str) -> str:
    """Build user prompt with language instruction
    
    Args:
        text: Text to summarize
        target_lang: Target language for summary
        
    Returns:
        str: Formatted user prompt
    """
    lang_instruction = "Maintain the original language" if target_lang == "original" else f"Output the summary in {target_lang}"
    
    return f"""
    Analyze and summarize the following input. {lang_instruction}.

    <input>
    {text}
    </input>

    Provide a well-structured summary, ensure the output is in {target_lang} language while keeping technical terms accurate.
    """
