### conda-local

`conda` is a widely used tool for managing and deploying applications, environments and packages. But it's very slow sometimes. `conda-local` implement by conda core api and provide a cached repodata for conda actions to speed up conda channel search, metadata collection, and package download. It's a plugin of conda and can also manage environments or packages like conda command. All environments and packages created by `conda-local` can be managed by conda and vice versa. All packages download and extract parallely in `conda-local`.

### Requirement

+ Linux-64
+ Pyhon >= 2.7.10

### Install

To install conda local with pip, run the following command in your `root (base)` environment:

```
$ pip install git+https://github.com/yodeng/conda-local.git
```

### Usage

Before using `conda-local`, command `conda local cache` should be done. This will cache and download all repodata to `LOCAL_CONDA_DIR` (default `$HOME/.conda`) from the default conda mirror [https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud](https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud) . And then all subcommands of `conda-local` will use this cache for action instead of remote channels. If not, `conda-local` still fetch remote matedata that is the same as conda.

```
$ conda local cache
Find channels repodata from https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud: done
[INFO 2022-11-26 18:28:33,182] Starting download ...
[INFO 2022-11-26 18:28:33,182] Donwload success
```

All of the usage is documented via the `--help` flag.

```
$ conda local --help 
usage: conda-local [-h] [-v] command ...

positional arguments:
  command
    install      Installs a list of packages into a specified conda environment from local conda repodata.
    create       Create a new conda environment from a list of specified packages.
    update       Update a list of packages into a specified conda environment from local conda repodata.
    remove       Remove a list of packages from a specified conda environment.
    search       Search for packages from local conda repo and display associated information.
    cache        Cache local conda repodata.
    list         List all available (cached) local conda repodata.

optional arguments:
  -h, --help     Show this help message and exit.
  -v, --version  show program's version number and exit
```

### Cache list

All cached channels repodata can be show by command `conda local list`.

