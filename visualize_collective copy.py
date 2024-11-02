import csv
import argparse
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.animation as animation

def process_collective_algo(filename):
    data = {
        "NPU_Count": None,
        "Links_Count": None,
        "Chunks_Count": None,
        "Chunk_Size": None,
        "Collective_Time": None,
        "Connections": []
    }

    with open(filename, mode='r') as file:
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
                    chunk_id, start_time_ps = chunk.split(':')
                    start_time_ns = int(start_time_ps) / 1000  # Convert ps to ns
                    chunks.append((int(chunk_id), start_time_ns))

                connection = {
                    "SrcID": src_id,
                    "DestID": dest_id,
                    "Latency (ns)": latency_ns,
                    "Bandwidth (GB/s=B/ns)": bandwidth_gbps,
                    "Chunks (ID:ns)": chunks
                }
                data["Connections"].append(connection)

    # Convert Connections to a DataFrame for easier manipulation
    data["Connections"] = pd.DataFrame(data["Connections"])
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--filename', required=True, type=str, help='The filename to process')
    args = parser.parse_args()
    results = process_collective_algo(args.filename)
    print(results["Connections"])
    df = results["Connections"]
    
    print(df.dtypes)
    # Calculate link crossing times
    print(results["Collective_Time"])

    df['Link Time (ns)'] = df['Latency (ns)'] + (results["Chunk_Size"] / df['Bandwidth (GB/s=B/ns)'] )
    print(df["Link Time (ns)"])
    # Create network graph
    G = nx.DiGraph()
    for _, row in df.iterrows():
        G.add_edge(row['SrcID'], row['DestID'], link_time=row['Link Time (ns)'], chunks=row['Chunks (ID:ns)'])

    # Initialize plot
    pos = nx.spring_layout(G)
    fig, ax = plt.subplots(figsize=(8, 6))
    nx.draw(G, pos, with_labels=True, ax=ax, node_size=500, font_size=10)
    edge_labels = {(row['SrcID'], row['DestID']): f"{row['Link Time (ns)']:.2f} ns" for _, row in df.iterrows()}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, ax=ax)

    # Animation setup
    chunk_positions = {edge: [] for edge in G.edges}
    for (src, dest), data in G.edges.items():
        for chunk_id, start_time_ns in data['chunks']:
            chunk_positions[(src, dest)].append((chunk_id, 0, start_time_ns))  # (chunk_id, position along edge, start time in ns)

    def update(frame):
        ax.clear()
        nx.draw(G, pos, with_labels=True, ax=ax, node_size=500, font_size=10)
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, ax=ax)

        frame = frame * 1000
        for (src, dest), chunks in chunk_positions.items():
            for chunk_id, start_pos, start_time_ns in chunks:
                # Start moving the chunk only after its designated start time
                if frame >= start_time_ns:
                    move_pos = min(1, (frame - start_time_ns) / G[src][dest]['link_time'])
                    chunk_x = (1 - move_pos) * pos[src][0] + move_pos * pos[dest][0]
                    chunk_y = (1 - move_pos) * pos[src][1] + move_pos * pos[dest][1]
                    
                    # Plot the moving chunk with label
                    ax.plot(chunk_x, chunk_y, 'o', color="red", markersize=5)
                    ax.text(chunk_x, chunk_y + 0.03, str(chunk_id), color="black", ha='center', fontsize=8)

        ax.set_title(f"Network Animation - {frame} ns")
        ax.axis("off")

        if frame>=results["Collective_Time"]/1000:
            ani.event_source.stop()

    # Set up a faster animation by reducing interval and frame count
    ani = animation.FuncAnimation(
        fig, update, frames=range(0, int(df['Link Time (ns)'].max()) + 50), interval=50
    )
    plt.show()


if __name__ == "__main__":
    main()