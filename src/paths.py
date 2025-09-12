import os
import sys
from typing import Optional


WINDOWS_DEFAULT_INSTALL_DIR = r"C:\ValirianEtiquetas"


def is_frozen() -> bool:
    return getattr(sys, 'frozen', False) is True


def get_app_base_dir() -> str:
    """Retorna o diretório base da aplicação.

    - Em build congelado (PyInstaller), utiliza a pasta do executável.
    - Em modo desenvolvimento, utiliza a raiz do projeto (do arquivo atual).
    """
    if is_frozen():
        # Pasta do executável (portátil)
        return os.path.dirname(sys.executable)
    # dev mode: raiz do projeto (.. de src)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def get_templates_dir() -> str:
    base = get_app_base_dir()
    return os.path.join(base, 'src', 'templates') if not is_frozen() else os.path.join(base, 'templates')


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


