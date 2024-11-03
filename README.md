[//]: # (This source code is licensed under the MIT license found in the)
[//]: # (LICENSE file in the root directory of this source tree.)

# 🌮 TACOS
## [T]opology-[A]ware [Co]llective Algorithm [S]ynthesizer for Distributed Machine Learning

## Latest Release
[Latest Release](https://github.com/astra-sim/tacos/releases)

## Project Status
| branch | macOS | Ubuntu | Format | Coverage |
|:---:|:---:|:---:|:---:|:---:|
| **main** | TBA | TBA | [![format](https://github.com/astra-sim/tacos/actions/workflows/check-clang-format.yml/badge.svg?branch=main)](https://github.com/astra-sim/tacos/actions/workflows/check-clang-format.yml) | TBA |
| **develop** | TBA | TBA | [![format](https://github.com/astra-sim/tacos/actions/workflows/check-clang-format.yml/badge.svg?branch=develop)](https://github.com/astra-sim/tacos/actions/workflows/check-clang-format.yml) | TBA |

## Overview
TACOS receives an arbitrary point-to-point network topology and autonomously synthesizes the topology-aware All-Reduce (Reduce-Scatter and All-Gather) collective communication algorithm. TACOS is powered by the Time-expanded Network (TEN) representation and Utilization Maximizing Link-Chunk Matching algorithm, thereby resulting in greater scalability to large networks.

Below figure summarizes the TACOS framework:
![TACOS Abstraction](https://github.com/astra-sim/tacos/blob/main/docs/images/tacos_overview.png)

Please find more information about TACOS in [this paper](https://arxiv.org/abs/2304.05301).
- William Won, Midhilesh Elavazhagan, Sudarshan Srinivasan, Swati Gupta, and Tushar Krishna, "TACOS: Topology-Aware Collective Algorithm Synthesizer for Distributed Machine Learning," arXiv:2304.05301 [cs.DC]

## Getting Started
We highly recommend using the provided Docker image as the runtime environment, since TACOS requires several dependencies including protobuf and boost. You can either download the Docker image from the Docker Hub, or you may build one locally using the provided script.

1. Download the TACOS project.
```sh from the parent folder of the TACOS project itself
git clone --recurse-submodules https://github.com/astra-sim/tacos.git
```

2. Pull the TACOS Docker Image.
```sh
docker pull astrasim/tacos:latest

# Instead, you may consider building this Docker Image locally.
./utils/build_docker_image.sh
```

3. Start the Docker Container (which becomes your TACOS runtime environment).
```sh
./utils/start_docker_container.sh
```

4. Run TACOS with the provided script.
```sh
[docker] ./tacos.sh -f input.csv
```

Here is an example `input.csv`:
```txt
5
Src,Dest,Latency (ns),Bandwidth (GB/s)
0,1,500,50
1,2,500,50
2,3,500,50
3,4,500,50
4,0,500,50
```

5. Run BEAM TACOS by passing in an additional argument.
```sh
[docker] ./tacos.sh -f input.csv -b 3
```


If you'd like to analyze the codebase, `src/main.cpp` is the main entry point.

## Contact Us
For any questions about TACOS, please contact [Will Won](mailto:william.won@gatech.edu)
or [Tushar Krishna](mailto:tushar@ece.gatech.edu). You may also find or open a GitHub Issue in this repository.


ring and mesh bc they are entirely possible to do all-gather. we are only doing all-gather rn because that's already implemented. bidirecitonal ring with some slow links clockwise, might be optimal to go the other direction. Mesh with 4 nodes 0, 1, 2, 3; crisscross in middle, test scenarios where criscross is super slow and ring at border is super fast; square not crisscross; cube? inside slow outside is fast

generate these topologies for diff ratios of slow to fast links, and see how the algorithm performs.also for different world sizes of different number of computes

collect synthesized collective time in stdout and make google sheet
./tacos.sh --verbose --file input.csv --run # random TACOS
./tacos.sh --verbose --greedy --file input.csv --run # greedy TACOS (normal, lowest link delay for each chunk matching)
./tacos.sh --verbose --multiple 5 --file input.csv --run # 5 random runs of random TACOS (best being the one with the lowest collective end-to-end time)
``` 