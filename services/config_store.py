import json
from pathlib import Path


DEFAULT_CONFIG = {
    "keep": {
        "phone_number": "",
        "password": "",
    },
    "models": [],
}


def normalize_config(data):
    data = data or {}
    keep_config = data.get("keep", {})
    models = list(data.get("models") or [])

    legacy_ai = data.get("ai")
    if legacy_ai and not models:
        model_key = (
            legacy_ai.get("provider_name")
            or legacy_ai.get("model")
            or "default-model"
        )
        models.append(
            {
                "key": model_key,
                "label": model_key,
                "provider_name": legacy_ai.get("provider_name", ""),
                "base_url": legacy_ai.get("base_url", ""),
                "api_key": legacy_ai.get("api_key", ""),
                "model": legacy_ai.get("model", ""),
            }
        )

    normalized_models = []
    for index, item in enumerate(models):
        key = item.get("key") or item.get("provider_name") or item.get("model") or f"model-{index + 1}"
        normalized_models.append(
            {
                "key": key,
                "label": item.get("label") or key,
                "provider_name": item.get("provider_name", ""),
                "base_url": item.get("base_url", ""),
                "api_key": item.get("api_key", ""),
                "model": item.get("model", ""),
            }
        )

    return {
        "keep": {
            "phone_number": keep_config.get("phone_number", ""),
            "password": keep_config.get("password", ""),
        },
        "models": normalized_models,
    }


def load_config(config_path):
    config_path = Path(config_path)
    if not config_path.exists():
        return json.loads(json.dumps(DEFAULT_CONFIG))
    raw_data = json.loads(config_path.read_text(encoding="utf-8"))
    return normalize_config(raw_data)


def save_config(config_path, data):
    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_config(data)
    config_path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
