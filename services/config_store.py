import json
from pathlib import Path


DEFAULT_CONFIG = {
    "keep": {
        "phone_number": "",
        "password": "",
    },
    "ai": {
        "provider_name": "",
        "base_url": "",
        "api_key": "",
        "model": "",
    },
}


def load_config(config_path):
    config_path = Path(config_path)
    if not config_path.exists():
        return json.loads(json.dumps(DEFAULT_CONFIG))
    return json.loads(config_path.read_text(encoding="utf-8"))


def save_config(config_path, data):
    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

