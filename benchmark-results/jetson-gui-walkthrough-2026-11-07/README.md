# Jetson desktop GUI walkthrough — 2026-11-07

The desktop GUI was launched on DISPLAY=:0 and used to run the actual installed Jetson AGX Thor KiCad example through the Near field page. U13, VCC/GND, C46/C49; assumed 1 A pulse, 33% duty, 500 kHz switching, harmonics 1 and 2, nominal coarse/local mesh 2/1 mm, crop margin 2 mm, eight OpenMP workers. The scan uses 17 lateral points per axis at 1 and 3 mm above top copper. These are illustrative operating/mesh settings, not extracted switching-device behavior or demonstrated copper/crop convergence.

Run output is in U13/. The solve used 10,045 triangles on ten copper layers, 252 via segments and 5,654 loops. Total runtime including reading the KiCad file and plotting was about 49 s. Copper R is 1.258/1.483 mOhm and L is 0.400/0.345 nH at 500 kHz/1 MHz. FFT deposition converged after refinement 2. Peak H is 130.9/66.8 A/m at 1 mm and 11.42/5.90 A/m at 3 mm, for the assumed harmonic amplitudes 0.548/0.279 A peak.

Walkthrough:
1. Near field: select the board, converter, supply/ground and input capacitors; set the operating point, scan, mesh and backend. Use this page's Run button.
2. Summary: inspect R/L, peak H per harmonic and model assumptions.
3. Spectrum / H maps: inspect frequency dependence and the spatial field distribution.
4. Open fields in Viewer: Cut offers dump, component, normal axis, frame/frequency and phase controls. Its log scale displays log10 of H in A/m.
5. Viewer > 3D: choose the H volume dump; drag to orbit, wheel to zoom and Ctrl-drag to pan. The volume in this run has only the two requested height samples; add more scan heights for more directly sampled z planes.

The initial default desktop OpenGL backend produced PyOpenGL context errors. Relaunching with QT_QPA_PLATFORM=xcb QT_XCB_GL_INTEGRATION=xcb_glx PYOPENGL_PLATFORM=glx resolved them and both plane/volume overlays rendered on the RX 7800 XT. No production source changes were made. For future launches from the project root:

    QT_QPA_PLATFORM=xcb QT_XCB_GL_INTEGRATION=xcb_glx PYOPENGL_PLATFORM=glx kicad2ems/.venv/bin/kicad2ems-gui

The GUI was left open on the volume view. Saved screenshots record the settings, run, summary, spectrum, maps, 2D cut and working 3D view. 07-3d.png records the failed initial backend; 08-3d-relaunch.png and 09-volume.png show the working backend.
