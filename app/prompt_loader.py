# app/prompt_loader.py
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
PROMPT_DIR = APP_DIR / "prompt_store"
PROMPT_LATEST_FILE = PROMPT_DIR / "doc-llm-latest.md"

def load_latest_prompt() -> str | None:
    """加载最新的Prompt内容

    Returns:
        str | None: 如果文件存在，返回内容，否则返回None
    """
    try:
        with PROMPT_LATEST_FILE.open("r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"[WARN] Prompt file not found: {PROMPT_LATEST_FILE}")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to load prompt file: {repr(e)}")
        return None