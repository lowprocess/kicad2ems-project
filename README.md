# kicad2ems-project

The whole [kicad2ems](https://github.com/lowprocess/kicad2ems) stack in one checkout: each package is a git
submodule here, at the commit the others were last tested with.

| Repository | What it is |
|---|---|
| [kicad2ems](https://github.com/lowprocess/kicad2ems) | KiCad boards to EM solvers: the board model, the line model, the runs, the reports; `setup.sh` installs the stack |
| [mom25d](https://github.com/lowprocess/mom25d) | a 2.5D method-of-moments solver (layered Green's functions, GPU LU) |
| [gfdtd](https://github.com/lowprocess/gfdtd) | a GPU-accelerated FDTD solver |
| [kicad2ems-fdtd](https://github.com/lowprocess/kicad2ems-fdtd) | kicad2ems's openEMS and gfdtd solver plugins |
| [kicad2ems-gui](https://github.com/lowprocess/kicad2ems-gui) | the window: a run's settings, the run and its results |
| [kicad2ems-ipc](https://github.com/lowprocess/kicad2ems-ipc) | the plugin for KiCad's PCB editor (KiCad's IPC API, KiCad 9 and later) |
| [dfsynth](https://github.com/lowprocess/dfsynth) | distributed-element microstrip filter synthesis, checked with kicad2ems |
| [emsdev](https://github.com/lowprocess/emsdev) | the GPUs, CPU and memory as the solvers see them, shared by mom25d and gfdtd |

## Getting it

```bash
git clone --recurse-submodules https://github.com/lowprocess/kicad2ems-project.git
cd kicad2ems-project/kicad2ems
./setup.sh                      # asks what to install; --yes takes the defaults
```

`setup.sh` also makes the example boards, so `kicad2ems examples/demo_transition.toml` runs straight after it.

## Keeping it current

Each submodule tracks its repository's `main` branch:

```bash
git pull --recurse-submodules                   # this repository and the commits it pins
git submodule update --remote --merge           # every package to the latest on its main
git add -A && git commit -m "Submodules: ..."   # pin those commits here
```

Work happens in each package's own repository; this one records which commits go together.
