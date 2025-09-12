import os
from typing import Optional, Tuple

from db.sqlite_db import get_default_template_config, set_setting
from paths import get_templates_dir
from dotenv import dotenv_values

ENV_PATH = os.path.join(os.path.dirname(__file__), '.env')


DEFAULT_TEMPLATE_DIR = get_templates_dir()
DEFAULT_TEMPLATE_FILE = 'etiqueta_template.docx'


def get_template_path_from_settings() -> str:
    cfg = get_default_template_config()
    template_dir = cfg.get('template_dir') or DEFAULT_TEMPLATE_DIR
    template_file = cfg.get('template_file') or DEFAULT_TEMPLATE_FILE
    return os.path.join(template_dir, template_file)


def prompt_for_template_path() -> Tuple[str, bool]:
    """
    Pergunta ao usuário se deseja usar o modelo padrão. Retorna:
    - caminho do template escolhido
    - se deseja salvar este caminho como novo padrão
    """
    try:
        default_path = get_template_path_from_settings()
        print(f"\nModelo padrão atual: {default_path}")
        usar_padrao = input("Usar o modelo padrão? (Enter = sim, n = não): ").strip().lower()

        if usar_padrao in ['', 's', 'sim', 'y', 'yes']:
            return default_path, False

        caminho = input("Informe o caminho completo do modelo (.docx): ").strip()
        if not caminho:
            # Se usuário não informou, retorna padrão
            return default_path, False

        salvar_novo = input("Deseja tornar este o novo modelo padrão? (s/n): ").strip().lower()
        return caminho, salvar_novo in ['s', 'sim', 'y', 'yes']
    except Exception:
        # fallback para padrão se algo der errado
        return get_template_path_from_settings(), False


def save_template_as_default(template_path: str) -> None:
    template_dir = os.path.dirname(template_path)
    template_file = os.path.basename(template_path)
    set_setting('template_dir', template_dir)
    set_setting('template_file', template_file)


# ------------------------
# .env helpers
# ------------------------

def read_env() -> dict:
    try:
        return dotenv_values(ENV_PATH) or {}
    except Exception:
        return {}


def write_env(updates: dict) -> None:
    env = read_env()
    env.update({k: '' if v is None else str(v) for k, v in updates.items()})
    lines = [f"{k}={env[k]}" for k in sorted(env.keys())]
    with open(ENV_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))


def get_start_mode() -> str:
    env = read_env()
    # values: 'cli' | 'gui' | 'ask'
    return env.get('START_MODE', 'ask').lower()



