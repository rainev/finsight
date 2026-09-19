"""Keep late-retrieved Companyfacts inside a frozen discovery timestamp."""
from copy import deepcopy
from datetime import datetime, timezone, date, time, timedelta
from zoneinfo import ZoneInfo


def freeze_submissions(submissions, snapshot_timestamp):
    stamp=datetime.fromisoformat(snapshot_timestamp.replace('Z','+00:00'))
    if stamp.tzinfo is None:raise ValueError('snapshot timestamp must include timezone')
    result=deepcopy(submissions)
    recent=result['filings']['recent']
    indices=[]
    for i,accession in enumerate(recent['accessionNumber']):
        accepted=recent.get('acceptanceDateTime',[])
        if i>=len(accepted) or not accepted[i]:continue
        instant=datetime.fromisoformat(accepted[i].replace('Z','+00:00'))
        if instant.tzinfo is None:raise ValueError('filing acceptance timestamp must include timezone')
        if instant<=stamp:indices.append(i)
    result['filings']['recent']={key:[values[i] for i in indices] if isinstance(values,list) else values
        for key,values in recent.items()}
    return result


def freeze_companyfacts(packet, snapshot_timestamp):
    stamp=datetime.fromisoformat(snapshot_timestamp.replace('Z','+00:00'))
    if stamp.tzinfo is None:raise ValueError('snapshot timestamp must include timezone')
    stamp=stamp.astimezone(timezone.utc)
    day=stamp.date().isoformat()
    recent=packet['submissions']['filings']['recent']
    eligible=set()
    for i,accession in enumerate(recent['accessionNumber']):
        accepted=recent.get('acceptanceDateTime',[])
        if i>=len(accepted) or not accepted[i]:continue
        value=datetime.fromisoformat(accepted[i].replace('Z','+00:00'))
        if value.tzinfo is None:raise ValueError('filing acceptance timestamp must include timezone')
        if value<=stamp:eligible.add(accession)
    result=deepcopy(packet['companyfacts'])
    day_closed={}
    included=excluded=0
    for namespace in result.get('facts',{}).values():
        for concept in namespace.values():
            for unit,rows in concept.get('units',{}).items():
                kept=[]
                for row in rows:
                    filed=row.get('filed')
                    # SEC filing dates use Eastern time. Only a fully elapsed
                    # filing day is safe without accession-level acceptance.
                    if isinstance(filed,str) and filed not in day_closed:
                        try:
                            end=datetime.combine(date.fromisoformat(filed)+timedelta(days=1),time(),ZoneInfo('America/New_York'))
                            day_closed[filed]=end<=stamp
                        except ValueError:day_closed[filed]=False
                    allowed=isinstance(filed,str) and (day_closed.get(filed,False) or (filed<=day and row.get('accn') in eligible))
                    if allowed:kept.append(row);included+=1
                    else:excluded+=1
                concept['units'][unit]=kept
    return {**packet,'companyfacts':result,'companyfacts_snapshot_filter':{
        'version':'FINSIGHT-ACCEPTANCE-CUTOFF-1','snapshot_timestamp':snapshot_timestamp,
        'included_fact_rows':included,'excluded_unproven_or_later_fact_rows':excluded,
        'raw_source_hashes_preserved':True}}
