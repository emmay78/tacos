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
import time

def create_csv_files(output_dir: str, params: Dict[str, List[Any]]) -> None:
    # Create the output directory if it doesn't exist
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
               
                print(f"Generating CSV: {csv_filename} | Group Size: {gs} | Bad Links: {bad_links} | Bad Magnitude: {bm} | Bad Bandwidth Proportion: {bbp}")

                # Create links between consecutive nodes
                for i in range(gs - 1):
                    src = i
                    dest = i + 1
                    latency = 500  # in nanoseconds
                    bandwidth = 1 if i in bad_links else bm  # Bad bandwidth
                    csvwriter.writerow([src, dest, latency, bandwidth])
                
                # Closing the ring by connecting the last node to the first
                src = gs - 1
                dest = 0
                latency = 500
                bandwidth = 1 if (gs - 1) in bad_links else bm
                csvwriter.writerow([src, dest, latency, bandwidth])
        
                # other direction 
                for i in range(gs - 2, 0, -1):
                    src = i
                    dest = i - 1
                    latency = 500  # in nanoseconds
                    bandwidth = 1 if i + gs in bad_links else bm  # Bad bandwidth
                    csvwriter.writerow([src, dest, latency, bandwidth])
                
                # Closing the ring by connecting the last node to the first
                src = 0
                dest = gs - 1
                latency = 500
                bandwidth = 1 if (2 * gs - 1) in bad_links else bm
                csvwriter.writerow([src, dest, latency, bandwidth])
                
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
        elif topology == 'hierarchical':
            csv_filename = f"hierarchical_gs{gs}_bm{bm}.csv"
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

def run_command(command: List[str], cwd: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Executes a shell command and captures its standard output and standard error.

    Args:
        command (List[str]): The command and its arguments as a list.
        cwd (Optional[str]): Directory to run the command in.

    Returns:
        Tuple[Optional[str], Optional[str]]: A tuple containing stdout and stderr, or (None, None) if an error occurs.
    """
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        print(f"Command '{' '.join(command)}' failed with exit code {e.returncode}")
        print(f"Error Output: {e.stderr}")
        return None, None
    except FileNotFoundError:
        print(f"Command not found: {command[0]}")
        return None, None

def get_file_parameters(filename: str):
    """
    Extracts group_size and bad_bandwidth_proportion from the filename.
    Assumes that the filename follows the pattern 'ring_<group_size>_<bad_bandwidth_proportion>.csv'.

    Args:
        filename (str): The name of the file.

    Returns:
        Dict[str, List[Any]]: A dictionary containing the extracted parameters.
    """
    # extracting the existing parameters using _ as essentially a delimiter 
    pattern = r'-?\d+\.?\d*'
    # extracts the parameter value as well as the starting index of the match for each match
    matches = [(match.group(), match.start()) for match in re.finditer(pattern, filename)]
    # constructing the parameters dictionary 
    parameters = {}
    for value, index in matches: 
        parameters[filename[filename.rfind('_', 0, index) + 1:index]] = value
    return parameters


def run_tacos_commands(params_list: List[str], input_dir: str, output_csv: str = 'ring_results.csv') -> None:
    """
    Executes tacos.sh commands for each CSV file in the input directory, extracts synthesis times,
    and writes the results to an output CSV file.

    Args:
        params: dictionary mapping parameteres to their list of diff values
        input_dir (str): Directory containing input CSV files.
        output_csv (str): Path to the output results CSV file.
    """
    params_list.append("Algorithm")
    params_list.append("Synthesis Time (ps)")
    algorithms = [
        {"name": "random", "args": ["--run"]},
        {"name": "greedy", "args": ["--greedy", "--run"]},
        {"name": "multiple_5", "args": ["--multiple", "5", "--run"]}
    ]

    now_str = time.strftime("%Y%m%d-%H%M%S")
    os.mkdir(now_str)
    output_csv = os.path.join(now_str, output_csv)

    with open(output_csv, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(params_list)
        print(f"Results will be written to '{output_csv}'.\n")
        print(sorted(os.listdir(input_dir)))
        print("input_dir: ", input_dir)
        for filename in sorted(os.listdir(input_dir)):
            if not filename.endswith('.csv'):
                continue

            filepath = os.path.join(input_dir, filename)
            file_params = get_file_parameters(filename)
            #print(f"Processing File: {filename} | Group Size: {group_size} | Bad Bandwidth Proportion: {bad_bandwidth_proportion} | Bad Magnitude: {magnitude}")

            for algo in algorithms:
                algo_name = algo["name"]
                algo_args = algo["args"]

                if algo_name == "multiple_5":
                    synthesis_times = []
                    for run in range(1, 6):
                        command = ["./tacos.sh", "--verbose", "--file", filepath] + algo_args
                        print(f"  Running '{algo_name}' - Attempt {run}/5")
                        stdout, stderr = run_command(command)

                        if stdout is None:
                            print(f"    Failed to execute '{algo_name}' on '{filename}'. Skipping this run.")
                            continue

                        synthesis_time = extract_synthesis_time(stdout)
                        if synthesis_time is not None:
                            synthesis_times.append(synthesis_time)
                            print(f"    Extracted Synthesis Time: {synthesis_time} ps")
                        else:
                            print(f"    Synthesis time not found in output for '{algo_name}' on '{filename}'.")

                    if synthesis_times:
                        best_time = min(synthesis_times)
                        row = []
                        for key in file_params:
                            row.append(file_params[key])
                        row.append(algo_name)
                        row.append(best_time)
                        csvwriter.writerow(row)
                        print(f"    Best Synthesis Time for '{algo_name}': {best_time} ps\n")
                    else:
                        print(f"    No valid synthesis times extracted for '{algo_name}' on '{filename}'.\n")
                else:
                    command = ["./tacos.sh", "--verbose", "--file", filepath] + algo_args
                    print(f"  Running '{algo_name}'")
                    stdout, stderr = run_command(command)

                    if stdout is None:
                        print(f"    Failed to execute '{algo_name}' on '{filename}'. Skipping.\n")
                        continue

                    synthesis_time = extract_synthesis_time(stdout)
                    if synthesis_time is not None:
                        row = []
                        for key in file_params:
                            row.append(file_params[key])
                        row.append(algo_name)
                        row.append(synthesis_time)
                        csvwriter.writerow(row)
                        print(f"    Extracted Synthesis Time for '{algo_name}': {synthesis_time} ps\n")
                    else:
                        print(f"    Synthesis time not found in output for '{algo_name}' on '{filename}'.\n")

    print("All commands executed and results recorded.\n")

def get_used_args(args):
    return {arg: value for arg, value in vars(args).items() if value is not None}

def main(params: Dict[str, List[Any]]) -> None:
    """
    Main function to generate CSV files and process them with tacos.sh commands.
    """
    directory =  os.path.join("csvs", f"{params['topology']}") 
    for key, value in params.items(): 
        if key != 'topology':
            directory += f"_{key}{value}"
    output_csv = directory.replace("csvs/", "") + ".csv"
    create_csv_files(directory, params)
    # run_tacos_commands(directory, f"ring_results_g{group_sizes}_b{bad_bandwidth_proportions}_m{bad_magnitudes}.csv")
    run_tacos_commands(list(params.keys()), directory, output_csv)
    print("Directory", directory)


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
    # Key for params: IMPT DO NOT INCLUDE _ (underscores) in param names
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