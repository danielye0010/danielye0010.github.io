"""Configure/build the same C++ source using existing native Windows LLVM."""
from pathlib import Path
import argparse
import json
import subprocess
import sys,time
ROOT=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,default=ROOT/'build_native')
    p.add_argument('--cmake',type=Path,default=ROOT/'toolchain/cmake-3.31.8-windows-x86_64/bin/cmake.exe')
    p.add_argument('--ninja',type=Path,default=Path('D:/toolbox/shared/coder/ninja/win64/ninja.exe'))
    p.add_argument('--llvm',type=Path,default=Path('D:/UNITY/Unity Hub/6000.2.12f1/Editor/Data/PlaybackEngines/WebGLSupport/BuildTools/Emscripten/llvm'))
    a=p.parse_args(); a.build.mkdir(parents=True,exist_ok=True)
    commands=[[str(a.cmake),'-S',str(ROOT),'-B',str(a.build),'-G','Ninja',
        '-DCMAKE_TOOLCHAIN_FILE='+str(ROOT/'toolchain/windows-clang.cmake'),
        '-DCMAKE_MAKE_PROGRAM='+str(a.ninja),'-DE1_LLVM_BIN='+str(a.llvm),'-DE1_PYTHON='+sys.executable,'-DCMAKE_BUILD_TYPE=Release'],
        [str(a.cmake),'--build',str(a.build),'--verbose']]
    records=[]
    log=a.build/('BUILD_LOG_'+time.strftime('%Y%m%dT%H%M%S')+'.json')
    for command in commands:
        r=subprocess.run(command,capture_output=True,text=True)
        records.append(dict(command=command,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
        print(r.stdout+r.stderr,flush=True)
        (a.build/'BUILD_LOG.json').write_text(json.dumps(records,indent=2))
        log.write_text(json.dumps(records,indent=2))
        if r.returncode: raise SystemExit(r.returncode)


if __name__=='__main__': main()
