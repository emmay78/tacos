/******************************************************************************
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
*******************************************************************************/

#pragma once

#include <memory>
#include <random>
#include <tacos/collective/collective.h>
#include <tacos/event-queue/event_queue.h>
#include <tacos/synthesizer/time_expanded_network.h>
#include <tacos/topology/topology.h>
#include <tacos/writer/synthesis_result.h>

namespace tacos {

class BeamSynthesizer {
  public:
    using Time = EventQueue::Time;
    using StartTime = EventQueue::StartTime;
    using NpuID = Topology::NpuID;
    using ChunkID = Collective::ChunkID;
    using ChunkSize = Topology::ChunkSize;
    using CollectiveCondition = Collective::CollectiveCondition;

    BeamSynthesizer(std::shared_ptr<Topology> topology,
                std::shared_ptr<Collective> collective,
                const int num_beams,
                bool verbose = false) noexcept;

    [[nodiscard]] SynthesisResult synthesize() noexcept;

  private:
    EventQueue eventQueue = {};
    Time currentTime;

    std::shared_ptr<Topology> topology;
    std::shared_ptr<Collective> collective;

    int npusCount;
    int chunksCount;

    bool verbose;

    // beams
    int num_beams;
    std::vector<TimeExpandedNetwork> beam_tens;
    std::vector<CollectiveCondition> beam_preconditions;
    std::vector<CollectiveCondition> beam_postconditions;
    std::vector<SynthesisResult> beam_results;

    // topology link delays
    std::set<Time> distinctLinkDelays = {};

    // random devices
    std::random_device randomDevice = {};
    std::mt19937 randomEngine = decltype(randomEngine)(randomDevice());

    void scheduleNextEvents() noexcept;

    void linkChunkMatching(int beam_index) noexcept;

    [[nodiscard]] std::pair<NpuID, ChunkID> selectPostcondition(
        CollectiveCondition* const currentPostcondition) noexcept;

    [[nodiscard]] std::set<NpuID> checkCandidateSourceNpus(
        ChunkID chunk,
        const CollectiveCondition& currentPrecondition,
        const std::set<NpuID>& sourceNpus) noexcept;

    [[nodiscard]] NpuID selectSourceNpu(const std::set<NpuID>& candidateSourceNpus) noexcept;

    void markLinkChunkMatch(NpuID src, NpuID dest, ChunkID chunk, int beam_index) noexcept;

    [[nodiscard]] bool synthesisCompleted(int beam_index) const noexcept;
};

}  // namespace tacos
