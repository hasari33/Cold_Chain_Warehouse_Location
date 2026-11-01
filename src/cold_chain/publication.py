"""Format recomputed quantities in the original manuscript's table numbering."""
import csv
import json
from pathlib import Path
import numpy as np
from .model import METHODS


def export_tables(root,out,criteria,names,x,codes,scale,params,w,consistency,base,rho,cases,robustness,scenarios,mc,contrib,derived):
    static=json.loads((root/'data/static_tables.json').read_text())
    tables={k:[list(row) for row in rows] for k,rows in static.items()}
    excess=np.maximum(np.asarray(params['monthly_mean_temperature_c'])-params['threshold_c'],0).mean()
    values={3:f"{params['working_age_share']:g}",5:f"{params['min_distance_km']:g} km",
            6:f"{params['emission_factor_kg_co2e_per_tkm']:g} kg CO2e/t-km",7:f"{params['speed_kmh']:g} km/h",
            8:f"{params['threshold_c']:g}∘C",9:f"{excess:g}∘C",10:f"{params['practitioner_weights'][0]:.2f}"}
    for row,value in values.items():tables['02'][row][1]=value
    i=names.index('Çankaya');a=x[i];d=derived.set_index('Alternative').loc['Çankaya']
    tables['03']=[['Indicator','Calculation','Result'],
      ['C9','District-level land-price proxy',f'{a[8]:,.0f} TRY/m²'],
      ['C10',f"{d.Population:,.0f} × {params['working_age_share']:g}",f'{a[9]:,.2f} persons'],
      ['C11',f"{params['min_distance_km']:g} / {a[1]:g}",f'{a[10]:.4f}'],
      ['Total shipment load',f'{a[2]:,.0f} + {a[3]:g} + {a[4]:.2f} + {a[5]:.2f} + {a[6]:.2f} + {a[7]:.2f}',f'{d.Total_load_kg:,.2f} kg'],
      ['Cold-chain load',f'{a[2]:,.0f} + {a[3]:g} + {a[4]:.2f} + {a[6]:.2f} + {a[7]:.2f}',f'{d.Cold_load_kg:,.2f} kg'],
      ['C12',f"{d.Total_load_kg/1000:.5f} t × {a[1]:g} km × {params['emission_factor_kg_co2e_per_tkm']:g} kg CO₂e/(t·km)",f'{a[11]:.3f} kg CO₂e/recorded load period'],
      ['C13',f"{d.Cold_load_kg/1000:.5f} t × ({a[1]:g}/{params['speed_kmh']:g} h) × {excess:g}°C",f'{a[12]:.3f} tonne·h·°C']]
    tables['06']=[['Participant','λmax','CI','CR','Decision']]+[
      [r.Practitioner,f'{r.Lambda_max:.4f}',f'{r.CI:.4f}',f'{r.CR:.4f}','Acceptable' if r.Acceptable else 'Revise']
      for r in consistency.itertuples()]
    tables['07']=[['Code','Criterion','Weight','Rank']]+[
      [criteria.iloc[i].Criterion,criteria.iloc[i].Name,f'{w[i]:.5f}',str(rank)] for rank,i in enumerate(np.argsort(-w),1)]
    b=base.set_index('Alternative')
    tables['08']=[['Alternative','EDAS ↑','WASPAS ↑','CoCoSo ↑','TOPSIS ↑','VIKOR ↓']]+[
      [name]+[f"{b.loc[name,m+'_score']:.4f} ({b.loc[name,m+'_rank']:g})" for m in METHODS] for name in names]
    tables['09']=[['Method']+METHODS]+[[m]+[f'{v:.5f}' for v in rho[i]] for i,m in enumerate(METHODS)]
    tables['10']=[['Alternative']+METHODS+['Borda sum','Mean','SD','Range','Top-3 count']]+[
      [name]+[f"{b.loc[name,m+'_rank']:g}" for m in METHODS]+[
       f'{b.loc[name,"Borda_sum"]:g}',f'{b.loc[name,"Mean_rank"]:.4f}',f'{b.loc[name,"Rank_SD_population"]:.4f}',
       f'{b.loc[name,"Minimum_rank"]:g}–{b.loc[name,"Maximum_rank"]:g}',f'{b.loc[name,"Top3_count"]:g}'] for name in names]
    rows=[['Analysis family','Cases','Design','Consensus leader','Top-three behavior']]
    specs=[('All-criterion perturbation','Weight perturbation','Each C1-C13 varied by ±5%, ±10%, ±15%, ±20%'),
           ('WASPAS λ sweep','WASPAS parameter','0, 0.25, 0.50, 0.75, 1'),
           ('CoCoSo λ sweep','CoCoSo parameter','0, 0.25, 0.50, 0.75, 1'),
           ('VIKOR v sweep','VIKOR parameter','0, 0.25, 0.50, 0.75, 1'),
           ('Leave-one-criterion-out','Single criterion deletion','One criterion removed and remaining weights normalized'),
           ('Grouped structural deletion','Grouped deletion','C11-C13 removed jointly')]
    for title,family,design in specs:
      group=cases[cases.Family.eq(family)];n=len(group)
      leaders='; '.join(f'{name} {count}/{n}' for name,count in group.First.value_counts().items())
      changed_set=n-int(group.Same_top3_set.sum());changed_order=n-int(group.Same_top3_order.sum())
      if family=='Weight perturbation':behavior=f'Set unchanged in {n-changed_set}/{n}; order changes in {changed_order}'
      elif family.endswith('parameter'):behavior='Top-three order unchanged' if changed_order==0 else f'Order changes in {changed_order}'
      elif family=='Single criterion deletion':behavior=f'Set changes in {changed_set}; order changes in {changed_order}'
      else:
        leaders=group.iloc[0].First;behavior='–'.join(group.iloc[0][['First','Second','Third']])
      rows.append([title,str(n),design,leaders,behavior])
    tables['11']=rows
    structures=['Normalized SF-AHP weight vector',f'wⱼ = 1/13 = {1/13:.4f}','60% to C1 and C3-C8',
                '60% to C2, C10 and C11','60% to C9','60% to C12 and C13']
    tables['12']=[['Scenario','Weight structure','1st','2nd','3rd']]+[
      [r.Scenario,structure,r.First,r.Second,r.Third] for r,structure in zip(scenarios.itertuples(),structures)]
    tables['13']=[['Alternative','P(rank 1)','P(top 3)','Mean rank','SD','95% rank interval']]+[
      [r.Alternative,f'{r.P_rank_1*100:.2f}%',f'{r.P_top_3*100:.2f}%',f'{r.Mean_rank:.4f}',f'{r.Rank_SD:.4f}',
       f'{int(r["Rank_q2.5"])}–{int(r["Rank_q97.5"])}'] for _,r in mc.iterrows()]
    contributions=contrib.set_index('Alternative').loc['Etimesgut',criteria.Criterion].astype(float).sort_values(ascending=False).head(8)
    desc=criteria.set_index('Criterion').Name
    tables['14']=[['Criterion','Description','Weighted contribution']]+[[c,'Distance' if c=='C2' else desc[c],f'{v:.5f}'] for c,v in contributions.items()]
    cc=criteria.Criterion.tolist()
    for k in range(5):tables[f'B{k+1}']=[['Criterion']+cc]+[[c]+list(codes[k,i]) for i,c in enumerate(cc)]
    def cell(j,value):
      if j in [0,1,2,3,8]:return f'{value:,.0f}'
      if j in [4,5,6,7,9]:return f'{value:,.2f}'
      return f'{value:.5f}'
    tables['C1']=[['Alternative']+cc]+[[name]+[cell(j,v) for j,v in enumerate(x[i])] for i,name in enumerate(names)]
    folder=out/'tables';folder.mkdir(exist_ok=True)
    for label,rows in sorted(tables.items()):
      with (folder/f'table_{label}.csv').open('w',encoding='utf-8',newline='') as f:csv.writer(f).writerows(rows)
    (out/'publication_tables.json').write_text(json.dumps(tables,ensure_ascii=False,indent=2))
