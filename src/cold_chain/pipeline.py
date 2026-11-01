"""Reproduce every analysis and publication table in the approved manuscript."""
from pathlib import Path
import argparse
import hashlib
import json
import platform
import numpy as np
import pandas as pd
import scipy
from .model import METHODS, Evaluator, load_inputs, sf_weights, consistency, agreement, acceptability


def write(frame, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, float_format="%.17g")


def baseline_frame(res, names):
    out = pd.DataFrame({"Alternative": names})
    for j, method in enumerate(METHODS):
        out[f"{method}_score"] = res["scores"][0,:,j]
        out[f"{method}_rank"] = res["ranks"][0,:,j]
    out["VIKOR_S"],out["VIKOR_R"] = res["vikor_S"][0],res["vikor_R"][0]
    out["Borda_sum"],out["Consensus_rank"] = res["borda"][0],res["consensus"][0]
    ranks=res["ranks"][0]
    out["Mean_rank"],out["Rank_SD_population"] = ranks.mean(axis=1),ranks.std(axis=1)
    out["Minimum_rank"],out["Maximum_rank"] = ranks.min(axis=1),ranks.max(axis=1)
    out["Top3_count"] = (ranks<=3).sum(axis=1)
    return out.sort_values("Consensus_rank")


def run(root, out, n=5000):
    criteria,names,x,benefit,params,codes,scale,indices=load_inputs(root)
    out.mkdir(parents=True,exist_ok=True)
    cc=criteria.Criterion.tolist()
    w,priorities,scores,aggregated=sf_weights(codes,scale,params['practitioner_weights'])
    cr_table=consistency(codes,indices,params['ri_n13'])
    if not cr_table.Acceptable.all():
        raise ValueError('Practitioner matrices must be reciprocal with CR below 0.10')
    write(cr_table,out/'intermediate/practitioner_consistency.csv')
    wt=pd.DataFrame({'Criterion':cc,'Name':criteria.Name,'Weight':w,'mu':priorities[:,0],
                     'nu':priorities[:,1],'pi':priorities[:,2],'Score':scores})
    write(wt,out/'intermediate/criterion_weights.csv')
    write(pd.DataFrame([{'Row':cc[i],'Column':cc[j],'mu':aggregated[i,j,0],
                        'nu':aggregated[i,j,1],'pi':aggregated[i,j,2]}
                       for i in range(13) for j in range(13)]),out/'intermediate/aggregated_spherical_matrix.csv')
    write(pd.DataFrame(x,columns=cc).assign(Alternative=names)[['Alternative']+cc],out/'intermediate/decision_matrix.csv')
    write(pd.DataFrame([{'Practitioner':f'P{k+1}','Row':cc[i],'Column':cc[j],
                        'Code':codes[k,i,j],'SI':indices[codes[k,i,j]],
                        'mu':scale[codes[k,i,j]][0],'nu':scale[codes[k,i,j]][1],'pi':scale[codes[k,i,j]][2]}
                       for k in range(5) for i in range(13) for j in range(13)]),out/'intermediate/practitioner_comparisons.csv')
    evaluator=Evaluator(x,benefit)
    defaults={'waspas':params['waspas_lambda'],'cocoso':params['cocoso_lambda'],'vikor':params['vikor_v']}
    baseline=evaluator.evaluate(w,**defaults)
    base=baseline_frame(baseline,names)
    write(base,out/'intermediate/baseline_results.csv')
    rho,tau,stats=agreement(baseline['ranks'][0])
    for label,values in [('spearman',rho),('kendall_tau',tau)]:
        frame=pd.DataFrame(values,columns=METHODS);frame.insert(0,'Method',METHODS)
        write(frame,out/f'intermediate/{label}.csv')
    baseline_top=base.Alternative.iloc[:3].tolist()
    case_records=[];full=[];weight_records=[]
    def case(family,label,ww,**overrides):
        active=ww>0
        res=evaluator.evaluate(ww,**(defaults|overrides))
        order=np.argsort(res['consensus'][0]);top=np.array(names)[order[:3]].tolist()
        case_records.append({'Family':family,'Case':label,'First':top[0],'Second':top[1],'Third':top[2],
                             'Same_top3_set':set(top)==set(baseline_top),'Same_top3_order':top==baseline_top})
        frame=baseline_frame(res,names);frame.insert(0,'Case',label);frame.insert(0,'Family',family)
        full.extend(frame.to_dict('records'))
        weight_records.append({'Family':family,'Case':label,**dict(zip(cc,ww/ww.sum())),
                               'Active_criteria':int(active.sum()),**(defaults|overrides)})
    for j,c in enumerate(cc):
        for delta in params['perturbations']:
            ww=w.copy();ww[j]*=1+delta
            case('Weight perturbation',f'{c} {delta:+.0%}',ww)
    for method,param in [('WASPAS','waspas'),('CoCoSo','cocoso'),('VIKOR','vikor')]:
        for value in params['parameter_grid']:case(f'{method} parameter',str(value),w,**{param:value})
    for j,c in enumerate(cc):
        ww=w.copy();ww[j]=0;case('Single criterion deletion',c,ww)
    ww=w.copy();ww[10:13]=0;case('Grouped deletion','C11 C12 C13',ww)
    cases=pd.DataFrame(case_records)
    write(cases,out/'intermediate/deterministic_cases.csv')
    write(pd.DataFrame(full),out/'intermediate/deterministic_full_results.csv')
    write(pd.DataFrame(weight_records),out/'intermediate/deterministic_weights.csv')
    summaries=[]
    for family,rows in cases.groupby('Family',sort=False):
        summaries.append({'Family':family,'Cases':len(rows),'Leaders':'; '.join(f'{a}: {c}' for a,c in rows.First.value_counts().items()),
                          'Same_top3_set':int(rows.Same_top3_set.sum()),'Same_top3_order':int(rows.Same_top3_order.sum())})
    robustness=pd.DataFrame(summaries)
    write(robustness,out/'intermediate/robustness_summary.csv')
    scenarios={'Baseline SF-AHP':w,'Equal weights':np.ones(13)/13}
    for name,group in [('Demand-operational',[0,2,3,4,5,6,7]),('Accessibility-infrastructure',[1,9,10]),
                       ('Economic',[8]),('Environmental-risk',[11,12])]:
        mask=np.zeros(13,bool);mask[group]=True;ww=np.empty(13)
        ww[mask]=.6*w[mask]/w[mask].sum();ww[~mask]=.4*w[~mask]/w[~mask].sum();scenarios[name]=ww
    scenario_rows=[];scenario_full=[];scenario_weights=[]
    for label,ww in scenarios.items():
        res=evaluator.evaluate(ww,**defaults);frame=baseline_frame(res,names)
        scenario_rows.append({'Scenario':label,**dict(zip(['First','Second','Third'],frame.Alternative.iloc[:3]))})
        frame.insert(0,'Scenario',label);scenario_full.extend(frame.to_dict('records'))
        scenario_weights.append({'Scenario':label,**dict(zip(cc,ww))})
    write(pd.DataFrame(scenario_rows),out/'intermediate/scenario_summary.csv')
    write(pd.DataFrame(scenario_full),out/'intermediate/scenario_full_results.csv')
    write(pd.DataFrame(scenario_weights),out/'intermediate/scenario_weights.csv')
    rng=np.random.Generator(np.random.PCG64(params['seed']))
    draws=rng.dirichlet(params['alpha']*w,size=n)
    chunks=[evaluator.evaluate(draws[k:k+1000],**defaults) for k in range(0,n,1000)]
    consensus=np.concatenate([a['consensus'] for a in chunks]);method_ranks=np.concatenate([a['ranks'] for a in chunks]);borda=np.concatenate([a['borda'] for a in chunks])
    for label,values,cols in [('weights',draws,cc),('consensus_ranks',consensus,names),('borda_sums',borda,names),
                              ('method_ranks',method_ranks.reshape(n,-1),[f'{a}__{m}' for a in names for m in METHODS])]:
        frame=pd.DataFrame(values,columns=cols);frame.insert(0,'Simulation',np.arange(1,n+1));write(frame,out/f'monte_carlo/{label}.csv')
    mc=acceptability(consensus,names);write(mc,out/'monte_carlo/rank_acceptability.csv')
    probability=pd.DataFrame({f'Rank_{r}':(consensus==r).mean(axis=0) for r in range(1,16)})
    probability.insert(0,'Alternative',names);write(probability,out/'monte_carlo/full_rank_acceptability.csv')
    total=x[:,2:8].sum(axis=1);cold=total-x[:,5]
    excess=float(np.maximum(np.asarray(params['monthly_mean_temperature_c'])-params['threshold_c'],0).mean())
    derived=pd.DataFrame({'Alternative':names,'Total_load_kg':total,'Cold_load_kg':cold,
                          'Population':pd.read_csv(root/'data/observed_inputs.csv').Population,
                          'C10':x[:,9],'C11':x[:,10],'C12':x[:,11],'C13':x[:,12]})
    write(derived,out/'intermediate/derived_indicators.csv')
    corr=pd.DataFrame(x,columns=cc).corr(method='spearman');corr.insert(0,'Criterion',cc)
    write(corr,out/'intermediate/criterion_spearman.csv')
    contrib=pd.DataFrame(baseline['contributions'][0],columns=cc);contrib.insert(0,'Alternative',names);contrib['Total_utility']=baseline['utility'][0]
    write(contrib,out/'intermediate/weighted_minmax_contributions.csv')
    av=x.mean(axis=0);dev=np.where(benefit,x-av,av-x)/av
    mm=np.where(benefit,(x-x.min(axis=0))/np.ptp(x,axis=0),(x.max(axis=0)-x)/np.ptp(x,axis=0))
    for label,values in [('edas_PDA',np.maximum(dev,0)),('edas_NDA',np.maximum(-dev,0)),
                         ('waspas_ratio',np.where(benefit,x/x.max(axis=0),x.min(axis=0)/x)),('cocoso_minmax',mm),
                         ('topsis_vector',x/np.sqrt((x*x).sum(axis=0))),('vikor_weighted_regret',(1-mm)*w)]:
        frame=pd.DataFrame(values,columns=cc);frame.insert(0,'Alternative',names);write(frame,out/f'intermediate/{label}.csv')
    order=np.argsort(baseline['scores'][0,:,4]);gap=float(baseline['scores'][0,order[1],4]-baseline['scores'][0,order[0],4])
    stats.update(VIKOR_first=names[order[0]],VIKOR_second=names[order[1]],VIKOR_Q_gap=gap,VIKOR_DQ=1/14,
                 VIKOR_advantage=gap>=1/14,VIKOR_stability=bool(order[0] in [np.argmin(baseline['vikor_S'][0]),np.argmin(baseline['vikor_R'][0])]))
    checks={'Primary_weight_sum':float(w.sum()),'All_practitioner_CR_below_0.1':bool(cr_table.Acceptable.all()),
            'Spherical_priority_feasible':bool(np.all((priorities**2).sum(axis=1)<=1+1e-12)),
            'Climate_positive_excess':excess,'Simulation_count':n,'All_draws_unit_sum':bool(np.allclose(draws.sum(axis=1),1)),
            'All_consensus_ranks_permutations':bool(np.all(np.sort(consensus,axis=1)==np.arange(1,16)))}
    metadata={'analysis_version':params['analysis_version'],'primary_model':'Equal-weight aggregation of five practitioner matrices in Appendix B',
              'random_generator':'numpy.random.Generator(PCG64(42))','alpha':params['alpha'],'seed':params['seed'],'simulations':n,
              'statistics':stats,'checks':checks,'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'scipy':scipy.__version__,
              'input_sha256':{str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((root/'data').glob('*')) if f.is_file()}}
    (out/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2))
    from .publication import export_tables
    export_tables(root,out,criteria,names,x,codes,scale,params,w,cr_table,base,rho,cases,robustness,pd.DataFrame(scenario_rows),mc,contrib,derived)
    from .plots import make_figures
    make_figures(root,out,names,baseline,rho,mc,cases,w)
    print(json.dumps({'leader':base.iloc[0].Alternative,'statistics':stats,'checks':checks},ensure_ascii=False,indent=2))
    return metadata


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output',type=Path)
    parser.add_argument('--simulations',type=int,default=5000)
    args=parser.parse_args()
    if args.simulations<2:parser.error('At least two simulations are required')
    run(args.root.resolve(),(args.output or args.root/'results').resolve(),args.simulations)

if __name__=='__main__':main()
