"""All publication graphics are deterministic functions of recomputed results."""
from io import BytesIO
from pathlib import Path
import os
import tempfile
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import shutil
from .model import METHODS


def make_figures(root, out, names, baseline, rho, mc, cases, weights):
    folder=out/"figures";folder.mkdir(exist_ok=True)
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,
                         "axes.spines.top":False,"axes.spines.right":False,
                         "savefig.facecolor":"white","svg.fonttype":"none"})
    def save(fig, name):
        for ext in ["png","svg","pdf"]:
            buffer=BytesIO()
            fig.savefig(buffer,format=ext,dpi=400,bbox_inches="tight",metadata={"Creator":"Cold Chain Warehouse Location 2.0.0"} if ext=="pdf" else None)
            # Publish only complete files, including on a synchronized filesystem.
            temporary=None
            try:
                with tempfile.NamedTemporaryFile(dir=folder,prefix=f".{name}.",suffix=".tmp",delete=False) as handle:
                    temporary=Path(handle.name)
                    handle.write(buffer.getvalue())
                    handle.flush()
                    os.fsync(handle.fileno())
                temporary.replace(folder/f"{name}.{ext}")
            finally:
                if temporary is not None and temporary.exists():temporary.unlink()
                buffer.close()
        plt.close(fig)
    # The original architecture is an author-supplied illustration. Preserve it
    # byte for byte instead of recreating or altering its design.
    shutil.copyfile(root/'assets/figure_01_workflow.png',folder/'figure_01_workflow.png')
    order=np.argsort(baseline["consensus"][0]);rank=baseline["ranks"][0,order]
    fig,ax=plt.subplots(figsize=(7.2,6.4));im=ax.imshow(rank,cmap="YlGnBu_r",vmin=1,vmax=len(names),aspect="auto")
    ax.set_xticks(range(5),METHODS);ax.xaxis.tick_top();ax.tick_params(axis="x",length=0,pad=8)
    ax.set_yticks(range(len(names)),np.array(names)[order]);ax.tick_params(axis="y",length=0)
    for i in range(len(names)):
        for j in range(5):ax.text(j,i,f"{rank[i,j]:g}",ha="center",va="center",color="white" if rank[i,j]<=5 else "black")
    fig.colorbar(im,ax=ax,fraction=.04,pad=.04,label="Rank 1 is preferred")
    save(fig,"figure_02_method_ranks")
    fig,ax=plt.subplots(figsize=(6.3,5.3));im=ax.imshow(rho,cmap="Blues",vmin=.7,vmax=1)
    ax.set_xticks(range(5),METHODS);ax.xaxis.tick_top();ax.set_yticks(range(5),METHODS);ax.tick_params(length=0,pad=8)
    for i in range(5):
        for j in range(5):ax.text(j,i,f"{rho[i,j]:.4f}",ha="center",va="center",color="white" if rho[i,j]>.91 else "black")
    fig.colorbar(im,ax=ax,fraction=.045,pad=.04,label="Spearman correlation")
    save(fig,"figure_03_rank_agreement")
    selected=mc.head(7).iloc[::-1]
    fig,ax=plt.subplots(figsize=(7.6,4.6));yy=np.arange(len(selected))
    ax.barh(yy+.17,selected.P_rank_1*100,height=.31,label="Rank 1",color="#245b78")
    ax.barh(yy-.17,selected.P_top_3*100,height=.31,label="Top 3",color="#94bccb")
    for y,(p1,p3) in zip(yy,selected[["P_rank_1","P_top_3"]].to_numpy()):
        ax.text(p1*100+1,y+.17,f"{p1*100:.2f}%",va="center",fontsize=8)
        ax.text(p3*100+1,y-.17,f"{p3*100:.2f}%",va="center",fontsize=8)
    ax.set_yticks(yy,selected.Alternative);ax.set_xlim(0,117);ax.set_xlabel("Share of weight simulations (%)");ax.legend(loc="lower right",frameon=False)
    save(fig,"figure_S3_rank_acceptability")
    full=pd.read_csv(out/"intermediate/deterministic_full_results.csv")
    chosen=["Etimesgut","Yenimahalle","Mamak","Çankaya","Gölbaşı"]
    xs=["Baseline","Remove C11","Remove C12","Remove C13","Remove C11–C13"]
    fig,ax=plt.subplots(figsize=(7.6,4.8))
    for a in chosen:
        i=names.index(a);rr=[baseline["consensus"][0,i]]
        for family,case in [("Single criterion deletion","C11"),("Single criterion deletion","C12"),("Single criterion deletion","C13"),("Grouped deletion","C11 C12 C13")]:
            rr.append(full.loc[full.Family.eq(family)&full.Case.eq(case)&full.Alternative.eq(a),"Consensus_rank"].iloc[0])
        ax.plot(range(5),rr,marker="o",label=a,linewidth=1.7)
    ax.set_xticks(range(5),xs,rotation=15,ha="right");ax.set_yticks(range(1,10));ax.set_ylim(9.5,.5)
    ax.set_ylabel("Consensus rank");ax.legend(ncol=3,loc="upper center",bbox_to_anchor=(.5,1.18),frameon=False)
    ax.grid(axis="y",alpha=.2)
    save(fig,"figure_S2_structural_sensitivity")
    fig,ax=plt.subplots(figsize=(7.2,4.7));idx=np.argsort(weights)
    ax.barh(np.arange(13),weights[idx],color="#245b78");ax.set_yticks(range(13),np.array([f"C{i+1}" for i in range(13)])[idx])
    ax.set_xlabel("Recomputed criterion weight");ax.set_xlim(0,.105)
    for y,val in enumerate(weights[idx]):ax.text(val+.001,y,f"{val:.5f}",va="center",fontsize=9)
    save(fig,"figure_S1_weights")
