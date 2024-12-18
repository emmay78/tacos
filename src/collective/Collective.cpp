/******************************************************************************
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
*******************************************************************************/

#include <cassert>
#include <iostream>
#include <tacos/collective/collective.h>

using namespace tacos;

Collective::Collective(const int npusCount, const ChunkSize chunkSize) noexcept
    : npusCount(npusCount),
      chunkSize(chunkSize) {
    assert(npusCount > 0);
    assert(chunkSize > 0);

    for (auto npu = 0; npu < npusCount; npu++) {
        precondition[npu] = {};
        postcondition[npu] = {};
    }
}

void Collective::add(const ChunkID chunkID, const NpuID src, const NpuID dest) noexcept {
    assert(chunkID >= 0);
    assert(0 <= src && src < npusCount);
    assert(0 <= dest && dest < npusCount);

    chunks.insert(chunkID);
    precondition[src].emplace(chunkID, 0);
    postcondition[dest].insert(chunkID);
}

void Collective::updateChunksCount() noexcept {
    chunksCount = static_cast<int>(chunks.size());
}

Collective::ChunkSize Collective::getChunkSize() const noexcept {
    return chunkSize;
}

int Collective::getChunksCount() const noexcept {
    return chunksCount;
}

Collective::CollectivePrecondition Collective::getPrecondition() const noexcept {
    return precondition;
}

Collective::CollectivePostcondition Collective::getPostcondition() const noexcept {
    return postcondition;
}
