/******************************************************************************
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
*******************************************************************************/

#include <iostream>
#include <tacos/collective/all_gather.h>
#include <tacos/event-queue/timer.h>
#include <tacos/synthesizer/synthesizer.h>
#include <tacos/synthesizer/beam_synthesizer.h>
#include <tacos/topology/mesh_2d.h>
#include <tacos/writer/csv_writer.h>
#include <tacos/writer/synthesis_result.h>

using namespace tacos;

int main(int argc, char* argv[]) {
    // ensure at least one argument
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <filename.csv> [optional_second_argument]" << std::endl;
        return 1;
    }

    // set print precision
    fixed(std::cout);
    std::cout.precision(2);

    // print header
    std::cout << "[TACOS]" << std::endl;
    std::cout << std::endl;

    // construct a topology
    const auto topology = std::make_shared<Topology>();
    topology->connectFromFile(argv[1]);
    const auto npusCount = topology->getNpusCount();

    std::cout << "[Topology Information]" << std::endl;
    std::cout << "\t- NPUs Count: " << npusCount << std::endl;
    std::cout << std::endl;

    // target collective
    const auto chunkSize = 1'048'576;  // B
    const auto initChunksPerNpu = 1;

    const auto collective = std::make_shared<AllGather>(npusCount, chunkSize, initChunksPerNpu);
    const auto chunksCount = collective->getChunksCount();

    std::cout << "[Collective Information]" << std::endl;
    const auto chunkSizeMB = chunkSize / (1 << 20);
    std::cout << "\t- Chunks Count: " << chunksCount << std::endl;
    std::cout << "\t- Chunk Size: " << chunkSize << " B";
    std::cout << " (" << chunkSizeMB << " MB)" << std::endl;
    std::cout << std::endl;


    // create timer
    auto timer = Timer();

    // synthesize collective algorithm
    std::cout << "[Synthesis Process]" << std::endl;

    timer.start();
    SynthesisResult synthesisResult(topology, collective);
    if (argc < 3) {
        // No beam argument: use Synthesizer
        auto synthesizer = std::make_unique<Synthesizer>(topology, collective);
        std::cout << "[Using Synthesizer]" << std::endl;
        synthesisResult = synthesizer->synthesize();  // Call synthesize on SynthesizerBase pointer
    } else {
        // Second argument provided: use BeamSynthesizer
        int beam_width;
        try {
            beam_width = std::stoi(argv[2]);
        } catch (const std::invalid_argument& e) {
            std::cerr << "Error: Second argument must be an integer." << std::endl;
            return 1;
        }
        auto synthesizer = std::make_unique<BeamSynthesizer>(topology, collective, beam_width);
        std::cout << "[Using BeamSynthesizer with beam width: " << beam_width << "]" << std::endl;
        synthesisResult = synthesizer->synthesize();  // Call synthesize on SynthesizerBase pointer
    }
    timer.stop();

    std::cout << std::endl;

    // print result
    std::cout << "[Synthesis Result]" << std::endl;

    const auto elapsedTimeUSec = timer.elapsedTime();
    const auto elapsedTimeSec = elapsedTimeUSec / 1e6;
    std::cout << "\t- Time to solve: " << elapsedTimeUSec << " us";
    std::cout << " (" << elapsedTimeSec << " s)" << std::endl;

    const auto collectiveTimePS = synthesisResult.getCollectiveTime();
    const auto collectiveTimeUSec = collectiveTimePS / 1.0e6;
    std::cout << "\t- Synthesized Collective Time: " << collectiveTimePS << " ps";
    std::cout << " (" << collectiveTimeUSec << " us)" << std::endl;
    std::cout << std::endl;

    // write results to file
    std::cout << "[Synthesis Result Dump]" << std::endl;
    const auto csvWriter = CsvWriter(topology, collective, synthesisResult);
    csvWriter.write("tacos_synthesis_result.csv");

    std::cout << std::endl;

    // terminate
    std::cout << "[TACOS] Done!" << std::endl;
    return 0;
}
