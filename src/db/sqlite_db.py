import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from paths import get_app_base_dir, ensure_dir, is_frozen
from datetime import datetime


BASE_DIR = get_app_base_dir()
DB_DIR = os.path.join(BASE_DIR, 'db') if is_frozen() else os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db')
DB_PATH = os.path.join(DB_DIR, 'valirian.db')


def _ensure_db_dir() -> None:
    ensure_dir(DB_DIR)


def get_connection() -> sqlite3.Connection:
    _ensure_db_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema() -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            PRAGMA foreign_keys = ON;
            """
        )

        # Tabela de receitas (recipe)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS recipes (
                id TEXT PRIMARY KEY,
                name TEXT,
                style TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # Tabela de batches (lotes)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS batches (
                id TEXT PRIMARY KEY,
                batch_no INTEGER,
                brewer TEXT,
                brew_date TEXT,
                name TEXT,
                measured_abv REAL,
                estimated_ibu REAL,
                estimated_color REAL,
                recipe_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recipe_id) REFERENCES recipes(id)
            );
            """
        )

        # Tabela de eventos do batch
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS batch_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT NOT NULL,
                event_type TEXT,
                time_ts INTEGER,
                time_human TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (batch_id) REFERENCES batches(id)
            );
            """
        )

        # Tabela de configurações da aplicação (chave/valor)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # Tabela de overrides (edições manuais) de um batch para impressão
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS batch_overrides (
                batch_id TEXT PRIMARY KEY,
                name TEXT,
                brew_date TEXT,
                measured_abv TEXT,
                estimated_ibu TEXT,
                estimated_color TEXT,
                observation TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (batch_id) REFERENCES batches(id)
            );
            """
        )

        # Tabela de tags livres (pares chave/valor) por batch
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS batch_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT NOT NULL,
                tag_key TEXT NOT NULL,
                tag_value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(batch_id, tag_key),
                FOREIGN KEY (batch_id) REFERENCES batches(id)
            );
            """
        )

        # Histórico de alterações
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS batch_overrides_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT NOT NULL,
                name TEXT,
                brew_date TEXT,
                measured_abv TEXT,
                estimated_ibu TEXT,
                estimated_color TEXT,
                observation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (batch_id) REFERENCES batches(id)
            );
            """
        )

        conn.commit()
    finally:
        conn.close()


def upsert_recipe(recipe: Optional[Dict[str, Any]]) -> Optional[str]:
    if not recipe:
        return None
    recipe_id = recipe.get('id') or recipe.get('_id')
    if not recipe_id:
        # Algumas respostas não trazem id da receita; não criamos registro órfão
        return None
    name = recipe.get('name')
    style = recipe.get('style', {}).get('name') if isinstance(recipe.get('style'), dict) else recipe.get('style')

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO recipes (id, name, style)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                style=excluded.style
            ;
            """,
            (recipe_id, name, style),
        )
        conn.commit()
        return recipe_id
    finally:
        conn.close()


def upsert_batch(batch: Dict[str, Any]) -> str:
    batch_id = batch.get('_id') or batch.get('id')
    if not batch_id:
        raise ValueError('Batch sem _id/id não pode ser persistido')

    # Pode vir tanto "name" direto quanto dentro de recipe
    recipe = batch.get('recipe') if isinstance(batch.get('recipe'), dict) else None
    recipe_id = upsert_recipe(recipe)

    name = batch.get('name') or (recipe.get('name') if recipe else None)

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO batches (
                id, batch_no, brewer, brew_date, name, measured_abv, estimated_ibu, estimated_color, recipe_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                batch_no=excluded.batch_no,
                brewer=excluded.brewer,
                brew_date=excluded.brew_date,
                name=excluded.name,
                measured_abv=excluded.measured_abv,
                estimated_ibu=excluded.estimated_ibu,
                estimated_color=excluded.estimated_color,
                recipe_id=excluded.recipe_id
            ;
            """,
            (
                batch_id,
                batch.get('batchNo'),
                batch.get('brewer'),
                batch.get('brewDate'),  # já vem formatada no serviço listBatches/listBatch
                name,
                batch.get('measuredAbv'),
                batch.get('estimatedIbu'),
                batch.get('estimatedColor'),
                recipe_id,
            ),
        )
        conn.commit()
        return batch_id
    finally:
        conn.close()


