<p align="center">
<img src="docs/img/icon.svg" height="200" />
</p>

# `x_xy_v2` -- A *tiny* Kinematic Tree Simulator
<img src="docs/img/coverage_badge.svg" height="20" />

## Installation

Supports `Python=3.10/3.11` (tested).

Install with `pip` using

`pip install 'x_xy[all] @ git+https://github.com/SimiPixel/x_xy_v2'`

Typically, this will install `jax` as cpu-only version. CUDA version can be installed with
```bash
pip install --upgrade "jax[cuda12_pip]" -f https://storage.googleapis.com/jax-releases/jax_cuda_releases.html
```

## Documentation

Available [here](https://simipixel.github.io/x_xy_v2/).

## Publications

The following publications utilize this software library, and refer to it as the *Random Chain Motion Generator (RCMG)* (more specifically the function `x_xy.build_generator`):

- [*RNN-based Observability Analysis for Magnetometer-Free Sparse Inertial Motion Tracking*](https://ieeexplore.ieee.org/document/9841375)
- [*Plug-and-Play Sparse Inertial Motion Tracking With Sim-to-Real Transfer*](https://ieeexplore.ieee.org/document/10225275)
- [*RNN-based State and Parameter Estimation for Sparse Magnetometer-free Inertial Motion Tracking*](https://www.journals.infinite-science.de/index.php/automed/article/view/745)

## Contact

Simon Bachhuber (simon.bachhuber@fau.de)
