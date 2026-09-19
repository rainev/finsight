from app.us_valuation.refresh_snapshot_cutoff import freeze_companyfacts


def test_late_companyfacts_rows_cannot_enter_earlier_snapshot():
    rows=[{'filed':'2026-09-17','accn':'older'},
          {'filed':'2026-09-18','accn':'early'},
          {'filed':'2026-09-18','accn':'late'},
          {'filed':'2026-09-19','accn':'tomorrow'},
          {'filed':'2026-09-18','accn':'unknown'}]
    packet={'submissions':{'filings':{'recent':{'accessionNumber':['early','late'],
        'acceptanceDateTime':['2026-09-18T19:00:00Z','2026-09-18T21:00:00Z']}}},
        'companyfacts':{'facts':{'us-gaap':{'Revenue':{'units':{'USD':rows}}}}}}
    result=freeze_companyfacts(packet,'2026-09-18T20:00:00+00:00')
    assert result['companyfacts']['facts']['us-gaap']['Revenue']['units']['USD']==rows[:2]
    assert result['companyfacts_snapshot_filter']['excluded_unproven_or_later_fact_rows']==3
    assert len(packet['companyfacts']['facts']['us-gaap']['Revenue']['units']['USD'])==5
