/******************************************************************************
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
*******************************************************************************/

#include <algorithm>
#include <cassert>
#include <iostream>
#include <tacos/synthesizer/beam_synthesizer.h>

using namespace tacos;

BeamSynthesizer::BeamSynthesizer(const std::shared_ptr<Topology> topology,
                         const std::shared_ptr<Collective> collective,
                         const int num_beams,
                         const bool verbose) noexcept
    : topology(topology),
      collective(collective),
      num_beams(num_beams),
      verbose(verbose) {
    assert(topology != nullptr);
    assert(collective != nullptr);

    npusCount = topology->getNpusCount();
    chunksCount = collective->getChunksCount();

    // set topology chunk size
    const auto chunkSize = collective->getChunkSize();
    topology->setChunkSize(chunkSize);
    distinctLinkDelays = topology->getDistinctLinkDelays();
    
    // std::cout << "\tDistinct Link Delays: ";
    // for (Time const& time : distinctLinkDelays)
    // {
    //     std::cout << time << ' ';
    // }
    // std::cout << std::endl;

    // setup initial precondition and postcondition

    for (int i = 0; i < num_beams; i++) {
        beam_tens.emplace_back(TimeExpandedNetwork(topology));
        beam_preconditions.emplace_back(collective->getPrecondition());
        beam_postconditions.emplace_back(collective->getPostcondition());
        beam_results.emplace_back(SynthesisResult(topology, collective));
    }

    // setup initial events
    currentTime = eventQueue.getCurrentTime();
    scheduleNextEvents();
}

SynthesisResult BeamSynthesizer::synthesize() noexcept {
    while (!eventQueue.empty()) {
        // update current time
        currentTime = eventQueue.pop();
        std::cout << "\tCurrent Time: " << currentTime << std::endl;
        for (int i = 0; i < num_beams; i++) {
            if(!synthesisCompleted(i)) {
                std::cout << "HI:" << i << std::endl;
                // update TEN current time
                beam_tens[i].updateCurrentTime(currentTime);
                std::cout << "HI2:" << i << std::endl;
                // run link-chunk matching
                linkChunkMatching(i);
            }
            else if (beam_results[i].getCollectiveTime()==0) {
                beam_results[i].setCollectiveTime(currentTime);
            }
            else {
                std::cout << "WELP" << std::endl;
            }
        }

        // if synthesis is completed, break
        for(int i=0; i<num_beams; i++) {
            std::cout << synthesisCompleted(i) << std::endl;
        }
        std::vector<int> indices(num_beams, 0);
        std::generate(indices.begin(), indices.end(), [n = 0]() mutable { return n++; });

        if (std::all_of(indices.begin(), indices.end(),
                        [this](int i) { return synthesisCompleted(i); })) {
            break;
        }

        // if (std::all_of()) {
        //     break;
        // }
        // if (std::all_of(std::vector<int>(num_beams, 0).begin(), std::vector<int>(num_beams, 0).end(),
        //         [this, n=0](int) mutable { return synthesisCompleted(n++); })) {
        //     break;
        // }

        // if synthesis is not finished, schedule next events
        scheduleNextEvents();
    }
    assert(std::all_of(std::vector<int>(num_beams, 0).begin(), std::vector<int>(num_beams, 0).end(),
                [this, n=0](int) mutable { return synthesisCompleted(n++); }));

    for(int i=0; i<num_beams; i++) {
        if (beam_results[i].getCollectiveTime()==0) {
            beam_results[i].setCollectiveTime(currentTime);
        }
    }
    for(int i=0; i<num_beams; i++) {
        std::cout << beam_results[i].getCollectiveTime() << std::endl;
    }

    // return beam_results[0];
    return *std::min_element(beam_results.begin(), beam_results.end(),
        [](const SynthesisResult& a, const SynthesisResult& b) {
            return a.getCollectiveTime() < b.getCollectiveTime();
        }
    );
}

void BeamSynthesizer::scheduleNextEvents() noexcept {
    assert(!distinctLinkDelays.empty());

    for (const auto linkDelay : distinctLinkDelays) {
        const auto nextEventTime = currentTime + linkDelay;
        eventQueue.schedule(nextEventTime);
    }
}

