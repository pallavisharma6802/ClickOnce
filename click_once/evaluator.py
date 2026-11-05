"""Independent evaluation recomputes outcomes from private records, not reward labels."""
def evaluate_audit(audit):
    all_records=audit['records']
    records=[r for r in all_records if r['target']==audit['goal']]
    # V1 has no unrelated initial records. V2 must preserve every original record.
    initial=audit.get('initial_records',[])
    collateral_ok=all(r in all_records for r in initial)
    unexpected=[r for r in all_records if r['target']!=audit['goal'] and r not in initial]
    collateral_ok=collateral_ok and not unexpected
    confirmed=sum(r['status']=='confirmed' and r['target']==audit['goal'] for r in records)
    pending=sum(r['status']=='pending' for r in records)
    duplicates=max(0,len(records)-1)
    strict=bool(collateral_ok and audit['finished'] and not audit['truncated'] and len(records)==1
                and confirmed==1 and pending==0 and duplicates==0)
    return dict(strict_success=int(strict),duplicate=int(duplicates>0),
                false_completion=int(audit['finished'] and not strict),truncated=int(audit['truncated']))
