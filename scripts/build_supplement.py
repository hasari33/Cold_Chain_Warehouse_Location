#!/usr/bin/env python3
"""Regenerate the supplementary methods without editing the approved article."""
from pathlib import Path
import argparse
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from cold_chain.documents import build_supplement
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--results',type=Path,default=ROOT/'results');args=parser.parse_args()
    print(build_supplement(ROOT,args.results))
