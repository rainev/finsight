#!/usr/bin/env python3
from app.db import pool,query
from app.pse_valuation.phase_b_batch_05 import FROZEN_BATCH_TICKERS,MODEL_VERSION
from app.storage import BUCKET,s3
def main():
 ids=[f"PSE:{t}" for t in FROZEN_BATCH_TICKERS];ph=", ".join(["%s"]*10);pool.open()
 try:
  secs=query(f"SELECT ticker FROM pse_securities WHERE ticker IN ({ph})",list(FROZEN_BATCH_TICKERS));docs=query(f"SELECT object_key FROM pse_documents WHERE issuer_id IN ({ph})",ids);facts=query(f"SELECT COUNT(*) count FROM pse_reported_facts f JOIN pse_documents d ON d.id=f.document_id WHERE d.issuer_id IN ({ph})",ids)[0]["count"];ass=query(f"SELECT COUNT(*) count FROM pse_assumptions WHERE version LIKE %s AND scope IN ({ph})",["%B05%",*FROZEN_BATCH_TICKERS])[0]["count"];runs=query("SELECT COUNT(*) count FROM pse_valuation_runs WHERE model_version=%s",[MODEL_VERSION])[0]["count"]
  for d in docs:s3.head_object(Bucket=BUCKET,Key=d["object_key"])
  actual={"securities":len(secs),"documents":len(docs),"reported_facts":int(facts),"assumptions":int(ass),"runs":int(runs),"minio_objects":len(docs)};expected={"securities":10,"documents":10,"reported_facts":46,"assumptions":174,"runs":10,"minio_objects":10}
  if actual!=expected:raise RuntimeError(f"persistence mismatch {actual}")
  print({"batch":MODEL_VERSION,**actual})
 finally:pool.close()
if __name__=="__main__":main()
