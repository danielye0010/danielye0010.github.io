"""Read-only reuse and preservation of 00-A. Use Python -B as well."""
import sys
from pathlib import Path
import hashlib
import json

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
PARENT=ROOT.parent
sys.path.insert(0,str(PARENT))
from sq.geometry import Box,Solid
from sq.field import Field,BITS
from sq.baselines import Stats as OldStats,newton
from sq import oracle as old_oracle


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+"\n",encoding="utf-8")


def parent_inventory():
    files=[p for p in PARENT.rglob("*") if p.is_file() and
           not any(v in ("exp00b",".venv",".mplconfig","__pycache__") for v in p.relative_to(PARENT).parts)]
    return {p.relative_to(PARENT).as_posix():sha(p) for p in sorted(files)}


def freeze_parent():
    path=ROOT/"PARENT_PRESERVATION.json"
    if path.exists():
        before=json.loads(path.read_text())
        assert before==parent_inventory(),"00-A preservation failed"
    else:
        write_json(path,parent_inventory())


def configuration():
    return json.loads((ROOT/"config.json").read_text())
