import csv
import os
import argparse
import random
import subprocess
import re
from typing import Optional, Tuple, List


def create_ring_csv_files(group_sizes: str, bad_bandwidth_proportions: str, bad_magnitudes: str, output_dir: str = 'ring_csvs') -> None:
    """
    Generates CSV files representing ring topologies with specified group sizes and proportions of bad bandwidth nodes.

    Args:
        group_sizes (str): The number of nodes in each group.
        bad_bandwidth_proportions (str): The proportions of bad bandwidth nodes.
        output_dir (str): Directory where CSV files will be stored.
    """
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    print(f"CSV files will be generated in the '{output_dir}' directory.")

    # No need to split here as the arguments are already strings
    for magnitude in map(int, bad_magnitudes.split()):
        for group_size in map(int, group_sizes.split()):
            for bad_bandwidth_proportion in map(float, bad_bandwidth_proportions.split()):
                csv_filename = f"ring_{group_size}_{bad_bandwidth_proportion}_{magnitude}.csv"
                csv_path = os.path.join(output_dir, csv_filename)
                
                with open(csv_path, 'w', newline='') as csvfile:
                    csvwriter = csv.writer(csvfile)
                    csvwriter.writerow([group_size])
                    csvwriter.writerow(['Src', 'Dest', 'Latency (ns)', 'Bandwidth (GB/s)'])
                    
                    # Calculate the number of bad links based on the proportion
                    num_bad_links = max(1, int(group_size * bad_bandwidth_proportion))
                    bad_links = random.sample(range(group_size), num_bad_links)
                    print(f"Generating CSV: {csv_filename} | Group Size: {group_size} | Bad Links: {bad_links} | Bad Magnitude: {magnitude}")

                    # Create links between consecutive nodes
                    for i in range(group_size - 1):
                        src = i
                        dest = i + 1
                        latency = 500  # in nanoseconds
                        bandwidth = 1 if i not in bad_links else magnitude  # Bad bandwidth
                        csvwriter.writerow([src, dest, latency, bandwidth])
                        csvwriter.writerow([dest, src, latency, bandwidth])
                    
                    # Closing the ring by connecting the last node to the first
                    src = group_size - 1
                    dest = 0
                    latency = 500
                    bandwidth = 1 if (group_size - 1) not in bad_links else magnitude
                    csvwriter.writerow([src, dest, latency, bandwidth])
                    csvwriter.writerow([dest, src, latency, bandwidth])
        
    print("CSV file generations completed.\n")


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


def get_file_parameters(filename: str) -> Tuple[str, str, str]:
    """
    Extracts group_size and bad_bandwidth_proportion from the filename.
    Assumes that the filename follows the pattern 'ring_<group_size>_<bad_bandwidth_proportion>.csv'.

    Args:
        filename (str): The name of the file.

    Returns:
        Tuple[str, str]: A tuple containing group_size and bad_bandwidth_proportion.
    """
    match = re.match(r'ring_(\d+)_(\d*\.?\d*)_(\d*\.?\d*)\.csv', filename)
    if match:
        group_size = match.group(1)
        bad_bandwidth_proportion = match.group(2)
        magnitude = match.group(3)
        return group_size, bad_bandwidth_proportion, magnitude
    else:
        return "N/A", "N/A", "N/A"


def run_tacos_commands(input_dir: str, output_csv: str = 'ring_results.csv') -> None:
    """
    Executes tacos.sh commands for each CSV file in the input directory, extracts synthesis times,
    and writes the results to an output CSV file.

    Args:
        input_dir (str): Directory containing input CSV files.
        output_csv (str): Path to the output results CSV file.
    """
    algorithms = [
        {"name": "random", "args": ["--run"]},
        {"name": "greedy", "args": ["--greedy", "--run"]},
        {"name": "multiple_5", "args": ["--multiple", "5", "--run"]}
    ]

    with open(output_csv, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(['group_size', 'bad_bandwidth_proportion', 'bad_magnitude','algorithm', 'synthesis_time_ps', ])
        print(f"Results will be written to '{output_csv}'.\n")

        for filename in sorted(os.listdir(input_dir)):
            if not filename.endswith('.csv'):
                continue

            filepath = os.path.join(input_dir, filename)
            group_size, bad_bandwidth_proportion, magnitude = get_file_parameters(filename)
            print(f"Processing File: {filename} | Group Size: {group_size} | Bad Bandwidth Proportion: {bad_bandwidth_proportion} | Bad Magnitude: {magnitude}")

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
                        csvwriter.writerow([group_size, bad_bandwidth_proportion, magnitude,algo_name, best_time])
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
                        csvwriter.writerow([group_size, bad_bandwidth_proportion, magnitude, algo_name, synthesis_time])
                        print(f"    Extracted Synthesis Time for '{algo_name}': {synthesis_time} ps\n")
                    else:
                        print(f"    Synthesis time not found in output for '{algo_name}' on '{filename}'.\n")

    print("All commands executed and results recorded.\n")


def main(group_sizes: str, bad_bandwidth_proportions: str, bad_magnitudes: str) -> None:
    """
    Main function to generate CSV files and process them with tacos.sh commands.

    Args:
        group_sizes (str): Space-separated string of group sizes.
        bad_bandwidth_proportions (str): Space-separated string of bad bandwidth proportions.
    """
    directory = f"ringcsvs_g{group_sizes}_b{bad_bandwidth_proportions}_m{bad_magnitudes}"
    create_ring_csv_files(group_sizes, bad_bandwidth_proportions, bad_magnitudes, directory)
    run_tacos_commands(directory, f"ring_results_g{group_sizes}_b{bad_bandwidth_proportions}_m{bad_magnitudes}.csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "This script generates ring topology CSV files based on given group sizes and proportions "
            "of bad bandwidth nodes. It then executes the 'tacos.sh' script with various algorithms on "
            "each CSV file, extracts the synthesized collective time, and compiles the results into "
            "'ring_results.csv'."
        )
    )
    parser.add_argument(
        "group_sizes",
        type=str,
        help="The number of nodes in each group (e.g., 5 10 15)"
    )
    parser.add_argument(
        "bad_bandwidth_proportions",
        type=str,
        help="The proportions of bad bandwidth nodes (e.g., 0.1 0.2 0.3)"
    )
    parser.add_argument(
        "bad_magnitudes",
        type=str,
        help="The magnitudes of bad bandwidth nodes (e.g., 5, 10, 50)"
    )
    args = parser.parse_args()
    main(args.group_sizes, args.bad_bandwidth_proportions, args.bad_magnitudes)