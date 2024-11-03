/******************************************************************************
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
*******************************************************************************/

#pragma once

#include <map>
#include <memory>
#include <optional>
#include <tacos/collective/collective.h>
#include <tacos/topology/topology.h>
#include <vector>

namespace tacos {

class NpuResult {
  public:
    using NpuID = Topology::NpuID;
    using ChunkID = Collective::ChunkID;
    using Time = Topology::Time;
    using StartTime = Topology::StartTime;

    NpuResult(int npu,
              std::shared_ptr<Topology> topology,
              std::shared_ptr<Collective> collective) noexcept;

    void addIngressLinkInfo(ChunkID chunk,
                            NpuID src,
                            Time currentTime,
                            StartTime transmissionStartTime) noexcept;

    void addEgressLinkInfo(ChunkID chunk,
                           NpuID dest,
                           Time currentTime,
                           StartTime transmissionStartTime) noexcept;

    std::vector<std::tuple<ChunkID, Time, StartTime>> getIngressLinkInfo(NpuID src) const noexcept;

    std::vector<std::tuple<ChunkID, Time, StartTime>> getEgressLinkInfo(NpuID dest) const noexcept;

  private:
    int npu;
    int npusCount;
    int chunksCount;
    std::map<NpuID, std::vector<std::tuple<ChunkID, Time, StartTime>>> ingressLinksInfo;
    std::map<NpuID, std::vector<std::tuple<ChunkID, Time, StartTime>>> egressLinksInfo;

    std::map<ChunkID, std::optional<int>> dependencyInfo;
};

}  // namespace tacos
