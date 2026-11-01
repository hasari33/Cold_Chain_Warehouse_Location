"""Build the supplementary methods document from freshly computed results."""
from pathlib import Path
import json
import re
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import pandas as pd

TITLE='Robust Cold-Chain Warehouse Location Selection Under Uncertainty: An Integrated Spherical Fuzzy and Multi-Method Decision Framework'

def setup(academic=False):
    doc=Document();s=doc.sections[0]
    if academic:s.page_width=Inches(8.2677);s.page_height=Inches(11.6929)
    else:s.page_width=Inches(8.5);s.page_height=Inches(11)
    s.top_margin=s.bottom_margin=Inches(.8);s.left_margin=s.right_margin=Inches(.85)
    normal=doc.styles['Normal'];normal.font.name='Times New Roman' if academic else 'Calibri';normal.font.size=Pt(11)
    normal.paragraph_format.space_after=Pt(7);normal.paragraph_format.line_spacing=1.12
    for name,size in [('Title',19),('Heading 1',14),('Heading 2',12)]:
        st=doc.styles[name];st.font.name=normal.font.name;st.font.size=Pt(size);st.font.color.rgb=RGBColor(0,0,0)
        st.paragraph_format.space_before=Pt(12 if name!='Title' else 0);st.paragraph_format.space_after=Pt(7)
        st.paragraph_format.keep_with_next=True
    for st in [doc.styles['Title'],doc.styles['Heading 1'],doc.styles['Heading 2']]:
        st.font.bold=True
        for el in list(st.element.xpath('./w:pPr/w:pBdr')):el.getparent().remove(el)
    footer=s.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
    field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)
    footer.style='Normal';footer.paragraph_format.space_after=Pt(0)
    doc.core_properties.author='Hüseyin Ali Sarıkaya'
    return doc

def paragraph(doc,text,style=None):
    return doc.add_paragraph(text,style)

def code(doc,text):
    lines=text.splitlines()
    for i,line in enumerate(lines):
        p=doc.add_paragraph();p.paragraph_format.space_after=Pt(2);p.paragraph_format.line_spacing=1
        p.paragraph_format.keep_with_next=i<len(lines)-1
        r=p.add_run(line);r.font.name='Consolas';r.font.size=Pt(9)

def table(doc,headers,rows,widths=None,size=10):
    t=doc.add_table(rows=1,cols=len(headers));t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
    if widths:
        for c,width in zip(t.columns,widths):c.width=Inches(width)
    for c,text in zip(t.rows[0].cells,headers):c.text=str(text)
    for values in rows:
        for c,value in zip(t.add_row().cells,values):c.text=str(value)
    for i,row in enumerate(t.rows):
        for j,c in enumerate(row.cells):
            if widths:c.width=Inches(widths[j])
            c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            pr=c._tc.get_or_add_tcPr()
            borders=OxmlElement('w:tcBorders')
            for edge in ['top','left','bottom','right']:
                el=OxmlElement('w:'+edge);el.set(qn('w:val'),'single');el.set(qn('w:sz'),'4');el.set(qn('w:color'),'D9D9D9');borders.append(el)
            pr.append(borders)
            margin=OxmlElement('w:tcMar')
            for edge in ['top','bottom','left','right']:
                el=OxmlElement('w:'+edge);el.set(qn('w:w'),'65');el.set(qn('w:type'),'dxa');margin.append(el)
            pr.append(margin)
            if i==0:
                shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'E7EBEE');pr.append(shade)
            for p in c.paragraphs:
                p.paragraph_format.line_spacing=1.05;p.paragraph_format.space_after=Pt(2);p.paragraph_format.space_before=Pt(2)
                if i==0:p.paragraph_format.keep_with_next=True
                for r in p.runs:r.font.size=Pt(size);r.font.bold=i==0
            cant=OxmlElement('w:cantSplit');row._tr.get_or_add_trPr().append(cant)
        if i==0:
            repeat=OxmlElement('w:tblHeader');row._tr.get_or_add_trPr().append(repeat)
    doc.add_paragraph().paragraph_format.space_after=Pt(1)
    return t

def newpage(doc,heading):
    doc.add_page_break();doc.add_heading(heading,1)

