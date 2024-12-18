/******************************************************************************
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
*******************************************************************************/

#pragma once

#include <memory>
#include <tacos/event-queue/event_queue.h>
#include <tacos/topology/topology.h>

namespace tacos {

class TimeExpandedNetwork {
  public:
    using Time = EventQueue::Time;
    using StartTime = EventQueue::StartTime;
    using NpuID = Topology::NpuID;

    explicit TimeExpandedNetwork(std::shared_ptr<Topology> topology) noexcept;

    void updateCurrentTime(Time newCurrentTime) noexcept;

    std::set<NpuID> backtrackTEN(NpuID dest) const noexcept;
  
    // std::set<NpuID> backtrackTENWithTimes(NpuID dest) const noexcept;

    void markLinkOccupied(NpuID src, NpuID dest) noexcept;

  private:
    Time currentTime = 0;

    int npusCount;
    std::shared_ptr<Topology> topology;

    std::vector<std::vector<Time>> linkBusyUntil = {};
    std::vector<std::vector<bool>> linkAvailable = {};

    void updateLinkAvailability() noexcept;

    [[nodiscard]] bool checkLinkAvailability(NpuID src, NpuID dest) const noexcept;
};

}  // namespace tacos