def insert_batch_event(batch_id: str, event: Dict[str, Any]) -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO batch_events (batch_id, event_type, time_ts, time_human)
            VALUES (?, ?, ?, ?)
            ;
            """,
            (
                batch_id,
                event.get('eventType') or event.get('event_type'),
                event.get('timestamp') or event.get('time'),
                event.get('time') if isinstance(event.get('time'), str) else event.get('time_human'),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def upsert_batch_with_events(batch: Dict[str, Any]) -> str:
    batch_id = upsert_batch(batch)
    bottling = batch.get('bottling_event')
    if bottling:
        insert_batch_event(batch_id, bottling)
    return batch_id


def fetch_batches(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, batch_no, brewer, brew_date, name, measured_abv, estimated_ibu, estimated_color, recipe_id
            FROM batches
            ORDER BY created_at DESC
            LIMIT ?
            ;
            """,
            (limit,),
        )
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def fetch_batches_filtered(limit: int = 50, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """Busca lotes do banco e aplica filtro por data (dd/mm/YYYY) em Python.

    - start_date/end_date: strings dd/mm/YYYY ou None
    - limit: máximo de registros retornados
    """
    rows = fetch_batches(10000)  # busca ampla e filtra em memória
    def parse(d: Optional[str]) -> Optional[datetime]:
        if not d:
            return None
        try:
            return datetime.strptime(d, '%d/%m/%Y')
        except Exception:
            return None
    sd = parse(start_date)
    ed = parse(end_date)
    filtered: List[Dict[str, Any]] = []
    for r in rows:
        bd = parse(r.get('brew_date'))
        if sd and (not bd or bd < sd):
            continue
        if ed and (not bd or bd > ed):
            continue
        filtered.append(r)
        if len(filtered) >= limit:
            break
    return filtered


def get_batch_by_id(batch_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, batch_no, brewer, brew_date, name, measured_abv, estimated_ibu, estimated_color, recipe_id
            FROM batches
            WHERE id = ?
            """,
            (batch_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def fetch_batch_events(batch_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT event_type, time_ts, time_human, created_at
            FROM batch_events
            WHERE batch_id = ?
            ORDER BY created_at DESC
            ;
            """,
            (batch_id,),
        )
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# ------------------------
# Configurações (key/value)
# ------------------------

def set_setting(key: str, value: str) -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value=excluded.value,
                updated_at=CURRENT_TIMESTAMP
            ;
            """,
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()


def get_setting(key: str) -> Optional[str]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def get_default_template_config() -> Dict[str, Optional[str]]:
    """Retorna diretório e nome de arquivo padrão do template, se definidos."""
    return {
        'template_dir': get_setting('template_dir'),
        'template_file': get_setting('template_file'),
    }


# ------------------------
# Overrides e Tags
# ------------------------

def upsert_batch_override(batch_id: str, overrides: Dict[str, Optional[str]], observation: Optional[str]) -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Grava histórico antes
        cur.execute(
            """
            INSERT INTO batch_overrides_history (batch_id, name, brew_date, measured_abv, estimated_ibu, estimated_color, observation)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                batch_id,
                overrides.get('name'),
                overrides.get('brewDate'),
                overrides.get('measuredAbv'),
                overrides.get('estimatedIbu'),
                overrides.get('estimatedColor'),
                observation,
            ),
        )
        cur.execute(
            """
            INSERT INTO batch_overrides (batch_id, name, brew_date, measured_abv, estimated_ibu, estimated_color, observation, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(batch_id) DO UPDATE SET
                name=excluded.name,
                brew_date=excluded.brew_date,
                measured_abv=excluded.measured_abv,
                estimated_ibu=excluded.estimated_ibu,
                estimated_color=excluded.estimated_color,
                observation=excluded.observation,
                updated_at=CURRENT_TIMESTAMP
            ;
            """,
            (
                batch_id,
                overrides.get('name'),
                overrides.get('brewDate'),
                overrides.get('measuredAbv'),
                overrides.get('estimatedIbu'),
                overrides.get('estimatedColor'),
                observation,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_batch_override(batch_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT batch_id, name, brew_date, measured_abv, estimated_ibu, estimated_color, observation, updated_at
            FROM batch_overrides
            WHERE batch_id = ?
            """,
            (batch_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def set_tag(batch_id: str, key: str, value: Optional[str]) -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO batch_tags (batch_id, tag_key, tag_value)
            VALUES (?, ?, ?)
            ON CONFLICT(batch_id, tag_key) DO UPDATE SET
                tag_value=excluded.tag_value
            ;
            """,
            (batch_id, key, value),
        )
        conn.commit()
    finally:
        conn.close()


def delete_tag(batch_id: str, key: str) -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM batch_tags WHERE batch_id = ? AND tag_key = ?", (batch_id, key))
        conn.commit()
    finally:
        conn.close()


def list_tags(batch_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT tag_key, tag_value, created_at
            FROM batch_tags
            WHERE batch_id = ?
            ORDER BY tag_key ASC
            """,
            (batch_id,),
        )
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def list_overridden_batches(limit: int = 100) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT b.id,
                   b.batch_no,
                   COALESCE(o.name, b.name) AS name,
                   MAX(COALESCE(o.updated_at, h.created_at)) AS updated_at
            FROM batches b
            LEFT JOIN batch_overrides o ON o.batch_id = b.id
            LEFT JOIN batch_overrides_history h ON h.batch_id = b.id
            GROUP BY b.id, b.batch_no, COALESCE(o.name, b.name)
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_batch_with_overrides(batch_id: str) -> Optional[Dict[str, Any]]:
    """Retorna os campos do batch mesclando overrides quando existirem."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT b.id,
                   b.batch_no,
                   COALESCE(o.name, b.name) AS name,
                   COALESCE(o.brew_date, b.brew_date) AS brew_date,
                   COALESCE(o.measured_abv, b.measured_abv) AS measured_abv,
                   COALESCE(o.estimated_ibu, b.estimated_ibu) AS estimated_ibu,
                   COALESCE(o.estimated_color, b.estimated_color) AS estimated_color
            FROM batches b
            LEFT JOIN batch_overrides o ON o.batch_id = b.id
            WHERE b.id = ?
            """,
            (batch_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


