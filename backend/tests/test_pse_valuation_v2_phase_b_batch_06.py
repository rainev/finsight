import hashlib,json
from pathlib import Path
import pytest
from app.pse_valuation.calculator import calculate
from app.pse_valuation.catalog import load_pointer
from app.pse_valuation.phase_b_batch_06 import FROZEN_BATCH_TICKERS,build_batch_artifacts,load_batch_config,source_receipt
from app.routers import pse_valuations
from scripts.build_pse_v2_phase_b_batch_06 import PARENT_CATALOG_VERSION,build
ROOT=Path(__file__).parents[2];ACTIVE=ROOT/"backend/app/data/pse_valuation_catalogs"
def tree(r):return {p.relative_to(r):p.read_bytes() for p in r.rglob("*") if p.is_file()}
def test_membership_and_values():
 a=build_batch_artifacts();assert tuple(a)==FROZEN_BATCH_TICKERS;assert all(x.availability_type=="market_relative_only" for x in a.values())
 expected={"TEL":1277.8,"GLO":1512.1,"CNVRG":13.952,"DITO":0.7647704401144799,"NOW":1.0,"GMA7":3.6,"ABS":3.1160477679936034,"MB":0.6,"DFNN":0.4231512495,"PLUS":22.48}
 for t,v in expected.items():assert a[t].market_relative["estimates"]["base"]==pytest.approx(v)
def test_receipts_and_calculators():
 c=load_batch_config()
 for t,a in build_batch_artifacts(c).items():
  r,b=source_receipt(t,c);assert hashlib.sha256(b).hexdigest()==r["sha256"];payload=a.model_dump(mode="json");result=calculate(payload,overrides={},scenario="base",manual_price=None);assert result["result"]["base"]==pytest.approx(payload["market_relative"]["estimates"]["base"])
def test_twins_and_active_preserved(tmp_path):
 before=tree(ACTIVE);f=tmp_path/"f";s=tmp_path/"s";fc=build(f);build(s);assert tree(f)==tree(s);assert tree(ACTIVE)==before;assert len(load_pointer(f).entries)==68;parent=ACTIVE/PARENT_CATALOG_VERSION;pm=json.loads((parent/"manifest.json").read_text());
 for row in pm["entries"]:assert (fc/"artifacts"/f"{row['ticker']}.json").read_bytes()==(parent/"artifacts"/f"{row['ticker']}.json").read_bytes()
def test_router_parity(tmp_path,monkeypatch):
 root=build(tmp_path);monkeypatch.setattr(pse_valuations,"CATALOGS_ROOT",tmp_path);monkeypatch.setattr(pse_valuations,"POINTER_NAME","staged.json");u={"sub":1,"role":"user"};assert pse_valuations.list_pse_valuations(u)["count"]==68
 for t in FROZEN_BATCH_TICKERS:stored=json.loads((root/"artifacts"/f"{t}.json").read_text());served=pse_valuations.get_pse_valuation(t,u);assert {k:served[k] for k in stored}==stored
