"""Automatic startup must not erase legacy holdings or rewrite unrelated PSE rows."""
import pytest
from app import db_migrate

@pytest.mark.parametrize('column',['shares','avg_cost'])
def test_legacy_holdings_block_before_any_ddl(monkeypatch,column):
    calls=[]
    def read(statement):
        calls.append(statement)
        return [{'column_name':column}]
    monkeypatch.setattr(db_migrate,'query',read)
    with pytest.raises(RuntimeError,match='legacy holdings'):
        db_migrate.run_migrations()
    assert len(calls)==1 and calls[0].lstrip().startswith('SELECT')

def test_pending_pse_rows_block_before_any_ddl(monkeypatch):
    calls=[]
    def read(statement):
        calls.append(statement)
        if "table_name='holdings'" in statement:return []
        if 'information_schema.columns' in statement:return [{'column_name':'scenario'}]
        return [{'count':1}]
    monkeypatch.setattr(db_migrate,'query',read)
    with pytest.raises(RuntimeError,match='PSE scenario'):
        db_migrate.run_migrations()
    assert len(calls)==3 and all(s.lstrip().startswith('SELECT') for s in calls)

@pytest.mark.parametrize('existing_schema',[False,True])
def test_clean_and_fresh_startup_never_execute_data_changing_legacy_steps(monkeypatch,existing_schema):
    calls=[]
    def read(statement):
        calls.append(statement)
        if "table_name='holdings'" in statement:return []
        if 'information_schema.columns' in statement:return [{'column_name':'scenario'}] if existing_schema else []
        if statement.startswith('SELECT count(*)'):return [{'count':0}]
        return []
    monkeypatch.setattr(db_migrate,'query',read)
    db_migrate.run_migrations()
    ddl=[s for s in calls if not s.lstrip().startswith('SELECT')]
    assert ddl
    assert not any('DROP COLUMN' in s for s in ddl)
    assert not any(s.startswith('UPDATE pse_assumptions') for s in ddl)
    assert "CREATE EXTENSION IF NOT EXISTS vector" in ddl

def test_failed_fresh_precheck_is_fail_closed(monkeypatch):
    calls=[]
    def broken(statement):
        calls.append(statement)
        raise OSError('DB unavailable')
    monkeypatch.setattr(db_migrate,'query',broken)
    with pytest.raises(OSError):db_migrate.run_migrations()
    assert len(calls)==1 and calls[0].lstrip().startswith('SELECT')
