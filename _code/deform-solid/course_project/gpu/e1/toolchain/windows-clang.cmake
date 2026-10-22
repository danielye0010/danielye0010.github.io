# Paths are configurable; never modifies PATH, VS installations, or SDKs.
set(CMAKE_SYSTEM_NAME Windows)
set(E1_LLVM_BIN "D:/UNITY/Unity Hub/6000.2.12f1/Editor/Data/PlaybackEngines/WebGLSupport/BuildTools/Emscripten/llvm" CACHE PATH "Installed native LLVM binary directory")
set(CMAKE_CXX_COMPILER "${E1_LLVM_BIN}/clang++.exe")
set(CMAKE_AR "${E1_LLVM_BIN}/llvm-ar.exe")
set(CMAKE_RC_COMPILER "${E1_LLVM_BIN}/llvm-rc.exe")
set(CMAKE_CXX_COMPILER_FORCED TRUE)
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)
set(E1_FREESTANDING ON CACHE BOOL "No C runtime build" FORCE)
