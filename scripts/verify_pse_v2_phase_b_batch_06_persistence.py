from app.db import pool,query
from app.pse_valuation.phase_b_batch_06 import FROZEN_BATCH_TICKERS,MODEL_VERSION
from app.storage import BUCKET,s3
def main():
 ids=[f"PSE:{t}" for t in FROZEN_BATCH_TICKERS];ph=", ".join(["%s"]*10);pool.open()
 try:
  docs=query(f"SELECT object_key FROM pse_documents WHERE issuer_id IN ({ph})",ids);facts=query(f"SELECT COUNT(*) count FROM pse_reported_facts f JOIN pse_documents d ON d.id=f.document_id WHERE d.issuer_id IN ({ph})",ids)[0]["count"];ass=query(f"SELECT COUNT(*) count FROM pse_assumptions WHERE version LIKE %s AND scope IN ({ph})",["%B06%",*FROZEN_BATCH_TICKERS])[0]["count"];runs=query("SELECT COUNT(*) count FROM pse_valuation_runs WHERE model_version=%s",[MODEL_VERSION])[0]["count"]
  for d in docs:s3.head_object(Bucket=BUCKET,Key=d["object_key"])
  actual=(len(docs),int(facts),int(ass),int(runs));assert actual==(10,10,30,10),actual;print({"documents":10,"facts":10,"assumptions":30,"runs":10,"objects":10})
 finally:pool.close()
if __name__=="__main__":main()
