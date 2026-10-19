"""Portable snapshot: SQLite online backup plus the local configuration."""
import sqlite3
import tempfile
import zipfile
from pathlib import Path
from .domain import Store


def backup(directory, output):
    store = Store(directory)
    destination = Path(output)
    temporary = destination.with_name(destination.name+'.tmp')
    with tempfile.TemporaryDirectory() as work:
        snapshot = Path(work)/'reserva.sqlite3'
        source = store.connect()
        target = sqlite3.connect(snapshot)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.write(snapshot, 'reserva.sqlite3')
            archive.write(Path(directory)/'pousada.json', 'pousada.json')
        temporary.replace(destination)


def restore(directory, source):
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as archive, tempfile.TemporaryDirectory(dir=destination) as work:
        for name in ('reserva.sqlite3', 'pousada.json'):
            (Path(work)/name).write_bytes(archive.read(name))
        with sqlite3.connect(Path(work)/'reserva.sqlite3') as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Backup inválido')
        for name in ('reserva.sqlite3', 'pousada.json'):
            (Path(work)/name).replace(destination/name)
