"""Verificação local adicional de backup online, sem integração ou rede externa."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
ENV = {k: v for k, v in os.environ.items()
       if not k.startswith(('EVOLUTION_', 'TELEGRAM_', 'WEBHOOK_'))}
ENV['RESERVA_AGORA'] = '2026-10-06T09:00'


def cli(*args):
    subprocess.run([str(ROOT / 'reserva'), *args], cwd=ROOT, env=ENV,
                   check=True, timeout=30, capture_output=True)


def snapshot(directory):
    with sqlite3.connect(directory / 'reserva.sqlite3') as db:
        assert db.execute('PRAGMA integrity_check').fetchone() == ('ok',)
        return list(db.iterdump())


with tempfile.TemporaryDirectory(prefix='reserva-backup-') as work:
    work = Path(work)
    directory = work / 'dados'
    server = subprocess.Popen([str(ROOT / 'reserva'), 'serve', '--porta', '0',
                               '--dados', str(directory)], env=ENV, cwd=ROOT,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        line = server.stdout.readline().strip()
        assert line.startswith('PORTA='), line
        base = 'http://127.0.0.1:' + line.split('=', 1)[1]
        config = (directory / 'pousada.json').read_bytes()
        token = json.loads(config)['token']

        def post(path, body):
            request = urllib.request.Request(base + path, json.dumps(body).encode(),
                headers={'Content-Type': 'application/json', 'X-Token': token})
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.load(response)

        post('/api/hospedes', {'nome': 'Antes', 'telefone': '11987654321'})
        post('/api/mensagens', {'telefone': '11987654321', 'texto': 'reservar'})
        before = snapshot(directory)
        cli('backup', '--dados', str(directory), '--saida', str(work / 'backup.zip'))
        post('/api/hospedes', {'nome': 'Depois', 'telefone': '21987654321'})
        assert snapshot(directory) != before
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)
    cli('restaurar', '--dados', str(directory), '--entrada', str(work / 'backup.zip'))
    assert snapshot(directory) == before
    assert (directory / 'pousada.json').read_bytes() == config
    print('BACKUP ONLINE OK: banco completo, conversa e configuração restaurados; escrita posterior removida')
