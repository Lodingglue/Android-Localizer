#!/usr/bin/env python3

import os
import sys
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET

from openai import OpenAI
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from rich.table import Table

console = Console()

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    console.print(
        "[red]OPENAI_API_KEY not found in .env file[/red]"
    )
    sys.exit(1)


LANGUAGES = {
    "ja": "Japanese",
    "ko": "Korean",
    "zh-rCN": "Simplified Chinese",
    "zh-rTW": "Traditional Chinese",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "ru": "Russian",
    "it": "Italian",
    "pt": "Portuguese",
    "tr": "Turkish",
    "ar": "Arabic",
    "hi": "Hindi",
}

PROMPT_TEMPLATE = """
You are a professional Android localization translator.

Translate all user-visible text inside this Android strings.xml file into {language}.

Rules:

- Translate ONLY string values.
- NEVER modify string names.
- Preserve valid Android XML.
- Preserve placeholders exactly:
  %s
  %d
  %1$s
  %1$d
  %2$s
  etc.

- Preserve escaped characters:
  \\n
  \\\'
  \\"

- Preserve XML tags and attributes.
- Preserve formatting.
- Preserve app names such as Myobu and Myōbu unless localization requires otherwise.
- Keep translations natural for native speakers.
- Keep UI labels concise.
- Preserve translatable="false" attributes.
- Do not add comments.
- Do not add explanations.
- Do not wrap output in markdown.
- Do not use code fences.
- Return ONLY the complete XML document.

XML TO TRANSLATE:

{xml_content}
"""


def validate_xml(xml_text: str) -> bool:
    try:
        ET.fromstring(xml_text)
        return True
    except Exception:
        return False


def clean_response(text: str) -> str:
    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines:
            lines = lines[1:]

        while lines and lines[-1].strip() == "```":
            lines.pop()

        text = "\n".join(lines)

    return text.strip()


def translate_xml(client, xml_content, language):
    prompt = PROMPT_TEMPLATE.format(
        language=language,
        xml_content=xml_content
    )

    for attempt in range(3):
        response = client.responses.create(
            model="gpt-5.4-mini",
            input=prompt
        )

        text = response.output_text
        text = clean_response(text)

        if validate_xml(text):
            return text

        console.print(
            f"[yellow]Retrying XML validation ({attempt + 1}/3)...[/yellow]"
        )

    raise RuntimeError(
        f"Failed to obtain valid XML for {language}"
    )


def save_translation(
    output_root,
    qualifier,
    translated_xml
):
    folder = Path(output_root) / f"values-{qualifier}"
    folder.mkdir(parents=True, exist_ok=True)

    output_file = folder / "strings.xml"

    output_file.write_text(
        translated_xml,
        encoding="utf-8"
    )


def main():
    console.print(
        Panel.fit(
            "[bold cyan]Android strings.xml Translator[/bold cyan]\n"
            "Powered by OpenAI",
            border_style="cyan"
        )
    )


    xml_path = Prompt.ask(
        "Path to strings.xml"
    ).strip()

    xml_file = Path(xml_path)

    if not xml_file.exists():
        console.print(
            "[red]File does not exist.[/red]"
        )
        sys.exit(1)

    try:
        xml_content = xml_file.read_text(
            encoding="utf-8"
        )
    except Exception as e:
        console.print(
            f"[red]Failed reading file:[/red] {e}"
        )
        sys.exit(1)

    if not validate_xml(xml_content):
        console.print(
            "[red]Input XML is invalid.[/red]"
        )
        sys.exit(1)

    timestamp = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    output_root = (
        Path.cwd()
        / f"translations_{timestamp}"
    )

    output_root.mkdir(
        parents=True,
        exist_ok=True
    )

    client = OpenAI(
        api_key=api_key
    )

    table = Table(title="Languages")

    table.add_column("Qualifier")
    table.add_column("Language")

    for qualifier, language in LANGUAGES.items():
        table.add_row(
            qualifier,
            language
        )

    console.print(table)

    with Progress(
        SpinnerColumn(),
        TextColumn(
            "[progress.description]{task.description}"
        ),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:

        task = progress.add_task(
            "Translating...",
            total=len(LANGUAGES)
        )

        for qualifier, language in LANGUAGES.items():

            progress.update(
                task,
                description=f"Translating {language}"
            )

            try:
                translated_xml = translate_xml(
                    client,
                    xml_content,
                    language
                )

                save_translation(
                    output_root,
                    qualifier,
                    translated_xml
                )

                console.print(
                    f"[green]✓[/green] {language}"
                )

            except Exception as e:
                console.print(
                    f"[red]✗ {language}: {e}[/red]"
                )

            progress.advance(task)

    console.print()

    console.print(
        Panel.fit(
            f"[green]Completed[/green]\n\n"
            f"Output Folder:\n"
            f"{output_root}",
            border_style="green"
        )
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print(
            "\n[yellow]Cancelled by user.[/yellow]"
        )