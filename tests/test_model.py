"""Independent numerical, provenance, deletion and reproducibility checks."""
import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import rankdata
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from cold_chain.model import (Evaluator, load_inputs, reciprocal_completion,
                              sf_weights, consistency, ordinal_consensus, agreement)


def scalar_oracle(x,w,b):
    """Separately coded scalar formula evaluation, without production helpers."""
    import math
    m,n=x.shape
    w=w/w.sum()
    mm=[];ratio=[];vec=[];pda=[];nda=[]
    for i in range(m):
        mm.append([]);ratio.append([]);vec.append([]);pda.append([]);nda.append([])
        for j in range(n):
            lo=min(x[:,j]);hi=max(x[:,j]);av=sum(x[:,j])/m
            mm[-1].append((x[i,j]-lo)/(hi-lo) if b[j] else (hi-x[i,j])/(hi-lo))
            ratio[-1].append(x[i,j]/hi if b[j] else lo/x[i,j])
            vec[-1].append(w[j]*x[i,j]/math.sqrt(sum(t*t for t in x[:,j])))
            dv=(x[i,j]-av)/av if b[j] else (av-x[i,j])/av
            pda[-1].append(max(0,dv));nda[-1].append(max(0,-dv))
    sp=[sum(w[j]*pda[i][j] for j in range(n)) for i in range(m)]
    sn=[sum(w[j]*nda[i][j] for j in range(n)) for i in range(m)]
    s=[sum(w[j]*mm[i][j] for j in range(n)) for i in range(m)]
    p=[sum(mm[i][j]**w[j] for j in range(n)) for i in range(m)]
    vs=[sum(w[j]*(1-mm[i][j]) for j in range(n)) for i in range(m)]
    vr=[max(w[j]*(1-mm[i][j]) for j in range(n)) for i in range(m)]
    ideal=[max(row[j] for row in vec) if b[j] else min(row[j] for row in vec) for j in range(n)]
    anti=[min(row[j] for row in vec) if b[j] else max(row[j] for row in vec) for j in range(n)]
    out=[]
    for i in range(m):
        ed=.5*(sp[i]/max(sp)+1-sn[i]/max(sn))
        wa=.5*(sum(w[j]*ratio[i][j] for j in range(n))+math.prod(ratio[i][j]**w[j] for j in range(n)))
        ka=(s[i]+p[i])/sum(s[k]+p[k] for k in range(m))
        kb=s[i]/min(s)+p[i]/min(p);kc=(s[i]+p[i])/(max(s)+max(p))
        co=(ka*kb*kc)**(1/3)+(ka+kb+kc)/3
        dp=math.sqrt(sum((vec[i][j]-ideal[j])**2 for j in range(n)))
        dn=math.sqrt(sum((vec[i][j]-anti[j])**2 for j in range(n)))
        vi=.5*((vs[i]-min(vs))/(max(vs)-min(vs))+(vr[i]-min(vr))/(max(vr)-min(vr)))
        out.append([ed,wa,co,dn/(dp+dn),vi])
    return np.array(out)


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.criteria,cls.names,cls.x,cls.b,cls.params,cls.codes,cls.scale,cls.indices=load_inputs(ROOT)
        raw=pd.read_csv(ROOT/'provenance/supplied/pairwise_as_received.csv')
        cc=cls.criteria.Criterion.tolist()
        cls.raw_codes=np.array([raw[raw.Perspective.eq(person)].pivot(index='Row',columns='Column',values='Canonical_code').loc[cc,cc].to_numpy() for person in sorted(raw.Perspective.unique())])
        cls.completed,cls.repairs=reciprocal_completion(cls.raw_codes,cls.indices)
        cls.w,*_=sf_weights(cls.completed,cls.scale)
        cls.e=Evaluator(cls.x,cls.b)

    def test_reciprocity_audit_and_explicit_completion(self):
        self.assertEqual(len(self.repairs),4)
        self.assertFalse(consistency(self.raw_codes,self.indices).iloc[1].Reciprocal)
        self.assertTrue(consistency(self.completed,self.indices).Acceptable.all())
        np.testing.assert_array_equal(self.codes,self.completed)
        for k in range(5):np.testing.assert_array_equal(np.triu(self.raw_codes[k]),np.triu(self.completed[k]))

    def test_derived_inputs_and_climate(self):
        x=self.x;total=x[:,2:8].sum(axis=1);cold=total-x[:,5]
        excess=np.maximum(np.array(self.params['monthly_mean_temperature_c'])-8,0).mean()
        self.assertAlmostEqual(excess,5.9)
        np.testing.assert_allclose(x[:,10],273/x[:,1],rtol=0,atol=1e-14)
        np.testing.assert_allclose(x[:,11],total/1000*x[:,1]*.129,rtol=0,atol=1e-10)
        np.testing.assert_allclose(x[:,12],cold/1000*x[:,1]/70*excess,rtol=0,atol=1e-10)
        self.assertAlmostEqual(x[0,9],952198*.685)

    def test_spherical_weight_trace_and_external_oracle(self):
        w,priorities,scores,_=sf_weights(self.completed,self.scale)
        self.assertTrue(np.all((priorities**2).sum(axis=1)<=1+1e-12))
        np.testing.assert_allclose(w,scores/scores.sum(),rtol=1e-14)
        actual=self.e.evaluate(w)['scores'][0]
        expected=scalar_oracle(self.x,w,self.b)
        np.testing.assert_allclose(actual,expected,atol=3e-14,rtol=3e-14)

    def test_zero_weight_is_actual_criterion_removal(self):
        for group in [[12],[5],[10,11,12]]:
            ww=self.w.copy();ww[group]=0
            keep=ww>0
            a=self.e.evaluate(ww)
            b=Evaluator(self.x[:,keep],self.b[keep]).evaluate(ww[keep])
            np.testing.assert_allclose(a['scores'],b['scores'],rtol=1e-13,atol=1e-13)
            np.testing.assert_array_equal(a['consensus'],b['consensus'])

    def test_column_unit_invariance_and_alt_identity(self):
        scale=np.array([2,.01,10,.2,2,5,.1,3,100,.01,7,1000,1/70])
        a=self.e.evaluate(self.w);b=Evaluator(self.x*scale,self.b).evaluate(self.w)
        np.testing.assert_allclose(a['scores'],b['scores'],atol=1e-13,rtol=1e-13)
        np.testing.assert_array_equal(a['consensus'],b['consensus'])
        reorder=np.arange(15)[::-1]
        b=Evaluator(self.x[reorder],self.b).evaluate(self.w)
        np.testing.assert_allclose(a['scores'][0],b['scores'][0,reorder],atol=1e-13)

    def test_score_ties_retain_average_method_ranks(self):
        w=self.w.copy();res=self.e.evaluate(w,vikor=0)
        expected=rankdata(res['scores'][0,:,4],method='average')
        np.testing.assert_array_equal(res['ranks'][0,:,4],expected)
        # Consensus is a unique ordering even when Borda is tied.
        ranks=np.array([[1,2],[2,1],[3,3]])
        bs,cr=ordinal_consensus(ranks)
        np.testing.assert_array_equal(bs,[[3,3,6]])
        np.testing.assert_array_equal(cr,[[1,2,3]])

    def test_vectorisation_and_random_reproducibility(self):
        draws=np.random.Generator(np.random.PCG64(42)).dirichlet(200*self.w,size=40)
        a=self.e.evaluate(draws)
        for i in [0,1,17,39]:
            oracle=scalar_oracle(self.x,draws[i],self.b)
            np.testing.assert_allclose(a['scores'][i],oracle,rtol=1e-13,atol=1e-13)
        again=np.random.Generator(np.random.PCG64(42)).dirichlet(200*self.w,size=40)
        np.testing.assert_array_equal(draws,again)
        self.assertTrue(np.all(np.sort(a['consensus'],axis=1)==np.arange(1,16)))

    def test_supplied_workbook_scores_with_its_recorded_weights(self):
        legacy=pd.read_csv(ROOT/'provenance/supplied/baseline_method_results.csv').set_index('Alternative').loc[self.names]
        supplied_weights=pd.read_csv(ROOT/'provenance/supplied/criteria_and_weights.csv').Baseline_weight.to_numpy()
        rr=self.e.evaluate(supplied_weights)
        for j,m in enumerate(['EDAS','WASPAS','CoCoSo','TOPSIS','VIKOR']):
            np.testing.assert_allclose(rr['scores'][0,:,j],legacy[m+'_score'],atol=1e-13,rtol=1e-13)
            np.testing.assert_array_equal(rr['ranks'][0,:,j],legacy[m+'_rank'])
        _,_,stats=agreement(rr['ranks'][0])
        self.assertAlmostEqual(stats['kendall_W'],.9151428571428571)

if __name__=='__main__':unittest.main()
