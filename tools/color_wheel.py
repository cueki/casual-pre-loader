import time
from typing import Dict, List

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, FFMpegWriter
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle
from operations.color import rgb_to_hsv, color_shift, RGB

plt.rcParams['animation.ffmpeg_path'] = "tools\\ffmpeg.exe"

def ease_inout(t):
    if t < 0.5:
        return 2 * t * t
    else:
        t = 2 * t - 1
        return -0.5 * (t * (t - 2) - 1)


def plot_rgb_vector(rgb_colors, labels=None):
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 12))
    ax.axis('off')

    # Set equal aspect ratio and center the plot
    ax.set_aspect('equal')
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.2)

    for s in [0.2, 0.4, 0.6, 0.8, 1.0]:
        circle = Circle((0, 0), s, fill=True, color='black', alpha=1)
        ax.add_patch(circle)

    # Plot each color as a vector
    for i, rgb in enumerate(rgb_colors):
        # Convert RGB to HSV
        h, s, v = rgb_to_hsv(*rgb)

        # Convert to radians and calculate vector components
        theta = np.radians(h)
        r = s / 100.0  # Normalize saturation to [0,1]
        x = r * np.cos(theta)
        y = r * np.sin(theta)

        # Create vector
        rgb_normalized = [c / 255 for c in rgb]
        ax.quiver(0, 0, x, y, angles='xy', scale_units='xy', scale=1,
                  color=rgb_normalized, width=0.003, headwidth=0, alpha=.3,
                  headlength=0, headaxislength=0)

        # Add label if provided
        if labels and i < len(labels):
            # Position label slightly beyond vector tip
            label_x = x * 1.1
            label_y = y * 1.1
            ax.text(label_x, label_y, labels[i], ha='center', va='center')

    # Add axes and grid
    plt.grid(False)

    # ax.set_title('Color Vectors in HSV Space', pad=20)
    plt.tight_layout()
    plt.show()


def animate_color_shift(colors: Dict[str, Dict[str, List[RGB]]],
                        targets: Dict[str, Dict[str, RGB]],
                        frames=120, interval=10,
                        show_metrics=False, save_video=False):
    plt.style.use('dark_background')

    if show_metrics:
        fig, (ax, ax_perf) = plt.subplots(2, 1, figsize=(12, 14),
                                          gridspec_kw={'height_ratios': [4, 1]})
        frame_times = []
        line_perf, = ax_perf.plot([], [], 'g-', label='Frame Time (ms)')
        ax_perf.set_xlim(0, frames)
        ax_perf.set_ylim(0, 50)
        ax_perf.set_xlabel('Frame')
        ax_perf.set_ylabel('Time (ms)')
        ax_perf.grid(True, alpha=0.3)
        ax_perf.legend()
    else:
        fig, ax = plt.subplots(figsize=(12, 12))
        frame_times = None
        line_perf = None

    ax.axis('off')
    ax.set_aspect('equal')
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.2)

    # Calculate shifts for all categories and teams
    shifted_colors = {}
    for team in ['red', 'blue', 'neutral']:
        shifted_colors[team] = {}
        for category in ['color1', 'color2', 'tint_clamp', 'color_fade']:
            if colors[team][category] and targets[team][category]:
                shifted_colors[team][category] = color_shift(colors[team][category],
                                                             targets[team][category])
            else:
                shifted_colors[team][category] = []

    # Pre-compute and create background
    for s in np.linspace(0.2, 1.0, 5):
        circle = Circle((0, 0), s, fill=True, color='black', alpha=1, linewidth=0)
        ax.add_patch(circle)

    # Calculate total number of lines needed
    total_lines = sum(len(colors[team][cat])
                      for team in colors
                      for cat in colors[team])

    segments = np.zeros((total_lines, 2, 2))
    colors_array = np.zeros((total_lines, 4))

    line_collection = LineCollection(segments, colors=colors_array,
                                     linewidth=3,
                                     alpha=0.8,
                                     capstyle='round')
    ax.add_collection(line_collection)

    # Pre-compute color data
    color_data = []

    for team in ['red', 'blue', 'neutral']:
        for category in ['color1', 'color2', 'tint_clamp', 'color_fade']:
            if not colors[team][category] or not targets[team][category]:
                continue

            for rgb in colors[team][category]:
                h1, s1, v1 = rgb_to_hsv(*rgb)
                shifted = shifted_colors[team][category][colors[team][category].index(rgb)]
                target_h, target_s, target_v = rgb_to_hsv(*shifted)

                dh = target_h - h1
                if abs(dh) > 180:
                    dh = dh - 360 if dh > 0 else dh + 360

                color_data.append({
                    'start_hsv': np.array([h1, s1, v1]),
                    'target_hsv': np.array([target_h, target_s, target_v]),
                    'dh': dh,
                    'start_rgb': np.array(rgb),
                    'target_rgb': np.array(shifted)
                })

    # Add target indicators
    target_segments = []
    target_colors = []
    for team in targets:
        for category in targets[team]:
            if targets[team][category]:
                h, s, v = rgb_to_hsv(*targets[team][category])
                theta = np.radians(h)
                r = s / 100.0
                target_segments.append([[0, 0], [r * np.cos(theta), r * np.sin(theta)]])
                target_colors.append(np.array([*[x / 255 for x in targets[team][category]], 0.5]))

    if target_segments:
        target_collection = LineCollection(target_segments,
                                           colors=target_colors,
                                           linewidth=1.5,
                                           linestyle='--',
                                           alpha=0.5)
        ax.add_collection(target_collection)

    # Pre-allocate arrays for the update function
    new_segments = np.zeros((total_lines, 2, 2))
    new_colors = np.zeros((total_lines, 4))

    def update(frame):
        if show_metrics:
            start_time = time.time()

        t = ease_inout(frame / (frames - 1))

        for i, data in enumerate(color_data):
            current_h = data['start_hsv'][0] + t * data['dh']
            current_s = data['start_hsv'][1] + t * (data['target_hsv'][1] - data['start_hsv'][1])

            theta = np.radians(current_h)
            r = current_s / 100.0
            x = r * np.cos(theta)
            y = r * np.sin(theta)

            new_segments[i] = [[0, 0], [x, y]]
            current_rgb = data['start_rgb'] + t * (data['target_rgb'] - data['start_rgb'])
            new_colors[i] = np.append(current_rgb / 255, 0.5)

        line_collection.set_segments(new_segments)
        line_collection.set_color(new_colors)

        if show_metrics:
            frame_time = (time.time() - start_time) * 1000
            frame_times.append(frame_time)
            line_perf.set_data(range(len(frame_times)), frame_times)
            return line_collection, line_perf

        return line_collection,

    anim = FuncAnimation(fig, update, frames=frames, interval=interval,
                         blit=True, repeat=False)

    if save_video:
        writer = FFMpegWriter(fps=60, bitrate=10000)
        anim.save('color_shift.mp4', writer=writer)

    plt.show()

    if show_metrics and frame_times:
        print(f"Performance Statistics:")
        print(f"Average frame time: {np.mean(frame_times):.2f}ms")
        print(f"Max frame time: {np.max(frame_times):.2f}ms")
        print(f"Min frame time: {np.min(frame_times):.2f}ms")
        print(f"95th percentile: {np.percentile(frame_times, 95):.2f}ms")

    return anim