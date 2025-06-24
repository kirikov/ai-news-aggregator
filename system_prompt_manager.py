import os
import logging

logger = logging.getLogger(__name__)

# Base system prompt template
BASE_SYSTEM_PROMPT = """You are an AI agent acting as an editor-in-chief of a curated international news channel. Your task is to evaluate news items from various sources and decide whether each item should be reposted to the audience of the channel.

Here are your core responsibilities:

{system_prompt_editorial_guidelines}

Be strict and professional in your decisions. The goal is to maintain a high-quality international feed for an informed audience.

Format your response in the following structure in JSON format:

Original Language: [Detected language]
Translated News: [Translated language]
Content Type: [e.g. Political News, Product Promo, Local Event, Global Event, Social Post, etc.]
Decision: [REPOST or REJECT]
Reasoning: [Concise editorial justification]"""


def load_system_prompt(base_prompt_path='system_prompt.txt', guidelines_path='system_prompt_editorial_guidelines.txt') -> str:
    """Load and combine base system prompt with configurable editorial guidelines"""
    try:
        # Use the internal base prompt instead of loading from file
        base_prompt = BASE_SYSTEM_PROMPT.strip()
        
        # Load editorial guidelines
        with open(guidelines_path, 'r', encoding='utf-8') as f:
            system_prompt_editorial_guidelines = f.read().strip()
        
        # Combine them by replacing the placeholder
        system_prompt = base_prompt.replace('{system_prompt_editorial_guidelines}', system_prompt_editorial_guidelines)
        
    except FileNotFoundError as e:
        logger.error(f"Required file not found: {e}")
        raise FileNotFoundError(f"Critical error: Required guidelines file not found. Application cannot continue.")
    except Exception as e:
        logger.error(f"Error reading editorial guidelines file: {e}")
        raise Exception(f"Critical error reading editorial guidelines file: {e}. Application cannot continue.")
    
    # Check if the system prompt is empty
    if not system_prompt:
        logger.error("Combined system prompt is empty")
        raise ValueError("Critical error: Combined system prompt is empty. Application cannot continue.")
    
    return system_prompt


def get_system_prompt_editorial_guidelines_file() -> str:
    """Get the editorial guidelines file path from environment variable"""
    return os.environ.get('system_prompt_editorial_guidelines_FILE', 'system_prompt_editorial_guidelines.txt')


def load_configured_system_prompt() -> str:
    """Load system prompt using the configured editorial guidelines file"""
    guidelines_file = get_system_prompt_editorial_guidelines_file()
    return load_system_prompt(guidelines_path=guidelines_file) 