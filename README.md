# News Aggregator: AI Editor-in-Chief

This project implements an **AI Editor-in-Chief** paradigm: an automated system that monitors a list of Telegram channels (news sources), reviews each new message, translates it into English using OpenAI, and reposts both the original and translated text to a designated Telegram channel. The AI acts as an editor-in-chief, curating and distributing news to your audience.

The Bot receives updates from multiple sources (in the current version: telegram channels), and forwards them to other telegram channel.

## Setup
1. Install Python 3.8+ and the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Obtain Telegram `API_ID` and `API_HASH` from [https://my.telegram.org](https://my.telegram.org).
3. Generate an [OpenAI API key](https://platform.openai.com) and set `OPENAI_API_KEY`.
4. Run the script once to generate a session file and log in.

## System Prompt Configuration

The AI Editor-in-Chief uses a modular system prompt structure that combines a base prompt with customizable editorial guidelines. This allows you to fine-tune the AI's decision-making criteria without modifying the core application code.

### Editorial Guidelines

The editorial guidelines are defined in `system_prompt_editorial_guidelines.txt` and include:

1. **Translation**: Ensures all content is translated to fluent English while preserving links
2. **Verification**: Filters out fake news, clickbait, and low-quality content
3. **Advertisement Filtering**: Rejects commercial advertisements and promotional content
4. **Event Relevance**: Only includes internationally relevant events
5. **Geopolitical Filter**: Excludes content from sanctioned countries unless critically important
6. **Editorial Judgment**: Prioritizes high-quality, globally relevant journalism
7. **Repost Decision**: Provides clear reasoning for each decision

### Customization

To customize the editorial guidelines:

1. Edit the `system_prompt_editorial_guidelines.txt` file to modify the decision criteria
2. Alternatively, create a custom guidelines file and set the environment variable:
   ```bash
   export system_prompt_editorial_guidelines_FILE=path/to/your/custom_guidelines.txt
   ```

The system automatically combines the base prompt template with your guidelines to create the complete system prompt used by the AI.

## Usage
Set the required environment variables and run the script:

```bash
export TELEGRAM_API_ID=your_api_id
export TELEGRAM_API_HASH=your_api_hash
export SOURCE_CHANNELS="channel1,channel2"
export TARGET_CHANNEL="@your_target_channel"
export OPENAI_API_KEY=your_openai_key
python app.py
```

`SOURCE_CHANNELS` should be a comma‑separated list of channel usernames or IDs. The account must have access to these channels.

The AI Editor-in-Chief will listen for new messages from the source channels, translate them to English, and repost the original text along with its translation to the target channel. This mimics the workflow of a human editor-in-chief, ensuring your Telegram channel receives curated, translated news updates automatically.