def build_supplement(root,results=None):
    results=results or root/'results'
    meta=json.loads((results/'metadata.json').read_text())
    tables=json.loads((results/'publication_tables.json').read_text())
    params=json.loads((root/'data/parameters.json').read_text())
    d=setup(True);d.add_heading('Supplementary Material',0)
    paragraph(d,TITLE)
    paragraph(d,'Hüseyin Ali Sarıkaya\nDepartment of Industrial Engineering, Mudanya University, Bursa, Türkiye\nCorrespondence: huseyin.sarikaya@mudanya.edu.tr')
    d.add_heading('Computational scope',1)
    paragraph(d,'This supplement documents the data, Python implementation and complete numerical outputs for the integrated cold-chain warehouse-location framework. Fifteen Ankara districts are evaluated against 13 criteria using judgments from five active domain practitioners, each weighted at 0.20. The analysis uses SF-AHP, EDAS, WASPAS, CoCoSo, TOPSIS and VIKOR.')
    table(d,['Analysis','Specification'],[
        ['Baseline consensus','Etimesgut, Yenimahalle, Mamak; Borda sums 8, 12 and 16'],
        ['Rank agreement',f"Kendall W = {meta['statistics']['kendall_W']:.10f}"],
        ['Deterministic design','104 weight perturbations; 15 parameter cases; 13 single deletions; one grouped deletion'],
        ['Strategic scenarios','Baseline, equal weights and four thematic scenarios'],
        ['Stochastic design',f"{meta['simulations']:,} Dirichlet replications; concentration {meta['alpha']}; PCG64; seed {meta['seed']}"]],[1.65,4.85])
    d.add_heading('Run the complete analysis',1)
    code(d,'python -m pip install -r requirements.txt\npython -m unittest discover -s tests -v\npython run_analysis.py\npython scripts/check_reproduction.py\npython scripts/build_supplement.py')
    paragraph(d,'Run these commands in the extracted project root with Python 3.12. After dependency installation, the analysis uses local files. GitHub Actions executes the same sequence. This document accompanies release 2.0.0 of the computational archive.')

    newpage(d,'Data and assumptions')
    paragraph(d,'The primary analysis reads the following files. The data dictionary in criteria.csv specifies measurement units, benefit/cost direction, origin and decision rationale for every criterion.')
    table(d,['Input file in data','Content'],[
        ['observed_inputs.csv','15 records: district identity, C1–C9, population'],
        ['criteria.csv','13 criterion definitions, units and directions'],
        ['practitioners.csv','Five practitioner departments and experience domains'],
        ['pairwise_practitioners.csv','845 linguistic entries: five 13 × 13 matrices'],
        ['fuzzy_scale.csv','Nine spherical fuzzy numbers and reciprocal score indices'],
        ['parameters.json','Common assumptions, weights, simulation controls'],
        ['static_tables.json','Definitions, profiles, adopted random-index values and publication labels']],[2.3,4.2])
    paragraph(d,'C1–C9 retain the supplied numeric inputs. Population integers are the values underlying the full-precision C10 workforce-accessibility indicator; no additional population observations are introduced. The working-age share is 0.685, evaluated as 685/1000 before final floating-point division.')
    paragraph(d,'C10 is population multiplied by the working-age share. C11 divides the minimum candidate distance, 273 km, by the district distance. C12 multiplies total load in tonnes, distance and 0.129 kg CO₂e per tonne-kilometre. C13 multiplies cold-chain load in tonnes, approximate travel time and the mean positive ambient-temperature excess. Consumables are excluded from cold-chain load.')
    paragraph(d,'The mean positive excess above 8°C is 5.9°C, computed from the 12 monthly means in parameters.json. Average speed is 70 km/h. The reporting duration of the shipment loads is unspecified; load and emission quantities refer to the recorded load period. The common ambient threshold is an exposure reference, rather than a product-specific food-safety limit.')
    paragraph(d,'The practitioner matrices match Appendix B. Upper-triangular assessments and reciprocal lower-triangular encoding follow the stated procedure. The unchanged supplied workbook and original comparison file are retained under provenance/supplied; the four lower-triangular encoding entries are documented in pairwise_encoding_log.csv. Full-precision release results are in reference_results.')

    newpage(d,'Spherical fuzzy weighting')
    paragraph(d,'model.sf_weights aggregates the five practitioner judgments cell by cell using the spherical weighted geometric mean, aggregates each criterion row using equal spherical weighted arithmetic weights, computes the stated score and normalizes the 13 scores to a unit-sum vector. The complete aggregate matrix is exported separately.')
    weights=pd.read_csv(results/'intermediate/criterion_weights.csv')
    table(d,['Code','Membership','Nonmembership','Hesitation','Score','Weight'],[
        [r.Criterion,f'{r.mu:.5f}',f'{r.nu:.5f}',f'{r.pi:.5f}',f'{r.Score:.5f}',f'{r.Weight:.8f}'] for r in weights.itertuples()],
        [.55,1.1,1.25,1.1,1.1,1.4],size=10)
    paragraph(d,'Score-index consistency is checked before aggregation using the reciprocal mapping in fuzzy_scale.csv and the adopted RI = 1.56 for order 13. All five matrices have CR below 0.10. Spherical feasibility is checked for the input triples and the aggregated priorities.')
    d.add_heading('Algorithm S1',2)
    paragraph(d,'1. Read criterion directions, measurements, practitioner codes and parameter values.\n2. Recalculate derived indicators and verify dimensions and positive values.\n3. Map linguistic codes to spherical triples and score-index matrices.\n4. Check reciprocity, spherical feasibility and consistency.\n5. Aggregate practitioner cells, then criterion rows, and normalize the resulting scores.\n6. Apply all five ranking methods to the same matrix and weights.\n7. Calculate method ranks, Borda sums, consensus ranks and agreement statistics.')

    newpage(d,'Deterministic and strategic analyses')
    paragraph(d,'A weight perturbation multiplies one criterion weight by 1 + δ and renormalizes the complete vector. A criterion deletion physically removes the column before normalization, ideal construction and CoCoSo power aggregation. Thematic scenarios allocate 60% to the emphasized group and 40% to the remaining criteria, retaining baseline ratios within each group.')
    table(d,['Experiment','Cases','Consensus result'],[
        ['Individual weight perturbation','104','Etimesgut 98; Yenimahalle 6; top-three set unchanged'],
        ['WASPAS mixing parameter','5','Etimesgut first in all five cases'],
        ['CoCoSo mixing parameter','5','Etimesgut first in all five cases'],
        ['VIKOR compromise parameter','5','Etimesgut first in all five cases'],
        ['Single criterion removal','13','Etimesgut 12; Yenimahalle 1'],
        ['Joint removal of C11–C13','1','Yenimahalle, Etimesgut, Mamak']],[2.15,.5,3.85],size=10)
    paragraph(d,'Perturbations are ±5%, ±10%, ±15% and ±20%. Each method parameter is evaluated at 0, 0.25, 0.50, 0.75 and 1. The baseline parameter is 0.50 for all three methods.')
    table(d,['Scenario','First','Second','Third'],[row[:1]+row[2:] for row in tables['12'][1:]],[2.1,1.4,1.5,1.5],size=10)
    paragraph(d,'deterministic_cases.csv records each of the 133 cases. deterministic_weights.csv retains its weight vector and method parameters. deterministic_full_results.csv retains every method score and rank, Borda sum and consensus rank. scenario_full_results.csv and scenario_weights.csv provide the equivalent records for all six strategic scenarios.')
    paragraph(d,'Method score ties use average ranks. Borda ties use, in order, more first places, more top-three appearances, a lower worst rank and the fixed district order. This ordering is applied to every deterministic case and Monte Carlo replication.')

    newpage(d,'Monte Carlo and numerical output')
    paragraph(d,'Each replication draws a weight vector from Dirichlet(200w) using NumPy Generator with PCG64 and seed 42, applies all five methods and recalculates the consensus. The archive retains every sampled vector, method rank, Borda sum and final consensus rank. These are weight-uncertainty replications, rather than optimization iterations.')
    table(d,tables['13'][0],tables['13'][1:],[1.55,.8,.8,1, .8,1.15],size=9.7)
    paragraph(d,'Monte Carlo SD is the sample standard deviation. The empirical 95% rank interval uses the nearest observed 2.5% and 97.5% quantiles. The method-rank dispersion in main Table 10 uses population SD across the five methods. Probabilities are conditional on fixed district measurements, practitioner comparisons and concentration 200.')
    paragraph(d,'full_rank_acceptability.csv contains the probability of every rank, not only first place and top three. Weighted min–max contributions are an auxiliary additive benchmark; they do not decompose the Borda consensus. All calculation CSVs retain 17 significant digits, while publication tables reproduce the manuscript display precision.')

    newpage(d,'Manuscript and output mapping')
    paragraph(d,'The following 21 publication tables are regenerated under the manuscript numbering. The complete manuscript, editable equations and appendices are provided in manuscript/IJPR_Manuscript.docx. Every computed result table is produced from the numerical analysis.')
    labels=[f'{i:02d}' for i in range(1,15)]+['A1','B1','B2','B3','B4','B5','C1']
    table(d,['Manuscript table','Generated CSV'],[[str(int(k)) if k.isdigit() else k,f'results/tables/table_{k}.csv'] for k in labels],[1.35,5.15],size=10)
    paragraph(d,'docs/artifact_map.csv additionally identifies inputs and producing functions for every table, figure and equation group. The reference snapshots retain the manuscript table labels, row order, units and rounding.')

    newpage(d,'Figures and reproducibility checks')
    table(d,['Element','File stem in results/figures','Source'],[
        ['Figure 1','figure_01_workflow','Original architecture image'],
        ['Figure 2','figure_02_method_ranks','Five-method baseline ranks'],
        ['Figure 3','figure_03_rank_agreement','Spearman matrix'],
        ['Figure S1','figure_S1_weights','Criterion weights'],
        ['Figure S2','figure_S2_structural_sensitivity','Criterion-deletion cases'],
        ['Figure S3','figure_S3_rank_acceptability','Monte Carlo summary']],[.8,3.35,2.35],size=10)
    paragraph(d,'Figure 1 is copied byte for byte at its original resolution. It is not redrawn. Figures 2–3 and S1–S3 are generated as 400 dpi PNG and as SVG and PDF. Their numeric data are retained in the corresponding CSV outputs.')
    paragraph(d,'Eight numerical tests compare the vectorized methods with an independently coded scalar implementation; verify derived indicators, reciprocity and spherical weights; check deletion semantics, measurement-unit invariance and district identity; retain average score ranks; and verify random-stream reproducibility. The supplied workbook scores are also reproduced using their recorded weight vector as a separate provenance check.')
    paragraph(d,'scripts/check_reproduction.py compares 51 CSV files within relative tolerance 1e-11 and absolute tolerance 1e-12, then checks all 2,026 cells of the 21 publication tables against the manuscript. The architecture image must remain byte-identical. Main Figures 2 and 3 are also compared at pixel level; font-dependent differences on another operating system are reported separately from numeric agreement.')
    paragraph(d,'metadata.json records input hashes, software versions, simulation settings, VIKOR compromise checks and agreement statistics. reproduction_check.json reports PASS or FAIL. requirements.txt pins the dependencies. Custom inputs or parameters are expected to differ from the frozen release and should be written to a separate output directory.')
    paragraph(d,'The analysis screens districts for subsequent parcel-level and network feasibility assessment. The emission and ambient-exposure indicators are comparative proxies. All empirical interpretations and limitations follow the accompanying manuscript.')
    dest=root/'docs/Supplementary_Material.docx';dest.parent.mkdir(exist_ok=True);d.save(dest)
    return dest

def markdown_document(source,title,page_break_headings=()):
    d=setup();d.add_heading(title,0);in_code=False;first=True;block=[]
    for line in source.splitlines():
        if line.startswith('```'):
            if in_code:
                if d.paragraphs:d.paragraphs[-1].paragraph_format.keep_with_next=True
                code(d,'\n'.join(block));block=[]
            in_code=not in_code;continue
        if in_code:block.append(line);continue
        if not line.strip():continue
        if line.startswith('# ') and first:first=False;continue
        first=False
        if line.startswith('## '):
            heading=line[3:]
            if any(heading.startswith(k) for k in page_break_headings):d.add_page_break()
            d.add_heading(heading,1)
        elif line.startswith('- '):paragraph(d,line[2:],'List Bullet')
        else:paragraph(d,line.replace('`','').replace('**',''))
    return d
