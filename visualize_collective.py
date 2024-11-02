import csv
import argparse
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Slider, Button


def process_collective_algo(filename):
    data = {
        "NPU_Count": None,
        "Links_Count": None,
        "Chunks_Count": None,
        "Chunk_Size": None,
        "Collective_Time": None,
        "Connections": [],
    }

    with open(filename, mode="r") as file:
        reader = csv.reader(file)
        for i, row in enumerate(reader):
            # Read the metadata from the first few lines
            if i == 0 and row[0].startswith("NPUs Count"):
                data["NPU_Count"] = int(row[1])
            elif i == 1 and row[0].startswith("Links Count"):
                data["Links_Count"] = int(row[1])
            elif i == 2 and row[0].startswith("Chunks Count"):
                data["Chunks_Count"] = int(row[1])
            elif i == 3 and row[0].startswith("Chunk Size"):
                data["Chunk_Size"] = int(row[1])
            elif i == 4 and row[0].startswith("Collective Time"):
                data["Collective_Time"] = int(row[1])
            # Read the connections data starting from the fifth line
            elif i == 5 and row[0].startswith("SrcID"):
                header = row
            elif i >= 6:
                src_id = int(row[0])
                dest_id = int(row[1])
                latency_ns = int(row[2])
                bandwidth_gbps = float(row[3])

                # Parse Chunks column
                chunks = []
                for chunk in row[4:]:
                    if chunk == "None":
                        break
                    chunk_id, arrival_time_ps = chunk.split(":")
                    arrival_time_ns = int(arrival_time_ps) / 1000  # Convert ps to ns
                    chunks.append((int(chunk_id), arrival_time_ns))

                connection = {
                    "SrcID": src_id,
                    "DestID": dest_id,
                    "Latency (ns)": latency_ns,
                    "Bandwidth (GB/s=B/ns)": bandwidth_gbps,
                    "Chunks (ID:ns)": chunks,
                }
                data["Connections"].append(connection)

    # Convert Connections to a DataFrame for easier manipulation
    data["Connections"] = pd.DataFrame(data["Connections"])
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--filename", required=True, type=str, help="The filename to process"
    )
    args = parser.parse_args()
    results = process_collective_algo(args.filename)
    df = results["Connections"]

    df["Latency (ns)"] = df["Latency (ns)"].astype(float)
    df["Bandwidth (GB/s=B/ns)"] = df["Bandwidth (GB/s=B/ns)"].astype(float)

    # Calculate link crossing times (time to traverse each link)
    df["Link Time (ns)"] = df["Latency (ns)"] + (
        (results["Chunk_Size"]) / (1 << 30)
    ) * (1e9 / df["Bandwidth (GB/s=B/ns)"])

    # Create network graph
    G = nx.DiGraph()
    for _, row in df.iterrows():
        G.add_edge(
            row["SrcID"],
            row["DestID"],
            link_time=row["Link Time (ns)"],
            chunks=row["Chunks (ID:ns)"],
        )

    # Initialize plot
    pos = nx.spring_layout(G)
    fig, ax = plt.subplots(figsize=(8, 6))
    nx.draw(G, pos, with_labels=True, ax=ax, node_size=500, font_size=10)
    edge_labels = {
        (row["SrcID"], row["DestID"]): f"{row['Link Time (ns)']:.2f} ns"
        for _, row in df.iterrows()
    }
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, ax=ax)

    # Set up the slider
    max_ns = results["Collective_Time"] / 1000

    ax_slider = plt.axes([0.2, 0.1, 0.6, 0.03], facecolor="lightgrey")
    slider = Slider(ax_slider, "Time (ns)", 0, max_ns, valinit=0, valstep=max_ns / 100)

    # Set up the play/pause button
    ax_button = plt.axes([0.85, 0.05, 0.1, 0.04])
    play_button = Button(ax_button, "Play", color="lightgrey", hovercolor="0.8")

    # Animation setup
    chunk_positions = {edge: [] for edge in G.edges}

    # Calculate departure times based on arrival times and link crossing times
    for (src, dest), data in G.edges.items():
        for chunk_id, arrival_time_ns in data["chunks"]:
            link_time = G[src][dest]["link_time"]
            start_time_ns = arrival_time_ns - link_time  # Calculate the departure time
            chunk_positions[(src, dest)].append(
                (chunk_id, start_time_ns, arrival_time_ns)
            )

    is_playing = False
    current_frame = 0
    updating_slider = False

    def update(frame):
        nonlocal current_frame, updating_slider
        current_frame = frame  # Update current frame

        if not updating_slider:
            updating_slider = True  # Avoid recursive slider update
            slider.set_val(frame)  # Sync slider with animation frame
            updating_slider = False  # Reset flag after updating slider
        ax.clear()
        nx.draw(G, pos, with_labels=True, ax=ax, node_size=500, font_size=10)
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, ax=ax)

        frame_ns = frame
        arrived_chunks = {node: [] for node in G.nodes}
        for (src, dest), chunks in chunk_positions.items():
            for chunk_id, start_time_ns, arrival_time_ns in chunks:
                # Start moving the chunk only after its calculated departure time
                if start_time_ns <= frame_ns < arrival_time_ns:
                    move_pos = min(
                        1, (frame_ns - start_time_ns) / G[src][dest]["link_time"]
                    )
                    chunk_x = (1 - move_pos) * pos[src][0] + move_pos * pos[dest][0]
                    chunk_y = (1 - move_pos) * pos[src][1] + move_pos * pos[dest][1]

                    # Plot the moving chunk with label
                    ax.plot(chunk_x, chunk_y, "o", color="red", markersize=5)
                    ax.text(
                        chunk_x,
                        chunk_y + 0.03,
                        str(chunk_id),
                        color="black",
                        ha="center",
                        fontsize=8,
                    )
                elif (
                    frame_ns >= arrival_time_ns and chunk_id not in arrived_chunks[dest]
                ):
                    # If the chunk has arrived at the destination, add it to arrived_chunks
                    arrived_chunks[dest].append(chunk_id)

        # Display arrived chunks next to each destination node
        for dest in arrived_chunks:
            ax.text(
                pos[dest][0],
                pos[dest][1] - 0.05,
                f"{arrived_chunks[dest]}",
                color="red",
                fontsize=8,
                ha="center",
                verticalalignment="top",
            )

        ax.set_title(f"Network Animation - {frame_ns:.4f} ns")
        ax.axis("off")

        # Stop animation if the collective time has been reached
        if frame_ns >= results["Collective_Time"] / 1000:
            ani.event_source.stop()

    # Handle slider changes to update frame
    def on_slider_change(val):
        nonlocal current_frame, is_playing
        if not updating_slider:  # Prevent recursion
            current_frame = slider.val
            if not is_playing:
                update(current_frame)

    slider.on_changed(on_slider_change)

    # Play/pause button click handling
    def on_button_click(event):
        nonlocal is_playing
        if is_playing:
            ani.event_source.stop()
            play_button.label.set_text("Play")
        else:
            ani.frame_seq = ani.new_frame_seq()
            ani.event_source.start()
            play_button.label.set_text("Pause")
        is_playing = not is_playing

    play_button.on_clicked(on_button_click)

    # Initialize animation
    ani = animation.FuncAnimation(
        fig, update, frames=np.linspace(0, max_ns, num=100), interval=50, repeat=False
    )
    plt.show()


if __name__ == "__main__":
    main()
