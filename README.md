## Android Strings Translator

Translates an Android `strings.xml` file into multiple languages using OpenAI.

### Install

```bash
pip install openai rich python-dotenv
```

### Setup

Create a `.env` file:

```env
OPENAI_API_KEY=your_api_key_here
```

Put your `strings.xml` file in the same folder as the script or provide its path when running.

### Run

```bash
python translate_strings.py
```

Enter the path to your `strings.xml` when prompted.


