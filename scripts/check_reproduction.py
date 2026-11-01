#!/usr/bin/env python3
"""Check full-precision release CSVs, the approved tables, and original figure."""
from pathlib import Path
import argparse
import json
import numpy as np
import pandas as pd
from check_manuscript import check

def main():
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--results',type=Path,default=root/'results');args=parser.parse_args()
    failures=[];checked=[]
    for ref in sorted((root/'reference_results').rglob('*.csv')):
        relative=ref.relative_to(root/'reference_results');target=args.results/relative
        if not target.exists():failures.append(f'Missing {relative}');continue
        a=pd.read_csv(ref,float_precision='round_trip');b=pd.read_csv(target,float_precision='round_trip')
        try:
            pd.testing.assert_frame_equal(a,b,check_dtype=False,check_exact=False,rtol=1e-11,atol=1e-12)
            checked.append(str(relative))
        except AssertionError as exc:failures.append(f'{relative}: {str(exc)[:400]}')
    if not checked:failures.append('No reference result tables were found')
    baseline=json.loads((root/'reference_results/metadata.json').read_text())
    fresh=json.loads((args.results/'metadata.json').read_text())
    for key in ['analysis_version','alpha','seed','simulations','input_sha256']:
        if fresh[key]!=baseline[key]:failures.append(f'Metadata mismatch: {key}')
    for key,value in baseline['statistics'].items():
        if isinstance(value,(int,float)) and not isinstance(value,bool):
            if not np.isclose(value,fresh['statistics'].get(key,np.nan),rtol=1e-11,atol=1e-12):failures.append(f'Statistic mismatch: {key}')
        elif fresh['statistics'].get(key)!=value:failures.append(f'Statistic mismatch: {key}')
    paper=check(root,args.results)
    failures.extend(paper['failures'])
    report={'status':'PASS' if not failures else 'FAIL','csv_files_compared':len(checked),
            'publication_tables_compared':paper['publication_tables_compared'],'table_cells_compared':paper['table_cells_compared'],
            'architecture_byte_identical':paper['architecture_byte_identical'],'numeric_figures_pixel_identical':paper['numeric_figures_pixel_identical'],
            'tolerance':{'rtol':1e-11,'atol':1e-12},'failures':failures}
    (args.results/'reproduction_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if failures:raise SystemExit(1)

if __name__=='__main__':main()