```
$ conda local list
Load cached conda repodata: done
conda-forge:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge
  - packages:
    - linux-64: 318771
    - noarch: 115640
  - size:
    - linux-64: 2633.83 GB
    - noarch: 163.42 GB

bioconda:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/bioconda
  - packages:
    - linux-64: 47862
    - noarch: 41904
  - size:
    - linux-64: 269.61 GB
    - noarch: 158.76 GB

main:
  - cache time: 2022-11-26 03:16:36
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
  - packages:
    - linux-64: 27891
    - noarch: 4717
  - size:
    - linux-64: 157.23 GB
    - noarch: 14.68 GB

r:
  - cache time: 2022-11-26 03:16:36
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r
  - packages:
    - linux-64: 8440
    - noarch: 9493
  - size:
    - linux-64: 8.67 GB
    - noarch: 5.51 GB

free:
  - cache time: 2022-11-26 03:16:36
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free
  - packages:
    - linux-64: 13330
    - noarch: 29
  - size:
    - linux-64: 45.69 GB
    - noarch: 398.7 MB

auto:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/auto
  - packages:
    - linux-64: 12371
    - noarch: 0
  - size:
    - linux-64: 1.18 GB
    - noarch: 0 B

intel:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/intel
  - packages:
    - linux-64: 3800
    - noarch: 142
  - size:
    - linux-64: 78.33 GB
    - noarch: 469.9 MB

numba:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/numba
  - packages:
    - linux-64: 2969
    - noarch: 4
  - size:
    - linux-64: 23.47 GB
    - noarch: 2.7 MB

fastai:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/fastai
  - packages:
    - linux-64: 55
    - noarch: 2680
  - size:
    - linux-64: 1.13 GB
    - noarch: 104.1 MB

rapidsai:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/rapidsai
  - packages:
    - linux-64: 2646
    - noarch: 76
  - size:
    - linux-64: 69.89 GB
    - noarch: 45.6 MB

pytorch:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/pytorch
  - packages:
    - linux-64: 2221
    - noarch: 95
  - size:
    - linux-64: 230.01 GB
    - noarch: 175.6 MB

omnia:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/omnia
  - packages:
    - linux-64: 2131
    - noarch: 45
  - size:
    - linux-64: 11.07 GB
    - noarch: 158.5 MB

pro:
  - cache time: 2022-11-26 03:16:36
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/pro
  - packages:
    - linux-64: 815
    - noarch: 0
  - size:
    - linux-64: 3.82 GB
    - noarch: 0 B

pytorch3d:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/pytorch3d
  - packages:
    - linux-64: 617
    - noarch: 0
  - size:
    - linux-64: 20.88 GB
    - noarch: 0 B

menpo:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/menpo
  - packages:
    - linux-64: 568
    - noarch: 3
  - size:
    - linux-64: 1.53 GB
    - noarch: 7 KB

dglteam:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/dglteam
  - packages:
    - linux-64: 557
    - noarch: 0
  - size:
    - linux-64: 55.84 GB
    - noarch: 0 B

psi4:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/psi4
  - packages:
    - linux-64: 411
    - noarch: 65
  - size:
    - linux-64: 4.32 GB
    - noarch: 11.0 MB

Paddle:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/Paddle
  - packages:
    - linux-64: 431
    - noarch: 0
  - size:
    - linux-64: 123.35 GB
    - noarch: 0 B

pyviz:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/pyviz
  - packages:
    - linux-64: 15
    - noarch: 360
  - size:
    - linux-64: 52.1 MB
    - noarch: 887.8 MB

mro:
  - cache time: 2022-11-26 03:16:36
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/mro
  - packages:
    - linux-64: 359
    - noarch: 0
  - size:
    - linux-64: 392.9 MB
    - noarch: 0 B

qiime2:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/qiime2
  - packages:
    - linux-64: 291
    - noarch: 0
  - size:
    - linux-64: 337.8 MB
    - noarch: 0 B

rdkit:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/rdkit
  - packages:
    - linux-64: 225
    - noarch: 1
  - size:
    - linux-64: 2.37 GB
    - noarch: 22 KB

deepmodeling:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/deepmodeling
  - packages:
    - linux-64: 132
    - noarch: 45
  - size:
    - linux-64: 3.18 GB
    - noarch: 9.2 MB

caffe2:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/caffe2
  - packages:
    - linux-64: 165
    - noarch: 0
  - size:
    - linux-64: 10.09 GB
    - noarch: 0 B

pytorch-test:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/pytorch-test
  - packages:
    - linux-64: 100
    - noarch: 38
  - size:
    - linux-64: 10.69 GB
    - noarch: 106.5 MB

matsci:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/matsci
  - packages:
    - linux-64: 134
    - noarch: 4
  - size:
    - linux-64: 49.7 MB
    - noarch: 354 KB

fermi:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/fermi
  - packages:
    - linux-64: 129
    - noarch: 7
  - size:
    - linux-64: 1.49 GB
    - noarch: 3.31 GB

plotly:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/plotly
  - packages:
    - linux-64: 15
    - noarch: 85
  - size:
    - linux-64: 859.0 MB
    - noarch: 328.0 MB

pytorch-lts:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/pytorch-lts
  - packages:
    - linux-64: 80
    - noarch: 1
  - size:
    - linux-64: 21.78 GB
    - noarch: 2 KB

simpleitk:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/simpleitk
  - packages:
    - linux-64: 71
    - noarch: 0
  - size:
    - linux-64: 2.76 GB
    - noarch: 0 B

biobakery:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/biobakery
  - packages:
    - linux-64: 44
    - noarch: 22
  - size:
    - linux-64: 2.31 GB
    - noarch: 1.50 GB

ursky:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/ursky
  - packages:
    - linux-64: 47
    - noarch: 0
  - size:
    - linux-64: 88.4 MB
    - noarch: 0 B

mordred-descriptor:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/mordred-descriptor
  - packages:
    - linux-64: 43
    - noarch: 1
  - size:
    - linux-64: 1.51 GB
    - noarch: 257 KB

MindSpore:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/MindSpore
  - packages:
    - linux-64: 30
    - noarch: 0
  - size:
    - linux-64: 5.28 GB
    - noarch: 0 B

ohmeta:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/ohmeta
  - packages:
    - linux-64: 4
    - noarch: 9
  - size:
    - linux-64: 12.4 MB
    - noarch: 2.5 MB

stackless:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/stackless
  - packages:
    - linux-64: 10
    - noarch: 0
  - size:
    - linux-64: 252.5 MB
    - noarch: 0 B

c4aarch64:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/c4aarch64
  - packages:
    - noarch: 6
  - size:
    - noarch: 2.3 MB

msys2:
  - cache time: 2022-11-26 03:16:36
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/msys2
  - packages:
    - linux-64: 0
    - noarch: 0
  - size:
    - linux-64: 0 B
    - noarch: 0 B

peterjc123:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/peterjc123
  - packages:
    - noarch: 0
  - size:
    - noarch: 0 B

idaholab:
  - cache time: 2022-11-26 03:22:34
  - url: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/idaholab
  - packages:
    - linux-64: 0
    - noarch: 0
  - size:
    - linux-64: 0 B
    - noarch: 0 B
```
