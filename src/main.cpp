/******************************************************************************
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
*******************************************************************************/

#include <iostream>
#include <tacos/collective/all_gather.h>
#include <tacos/event-queue/timer.h>
#include <tacos/synthesizer/synthesizer.h>
#include <tacos/synthesizer/greedy_synthesizer.h>
#include <tacos/synthesizer/multiple_synthesizer.h>
#include <tacos/synthesizer/beam_synthesizer.h>
#include <tacos/synthesizer/synthesizer.h>
#include <tacos/synthesizer/greedy_synthesizer.h>
#include <tacos/topology/mesh_2d.h>
#include <tacos/writer/csv_writer.h>
#include <tacos/writer/synthesis_result.h>

using namespace tacos;

std::string createOutfileName(const std::string& filename, const std::string& suffix) {
    // Find the position of the last '/' to get the base filename
    size_t lastSlashPos = filename.find_last_of("/\\");
    std::string baseName = (lastSlashPos == std::string::npos) ? filename : filename.substr(lastSlashPos + 1);

    // Remove the last four characters (assumes ".csv" extension)
    if (baseName.size() > 4 && baseName.substr(baseName.size() - 4) == ".csv") {
        baseName = baseName.substr(0, baseName.size() - 4);
    }

    // Create the output file name
    return baseName + "_" + suffix + "_result.csv";
}

int main(int argc, char* argv[]) {
    // ensure at least one argument
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <filename.csv> [optional_second_argument]"
                  << std::endl;
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

    // Choose synthesizer based on the flag provided
    timer.start();
    SynthesisResult synthesisResult(topology, collective);
    std::string out_filename;
    if (argc == 2) {
        // No additional argument: use Synthesizer
        auto synthesizer = std::make_unique<Synthesizer>(topology, collective);
        std::cout << "[Using Synthesizer]" << std::endl;
        synthesisResult = synthesizer->synthesize();
        out_filename = createOutfileName(argv[1],"tacos");
    } else if (argc >= 3) {
        std::string flag = argv[2];
        if (flag == "--greedy") {
            // GreedySynthesizer
            auto synthesizer = std::make_unique<GreedySynthesizer>(topology, collective);
            std::cout << "[Using GreedySynthesizer]" << std::endl;
            synthesisResult = synthesizer->synthesize();
            out_filename = createOutfileName(argv[1],"greedy");
        }
        else if (flag == "--multiple") {
            // MultipleSynthesizer with specified multiple factor
            int num_beams;
            // Attempt to parse the integer argument
            try {
                num_beams = std::stoi(argv[3]);
            } catch (const std::invalid_argument& e) {
                std::cerr << "Error: Argument following " << flag << " must be an integer." << std::endl;
                return 1;
            }
            auto synthesizer = std::make_unique<MultipleSynthesizer>(topology, collective, num_beams);
            std::cout << "[Using MultipleSynthesizer with factor: " << num_beams << "]" << std::endl;
            synthesisResult = synthesizer->synthesize();
            out_filename = createOutfileName(argv[1],"multiple_"+std::to_string(num_beams));
        }
        else if (flag == "--beam") {
            // BeamSynthesizer with specified beam width
            int num_beams;
            // Attempt to parse the integer argument
            try {
                num_beams = std::stoi(argv[3]);
            } catch (const std::invalid_argument& e) {
                std::cerr << "Error: Argument following " << flag << " must be an integer." << std::endl;
                return 1;
            }
            auto synthesizer = std::make_unique<BeamSynthesizer>(topology, collective, num_beams);
            std::cout << "[Using BeamSynthesizer with beam width: " << num_beams << "]" << std::endl;
            synthesisResult = synthesizer->synthesize();
            out_filename = createOutfileName(argv[1],"beam_"+std::to_string(num_beams));
        }
        else {
            std::cerr << "Error: Invalid flag. Use --greedy, --multiple <integer>, or --beam <integer>." << std::endl;
            return 1;
        }
    } else {
        std::cerr << "Error: Invalid arguments. Usage: " << argv[0] << " <filename.csv> [--greedy | --multiple <integer> | --beam <integer>]" << std::endl;
        return 1;
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
    csvWriter.write(out_filename);

    std::cout << std::endl;

    // terminate
    std::cout << "[TACOS] Done!" << std::endl;
    return 0;
}
