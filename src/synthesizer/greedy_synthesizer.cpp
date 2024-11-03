/******************************************************************************
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
*******************************************************************************/

#include <algorithm>
#include <cassert>
#include <iostream>
#include <tacos/synthesizer/greedy_synthesizer.h>

using namespace tacos;

#define N 1

GreedySynthesizer::GreedySynthesizer(const std::shared_ptr<Topology> topology,
                         const std::shared_ptr<Collective> collective,
                         const bool verbose) noexcept
    : topology(topology),
      collective(collective),
      synthesisResult(topology, collective),
      ten(topology),
      verbose(verbose) {
    assert(topology != nullptr);
    assert(collective != nullptr);

    npusCount = topology->getNpusCount();
    chunksCount = collective->getChunksCount();

    // set topology chunk size
    const auto chunkSize = collective->getChunkSize();
    topology->setChunkSize(chunkSize);
    distinctLinkDelays = topology->getDistinctLinkDelays();
    if (verbose) {
        std::cout << "Distinct Link Delays: ";
        for (const auto& delay : distinctLinkDelays) {
            std::cout << delay << " ";
        }
        std::cout << std::endl;
    }

    // setup initial precondition and postcondition
    precondition = collective->getPrecondition();
    postcondition = collective->getPostcondition();

    // setup initial events
    currentTime = eventQueue.getCurrentTime();
    scheduleNextEvents();
}

SynthesisResult GreedySynthesizer::synthesize() noexcept {
    while (!eventQueue.empty()) {
        // update current time
        currentTime = eventQueue.pop();

        // update TEN current time
        ten.updateCurrentTime(currentTime);

        // run link-chunk matching
        linkChunkMatching();

        // if synthesis is completed, break
        if (synthesisCompleted()) {
            break;
        }

        // if synthesis is not finished, schedule next events
        scheduleNextEvents();
    }

    assert(synthesisCompleted());

    synthesisResult.setCollectiveTime(currentTime);
    return synthesisResult;
}

void GreedySynthesizer::scheduleNextEvents() noexcept {
    assert(!distinctLinkDelays.empty());

    for (const auto linkDelay : distinctLinkDelays) {
        const auto nextEventTime = currentTime + linkDelay;
        eventQueue.schedule(nextEventTime);
    }
}

void GreedySynthesizer::linkChunkMatching() noexcept {
    // get current precondition and postcondition
    const auto currentPrecondition = precondition;
    auto currentPostcondition = postcondition;

    // iterate over all unsatisfied postconditions
    while (!currentPostcondition.empty()) {
        // randomly select one postcondition
        const auto [dest, chunk] = selectPostcondition(&currentPostcondition);

        // backtrack the TEN to find potential source NPUs
        const auto sourceNpus = ten.backtrackTEN(dest);

        // among the sourceNpus, find the candidate sources
        const auto candidateSourceNpus =
            checkCandidateSourceNpus(chunk, currentPrecondition, sourceNpus);

        // if there are no candidate source NPUs, skip
        if (candidateSourceNpus.empty()) {
            continue;
        }

        // randomly select one candidate source NPU
        auto src = selectSourceNpu(candidateSourceNpus, dest);

        // link-chunk match made: mark this
        markLinkChunkMatch(src, dest, chunk);
    }
}

std::pair<GreedySynthesizer::NpuID, GreedySynthesizer::ChunkID> GreedySynthesizer::selectPostcondition(
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

std::set<GreedySynthesizer::NpuID> GreedySynthesizer::checkCandidateSourceNpus(
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

GreedySynthesizer::NpuID GreedySynthesizer::selectSourceNpu(
    const std::set<NpuID>& candidateSourceNpus, NpuID dest) noexcept {
    assert(!candidateSourceNpus.empty());

    // if only one candidate source NPU, return it
    if (candidateSourceNpus.size() == 1) {
        if (verbose) {
            std::cout << "Candidate Source NPU: " << *candidateSourceNpus.begin() << std::endl;
        }
        const auto firstCandidate = candidateSourceNpus.begin();
        return *firstCandidate;
    }

    // sort condidate source NPUs by linkDelay[src][dest]
    auto linkDelays = std::vector<std::pair<NpuID, Time>>();
    for (const auto src : candidateSourceNpus) {
        const auto linkDelay = topology->getLinkDelay(src, dest);
        linkDelays.emplace_back(src, linkDelay);
    }
    std::sort(linkDelays.begin(), linkDelays.end(),
              [](const auto& a, const auto& b) { return a.second > b.second; });

    if (verbose) {
        std::cout << "Candidate Source NPUs [sorted]: ";
        for (const auto& [src, delay] : linkDelays) {
            std::cout << src << " -> " << dest << " (" << delay << " ps) ";
        }
        std::cout << std::endl;
    }

    // return the Nth best candidate source NPU
    const auto bestCandidate = linkDelays[N].first;
    return bestCandidate;
}

void GreedySynthesizer::markLinkChunkMatch(const NpuID src,
                                     const NpuID dest,
                                     const ChunkID chunk) noexcept {
    // mark the link-chunk match
    if (verbose) {
        std::cout << "[EventTime " << currentTime << " ps] ";
        std::cout << "Chunk " << chunk << ": " << src << " -> " << dest << std::endl;
    }

    const auto linkDelay = topology->getLinkDelay(src, dest);
    const StartTime transmissionStartTime = currentTime - linkDelay;

    // mark the synthesis result
    synthesisResult.markLinkChunkMatch(chunk, src, dest, currentTime, transmissionStartTime);

    // mark the link as occupied
    ten.markLinkOccupied(src, dest);

    // insert the chunk to the precondition
    precondition[dest].insert(chunk);

    // remove the chunk from the postcondition
    postcondition[dest].erase(chunk);

    // if there's no remaining postcondition of the dest, remove it
    if (postcondition[dest].empty()) {
        postcondition.erase(dest);
    }
}

bool GreedySynthesizer::synthesisCompleted() const noexcept {
    // synthesis is done when there's no remaining postcondition
    return postcondition.empty();
}
