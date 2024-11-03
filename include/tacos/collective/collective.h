/******************************************************************************
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
*******************************************************************************/

#pragma once

#include <map>
#include <set>
#include <tacos/topology/topology.h>

namespace tacos {
class Collective {
  public:
    using ChunkID = int;
    using ChunkSize = Topology::ChunkSize;
    using NpuID = Topology::NpuID;
    using Time = Topology::Time;
    
    using CollectivePrecondition = std::map<NpuID, std::set<std::tuple<ChunkID, Time>>>;
    using CollectivePostcondition = std::map<NpuID, std::set<ChunkID>>;

    Collective(int npusCount, ChunkSize chunkSize) noexcept;

    [[nodiscard]] ChunkSize getChunkSize() const noexcept;

    [[nodiscard]] int getChunksCount() const noexcept;

    [[nodiscard]] CollectivePrecondition getPrecondition() const noexcept;

    [[nodiscard]] CollectivePostcondition getPostcondition() const noexcept;

    [[nodiscard]] bool synthesisCompleted() const noexcept;

  protected:
    int npusCount;
    int chunksCount = 0;

    void add(ChunkID chunkID, NpuID src, NpuID dest) noexcept;

    void updateChunksCount() noexcept;

  private:
    ChunkSize chunkSize;

    std::set<ChunkID> chunks = {};
    CollectivePrecondition precondition = {};
    CollectivePostcondition postcondition = {};
};

}  // namespace tacos
