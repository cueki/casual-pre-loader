import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from operations.color import rgb_to_hsv


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