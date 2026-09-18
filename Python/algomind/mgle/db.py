"""
ALGOMIND MACRO / GEOPOLITICAL / GOLD / PROXY-OPTIONS LAYER (MGLE)
==================================================================
Point-in-Time (PIT) Causal Storage Engine (v1.0)
Guarantees strict publication timestamp gating to eliminate future data leakage.
"""

from __future__ import annotations
import sqlite3
import json
import os
from typing import List, Optional
from algomind.mgle.schema import ExternalObservation, DataQualityTag

class MGLEDatabase:
    def __init__(self, db_path: str = "Python/algomind_mgle_pit.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS observations (
                    obs_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    dataset_id TEXT NOT NULL,
                    series_id TEXT NOT NULL,
                    instrument TEXT NOT NULL,
                    observation_ts INTEGER NOT NULL,
                    publication_ts INTEGER NOT NULL,
                    retrieval_ts INTEGER NOT NULL,
                    unit TEXT NOT NULL,
                    value REAL NOT NULL,
                    quality_tag INTEGER NOT NULL,
                    revision_version INTEGER DEFAULT 1,
                    metadata_json TEXT,
                    UNIQUE(source_id, series_id, observation_ts, revision_version)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_pit_lookup 
                ON observations(series_id, publication_ts, observation_ts)
            """)

    def insert_observation(self, obs: ExternalObservation) -> bool:
        """Insert observation into SQLite database with provenance metadata."""
        query = """
            INSERT OR REPLACE INTO observations (
                source_id, dataset_id, series_id, instrument,
                observation_ts, publication_ts, retrieval_ts,
                unit, value, quality_tag, revision_version, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            with self._get_connection() as conn:
                conn.execute(query, (
                    obs.source_id, obs.dataset_id, obs.series_id, obs.instrument,
                    obs.observation_timestamp, obs.publication_timestamp, obs.retrieval_timestamp,
                    obs.unit, obs.value, int(obs.quality_tag), obs.revision_version,
                    json.dumps(obs.metadata)
                ))
            return True
        except Exception as e:
            print(f"[MGLEDatabase] Insert error: {e}")
            return False

    def query_pit_series(self, series_id: str, as_of_ts: int, limit: int = 100) -> List[ExternalObservation]:
        """
        CAUSAL PIT QUERY: Returns historical series available AS OF as_of_ts.
        Strictly enforces: publication_timestamp <= as_of_ts.
        """
        query = """
            SELECT * FROM observations
            WHERE series_id = ? AND publication_ts <= ?
            ORDER BY observation_ts DESC, revision_version DESC
            LIMIT ?
        """
        results: List[ExternalObservation] = []
        with self._get_connection() as conn:
            rows = conn.execute(query, (series_id, as_of_ts, limit)).fetchall()
            for r in rows:
                meta = json.loads(r['metadata_json']) if r['metadata_json'] else {}
                results.append(ExternalObservation(
                    source_id=r['source_id'],
                    dataset_id=r['dataset_id'],
                    series_id=r['series_id'],
                    instrument=r['instrument'],
                    observation_timestamp=r['observation_ts'],
                    publication_timestamp=r['publication_ts'],
                    retrieval_timestamp=r['retrieval_ts'],
                    unit=r['unit'],
                    value=r['value'],
                    quality_tag=DataQualityTag(r['quality_tag']),
                    revision_version=r['revision_version'],
                    metadata=meta
                ))
        return results