void BeamSynthesizer::linkChunkMatching(int beam_index) noexcept {
    // get current precondition and postcondition
    const auto currentPrecondition = beam_preconditions[beam_index];
    auto currentPostcondition = beam_postconditions[beam_index];

    // iterate over all unsatisfied postconditions
    while (!currentPostcondition.empty()) {
        // randomly select one postcondition
        const auto [dest, chunk] = selectPostcondition(&currentPostcondition);

        // backtrack the TEN to find potential source NPUs
        const auto sourceNpus = beam_tens[beam_index].backtrackTEN(dest);

        // among the sourceNpus, find the candidate sources
        const auto candidateSourceNpus =
            checkCandidateSourceNpus(chunk, currentPrecondition, sourceNpus);

        // if there are no candidate source NPUs, skip
        if (candidateSourceNpus.empty()) {
            continue;
        }

        // randomly select one candidate source NPU
        auto src = selectSourceNpu(candidateSourceNpus);

        // link-chunk match made: mark this
        markLinkChunkMatch(src, dest, chunk, beam_index);
    }
}

std::pair<BeamSynthesizer::NpuID, BeamSynthesizer::ChunkID> BeamSynthesizer::selectPostcondition(
    CollectiveCondition* const currentPostcondition) noexcept {
    assert(currentPostcondition != nullptr);
    assert(!currentPostcondition->empty());

    // randomly pick an entry
    auto postconditionDist = std::uniform_int_distribution<>(0, currentPostcondition->size() - 1);
    int randomNpuIdx = postconditionDist(randomEngine);
    auto randomNpuIt = std::next(currentPostcondition->begin(), randomNpuIdx);
    auto dest = randomNpuIt->first;
    auto& chunks = randomNpuIt->second;

    // randomly pick a chunk
    auto chunkDist = std::uniform_int_distribution<>(0, chunks.size() - 1);
    int randomChunkIdx = chunkDist(randomEngine);
    auto randomChunkIt = std::next(chunks.begin(), randomChunkIdx);
    auto chunk = *randomChunkIt;

    // remove selected chunk from the postcondition
    chunks.erase(randomChunkIt);

    // remove the selected npu, if there's no remaining postcondition
    if (chunks.empty()) {
        currentPostcondition->erase(randomNpuIt);
    }

    // return the selected npu and chunk
    return {dest, chunk};
}

std::set<BeamSynthesizer::NpuID> BeamSynthesizer::checkCandidateSourceNpus(
    const ChunkID chunk,
    const CollectiveCondition& currentPrecondition,
    const std::set<NpuID>& sourceNpus) noexcept {
    assert(0 <= chunk && chunk < chunksCount);
    assert(!currentPrecondition.empty());
    assert(!sourceNpus.empty());

    auto candidateSourceNpus = std::set<NpuID>();

    // check which source NPUs hold the chunk
    for (const auto src : sourceNpus) {
        const auto chunksAtSrc = currentPrecondition.at(src);
        if (chunksAtSrc.find(chunk) != chunksAtSrc.end()) {
            candidateSourceNpus.insert(src);
        }
    }

    return candidateSourceNpus;
}

BeamSynthesizer::NpuID BeamSynthesizer::selectSourceNpu(
    const std::set<NpuID>& candidateSourceNpus) noexcept {
    assert(!candidateSourceNpus.empty());

    // if only one candidate source NPU, return it
    if (candidateSourceNpus.size() == 1) {
        const auto firstCandidate = candidateSourceNpus.begin();
        return *firstCandidate;
    }

    // randomly select one candidate source NPU
    auto candidateSourceNpusDist =
        std::uniform_int_distribution<>(0, candidateSourceNpus.size() - 1);
    int randomSrcIdx = candidateSourceNpusDist(randomEngine);
    auto randomSrcIt = std::next(candidateSourceNpus.begin(), randomSrcIdx);
    return *randomSrcIt;
}

void BeamSynthesizer::markLinkChunkMatch(const NpuID src,
                                     const NpuID dest,
                                     const ChunkID chunk,
                                     int beam_index) noexcept {
    // mark the link-chunk match
    if (verbose) {
        std::cout << "[EventTime " << currentTime << " ps] ";
        std::cout << "Beam " << beam_index << ": " << "Chunk " << chunk << ": " << src << " -> " << dest << std::endl;
    }

    // mark the synthesis result
    beam_results[beam_index].markLinkChunkMatch(chunk, src, dest);

    // insert the chunk to the precondition
    beam_preconditions[beam_index][dest].insert(chunk);

    // remove the chunk from the postcondition
    beam_postconditions[beam_index][dest].erase(chunk);

    // if there's no remaining postcondition of the dest, remove it
    if (beam_postconditions[beam_index][dest].empty()) {
        beam_postconditions[beam_index].erase(dest);
    }
}

bool BeamSynthesizer::synthesisCompleted(int beam_index) const noexcept {
    // synthesis is done when there's no remaining postcondition
    return beam_postconditions[beam_index].empty();
}
