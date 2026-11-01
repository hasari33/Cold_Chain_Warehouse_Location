#!/usr/bin/env python3
"""Compare all 21 generated tables to the author's approved manuscript."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import zipfile
from docx import Document
from lxml import etree
from PIL import Image, ImageChops

NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
def xp(el,path):return etree.XPath(path,namespaces=NS)(el)
def accepted(el):
    return ''.join(t.text or '' for t in xp(el,'.//w:t|.//m:t') if not any(xp(a,'./w:rPr/w:strike[not(@w:val="0")]') or xp(a,'./m:ctrlPr/w:rPr/w:strike') for a in t.iterancestors()))

def check(root,results):
    expected=json.loads((root/'manuscript/accepted_tables.json').read_text())
    identity=json.loads((root/'manuscript/approved_identity.json').read_text())
    generated=json.loads((results/'publication_tables.json').read_text())
    main=root/'manuscript/IJPR_Manuscript.docx'
    failures=[];cells=0
    if hashlib.sha256(main.read_bytes()).hexdigest()!=identity['manuscript_sha256']:failures.append('Approved manuscript byte identity changed')
    doc=Document(main)
    indices=[0,7,8,9,18,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55]
    for (label,rows),idx in zip(expected.items(),indices):
        source_rows=[[accepted(c) for c in xp(r,'./w:tc')] for r in xp(doc.tables[idx]._tbl,'./w:tr')]
        if source_rows!=rows:failures.append(f'Approved snapshot differs from DOCX table {label}')
        actual=generated.get(label,[])
        if len(actual)!=len(rows):failures.append(f'Table {label} row count');continue
        for r,(aa,bb) in enumerate(zip(actual,rows)):
            if len(aa)!=len(bb):failures.append(f'Table {label} row {r} column count');continue
            for c,(a,b) in enumerate(zip(aa,bb)):
                cells+=1
                if a!=b:failures.append(f'Table {label} row {r} col {c}: generated {a!r}; manuscript {b!r}')
        with (results/f'tables/table_{label}.csv').open(newline='',encoding='utf-8') as f:
            if list(csv.reader(f))!=actual:failures.append(f'Table {label} CSV differs from computed table')
    with zipfile.ZipFile(main) as z:
        original=z.read('word/media/image1.png')
    for path in [root/'assets/figure_01_workflow.png',results/'figures/figure_01_workflow.png']:
        if path.read_bytes()!=original:failures.append(f'Original architecture changed: {path.name}')
    figure_matches=[]
    for n,name in [(2,'figure_02_method_ranks'),(3,'figure_03_rank_agreement')]:
        a=Image.open(root/f'manuscript/approved_figure_{n:02d}.png').convert('RGB')
        b=Image.open(results/f'figures/{name}.png').convert('RGB')
        match=a.size==b.size and ImageChops.difference(a,b).getbbox() is None
        figure_matches.append(match)
        # Numeric tables are the portable acceptance criterion. Font rendering
        # can differ between operating systems, so pixel differences are reported.
    report={'status':'PASS' if not failures else 'FAIL','approved_manuscript_sha256':identity['manuscript_sha256'],
            'publication_tables_compared':len(expected),'table_cells_compared':cells,'architecture_byte_identical':not any('architecture' in x for x in failures),
            'numeric_figures_pixel_identical':figure_matches,
            'failures':failures}
    (results/'manuscript_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    return report

def main():
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--results',type=Path,default=root/'results');args=parser.parse_args()
    report=check(root,args.results);print(json.dumps(report,ensure_ascii=False,indent=2))
    if report['failures']:raise SystemExit(1)

if __name__=='__main__':main()
