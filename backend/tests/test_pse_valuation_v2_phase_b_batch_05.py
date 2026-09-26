from __future__ import annotations
import hashlib,json,shutil
from pathlib import Path
import pytest
from app.pse_valuation.calculator import calculate,calculator_view
from app.pse_valuation.catalog import load_pointer
from app.pse_valuation.models.residual_income import residual_income_valuation
from app.pse_valuation.phase_b_batch_05 import FROZEN_BATCH_TICKERS,INTRINSIC_TICKERS,RELATIVE_TICKERS,build_batch_artifacts,load_batch_config,source_receipt
from app.routers import pse_valuations
from scripts.build_pse_v2_phase_b_batch_05 import PARENT_CATALOG_VERSION,build
from scripts import activate_pse_v2_phase_b_batch_05 as activation
ROOT=Path(__file__).parents[2];ACTIVE_ROOT=ROOT/"backend/app/data/pse_valuation_catalogs"
def tree(root):return {p.relative_to(root):p.read_bytes() for p in root.rglob("*") if p.is_file()}
def test_membership_routes_exact():
 assert FROZEN_BATCH_TICKERS==("PNB","RCB","UBP","AUB","PBB","PSB","COL","PSE","NRCP","MFIN")
 a=build_batch_artifacts();assert tuple(a)==FROZEN_BATCH_TICKERS;assert {t for t,r in a.items() if r.availability_type=="intrinsic_valuation"}==set(INTRINSIC_TICKERS);assert {t for t,r in a.items() if r.availability_type=="market_relative_only"}==set(RELATIVE_TICKERS)
def test_rejects_drift(tmp_path):
 c=load_batch_config();c["frozen_tickers"].append("EXTRA");p=tmp_path/"x.json";p.write_text(json.dumps(c))
 with pytest.raises(ValueError,match="confirmed frozen set"):load_batch_config(p)
def test_receipts_hash_bound():
 c=load_batch_config()
 for t in FROZEN_BATCH_TICKERS:
  r,b=source_receipt(t,c);assert hashlib.sha256(b).hexdigest()==r["sha256"];assert r["url"].startswith("https://")
def test_exact_values_and_separation():
 expected={"PNB":(83.55680919032517,113.31431277036152,150.77187807429993),"RCB":(28.871354936801264,38.399769751853746,50.310540755551),"UBP":(27.07968544733096,35.9930399661488,47.213057829695884),"AUB":(40.11543948927631,59.09562494355668,80.86950239234363),"PBB":(12.235716438571206,16.289360191746706,21.310293741210664),"PSB":(50.92987411861971,67.76197512861248,88.72933293404036),"COL":(0.30699023381987184,0.4753124046455236,0.7055261955048878),"PSE":(141.1,169.32,197.54),"NRCP":(1.814508339488318,2.5989260514658543,3.6361875869534224),"MFIN":(1.296,1.728,2.16)}
 for t,a in build_batch_artifacts().items():
  if t in INTRINSIC_TICKERS:obs=tuple(a.scenarios[n].value_per_share for n in ("bear","base","bull"));assert a.market_relative is None
  else:obs=tuple(a.market_relative["estimates"][n] for n in ("low","base","high"));assert all(v is None for v in a.scenarios.values());assert a.blocking_reasons
  assert obs==pytest.approx(expected[t]);assert a.public_assumptions["reliability"]=="Low"
def test_pnb_base_independent_reconciliation():
 a=build_batch_artifacts()["PNB"];v=a.public_assumptions["scenario_assumptions"]["base"];expected=residual_income_valuation(opening_common_equity=a.public_assumptions["book_value_per_share"],shares_outstanding=1.0,forecast_years=5,**v);assert a.scenarios["base"].value_per_share==pytest.approx(expected["value_per_share"])
def test_calculators_reproduce_and_move():
 for t,m in build_batch_artifacts().items():
  a=m.model_dump(mode="json");v=calculator_view(a);r=calculate(a,overrides={},scenario="base",manual_price=None);expected=a["scenarios"]["base"]["value_per_share"] if t in INTRINSIC_TICKERS else a["market_relative"]["estimates"]["base"];assert r["result"]["base"]==pytest.approx(expected)
  if t in INTRINSIC_TICKERS:e=calculate(a,overrides={"cost_of_equity":0.11},scenario="base",manual_price=None)
  else:e=calculate(a,overrides={"valuation_multiple":v["defaults"]["valuation_multiple"]+1 if t=="PSE" else v["defaults"]["valuation_multiple"]+0.1},scenario="base",manual_price=None)
  assert e["result"]["base"]>expected
def test_twins_preserve_active_48(tmp_path):
 before=tree(ACTIVE_ROOT);f=tmp_path/"f";s=tmp_path/"s";fc=build(f);build(s);assert tree(f)==tree(s);assert tree(ACTIVE_ROOT)==before;assert len(load_pointer(f).entries)==58
 parent=ACTIVE_ROOT/PARENT_CATALOG_VERSION;pm=json.loads((parent/"manifest.json").read_text())
 for row in pm["entries"]:assert (fc/"artifacts"/f"{row['ticker']}.json").read_bytes()==(parent/"artifacts"/f"{row['ticker']}.json").read_bytes()
def test_router_parity(tmp_path,monkeypatch):
 root=build(tmp_path);monkeypatch.setattr(pse_valuations,"CATALOGS_ROOT",tmp_path);monkeypatch.setattr(pse_valuations,"POINTER_NAME","staged.json");u={"sub":1,"role":"user"};listing=pse_valuations.list_pse_valuations(u);assert listing["count"]==58
 for t in FROZEN_BATCH_TICKERS:
  stored=json.loads((root/"artifacts"/f"{t}.json").read_text());served=pse_valuations.get_pse_valuation(t,u);assert {k:served[k] for k in stored}==stored;assert pse_valuations.get_pse_valuation_calculator(t,u)["can_calculate"]
def test_activation_preserves_batch04(tmp_path,monkeypatch):
 candidate=tmp_path/"candidate";build(candidate);serving=tmp_path/"serving";prev=activation.PREVIOUS_CATALOG_VERSION;shutil.copytree(ACTIVE_ROOT/prev,serving/prev);pm=serving/prev/"manifest.json";pointer={"schema_version":"FINSIGHT-PSE-VALUATION-POINTER-1.0","status":"active","catalog_version":prev,"catalog_path":prev,"manifest_sha256":hashlib.sha256(pm.read_bytes()).hexdigest()};(serving/"active.json").write_text(json.dumps(pointer));(serving/"staged.json").write_text(json.dumps({**pointer,"status":"staged"}));monkeypatch.setattr(activation,"SERVING_ROOT",serving);r=activation.activate(candidate);assert r["artifact_count"]==58;assert pm.is_file();assert load_pointer(serving,"active.json").status=="active"
