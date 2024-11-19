import csv
import os
import argparse
import random
import subprocess
import re
from typing import Optional, Tuple, Dict, List, Any
import itertools
from tqdm import tqdm
from pprint import pprint
import math

def create_csv_files(output_dir: str, params: Dict[str, List[Any]]) -> None:
    # Create the output directory if it doesn't exist
    output_dir = output_dir.replace('topology', '')
    os.makedirs(output_dir, exist_ok=True)
    print(f"CSV files will be generated in the '{output_dir}' directory.") 
    topology = params['topology']
    del params['topology']
    # NOTE: order of params is important 
    # current order: gs, bm, bbp
    key_order = ['gs', 'bm', 'bbp']
    params_values = [params.get(key, [None]) for key in key_order]
    print(params_values)
    print(list(itertools.product(*params_values)))
    for gs, bm, bbp in itertools.product(*params_values):
        if topology == 'ring': # Bidirectional ring
            csv_filename = f"ring_gs{gs}_bm{bm}_bbp{bbp}.csv"
            csv_path = os.path.join(output_dir, csv_filename)
            
            with open(csv_path, 'w', newline='') as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow([gs])
                csvwriter.writerow(['Src', 'Dest', 'Latency (ns)', 'Bandwidth (GB/s)'])
                
                # Calculate the number of bad links based on the proportion
                num_bad_links = math.ceil(gs * bbp * 2)
                # one direction
                bad_links = random.sample(range(gs * 2), num_bad_links)
                first_direction = bad_links[:len(bad_links)//2]
                second_direction = bad_links[len(bad_links)//2:]
                print(f"Generating CSV: {csv_filename} | Group Size: {gs} | Bad Links: {bad_links} | Bad Magnitude: {bm} | Bad Bandwidth Proportion: {bbp}")

                # Create links between consecutive nodes
                for i in range(gs - 1):
                    src = i
                    dest = i + 1
                    latency = 500  # in nanoseconds
                    bandwidth = 1 if i in first_direction else bm  # Bad bandwidth
                    csvwriter.writerow([src, dest, latency, bandwidth])
                
                # Closing the ring by connecting the last node to the first
                src = gs - 1
                dest = 0
                latency = 500
                bandwidth = 1 if (gs - 1) in first_direction else bm
                csvwriter.writerow([src, dest, latency, bandwidth])
        
                # other direction 
                for i in range(gs - 1):
                    src = i
                    dest = i + 1
                    latency = 500  # in nanoseconds
                    bandwidth = 1 if i in second_direction else bm  # Bad bandwidth
                    csvwriter.writerow([dest, src, latency, bandwidth])
                
                # Closing the ring by connecting the last node to the first
                src = gs - 1
                dest = 0
                latency = 500
                bandwidth = 1 if (gs - 1) in second_direction else bm
                csvwriter.writerow([dest, src, latency, bandwidth])
                
        elif topology == 'mesh':
            csv_filename = f"mesh_gs{gs}_bm{bm}.csv"
            csv_path = os.path.join(output_dir, csv_filename)
            
            with open(csv_path, 'w', newline='') as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow([gs])
                csvwriter.writerow(['Src', 'Dest', 'Latency (ns)', 'Bandwidth (GB/s)'])
                
                # Calculate the number of bad links based on the proportion
                # num_bad_links = max(1, int(gs * bm))
                # bad_links = random.sample(range(gs), num_bad_links)
                print(f"Generating CSV: {csv_filename} | Group Size: {gs} | Bad Magnitude: {bm}")

                # Create links between consecutive nodes
                for i in range(gs - 1):
                    src = i
                    dest = i + 1
                    latency = 500  # in nanoseconds
                    # bandwidth = 1 if i in bad_links else 50  # Bad bandwidth
                    bandwidth  = bm # good bandwidth
                    csvwriter.writerow([src, dest, latency, bandwidth])
                    csvwriter.writerow([dest, src, latency, bandwidth])
                
                # Closing the ring by connecting the last node to the first
                src = gs - 1
                dest = 0
                latency = 500
                bandwidth = bm
                csvwriter.writerow([src, dest, latency, bandwidth])
                csvwriter.writerow([dest, src, latency, bandwidth])

                for i in range(gs):
                    for j in range(gs):
                        if i != j and abs(i-j) != 1:
                            src = i
                            dest = j
                            latency = 500
                            bandwidth = 1
                            csvwriter.writerow([src, dest, latency, bandwidth])
                            csvwriter.writerow([dest, src, latency, bandwidth])
        print(f"CSV file '{csv_filename}' has been generated.")
    return None

def extract_synthesis_time(output: str) -> Optional[int]:
    """
    Extracts the synthesized collective time in picoseconds from the command output.

    Args:
        output (str): The standard output from the shell command.

    Returns:
        Optional[int]: The extracted synthesis time in ps, or None if not found.
    """
    match = re.search(r"Synthesized Collective Time:\s+(\d+)\s+ps", output)
    if match:
        return int(match.group(1))
    else:
        return None
    
def get_used_args(args):
    return {arg: value for arg, value in vars(args).items() if value is not None}

def main(params: Dict[str, List[Any]]) -> None:
    """
    Main function to generate CSV files and process them with tacos.sh commands.
    """
    directory = f"{params['topology']}csvs"
    for key, value in params.items(): 
        directory += f"_{key}{value}"
    create_csv_files(directory, params)
    


    # directory = f"ringcsvs_g{gss}_b{bbps}_m{bms}"
    # create_csv_files(gss, bbps, bms, directory)
    # run_tacos_commands(directory, f"ring_results_g{gss}_b{bbps}_m{bms}.csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "This script generates ring topology CSV files based on given group sizes and proportions "
            "of bad bandwidth nodes. It then executes the 'tacos.sh' script with various algorithms on "
            "each CSV file, extracts the synthesized collective time, and compiles the results into "
            "'ring_results.csv'."
        )
    )
    # Key for params: 
    # gs = group sizes
    # bm = bad magnitudes
    # bbp = bad bandwidth proportions
    parser.add_argument(
        "--topology", 
        type=str,
        default="ring",
        help="The topology to generate CSV files for (e.g., 'ring')"
    )
    parser.add_argument(
        "--gs",
        type=int,
        nargs='+',
        help="The number of nodes in each group (e.g., 5 10 15)"
    )
    parser.add_argument(
        "--bm",
        type=int,
        nargs='+',
        help="The magnitudes of bad bandwidth nodes (e.g., 5, 10, 50)"
    )
    parser.add_argument(
        "--bbp",
        type=float,
        nargs='+',
        help="The proportions of bad bandwidth nodes (e.g., 0.1 0.2 0.3)"
    )
    # NOTE: can add more arguments in a similar format as above as needed
    
    
    args = parser.parse_args()
    used_args = get_used_args(args)
    main(used_args)