import numpy as np
import matplotlib.pyplot as plt
import colorsys

from matplotlib.patches import Circle


def rgb_to_hsv(r, g, b):
    """Convert RGB [0-255] to HSV [0-360, 0-100, 0-100]"""
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 360, s * 100, v * 100


def hsv_to_rgb(h, s, v):
    """Convert HSV [0-360, 0-100, 0-100] to RGB [0-1]"""
    h, s, v = h / 360, s / 100, v / 100
    return colorsys.hsv_to_rgb(h, s, v)

def plot_rgb_colors(rgb_colors, labels=None):
    """Plot specific RGB colors in polar coordinates"""
    plt.figure(figsize=(12, 12))
    ax = plt.subplot(111, projection='polar')

    points = []
    colors = []

    for rgb in rgb_colors:
        # Convert RGB to HSV
        h, s, v = rgb_to_hsv(*rgb)

        # Convert to polar coordinates
        theta = np.radians(h)
        radius = s / 100.0

        points.append([theta, radius])
        colors.append([x / 255 for x in rgb])

    points = np.array(points)

    # Create scatter plot
    ax.scatter(points[:, 0], points[:, 1], c=colors, s=200, zorder=5)

    # If labels provided, add them
    if labels:
        for i, (point, label) in enumerate(zip(points, labels)):
            ax.annotate(label,
                        (point[0], point[1]),
                        xytext=(10, 10),
                        textcoords='offset points')

    # Customize the plot
    ax.set_title('Specific Colors in HSV Polar Coordinates', pad=20)
    ax.set_rticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_rlabel_position(0)
    ax.set_rlim(0, 1.1)

    # Add angle labels
    ax.set_xticks(np.linspace(0, 2 * np.pi, 12))
    angle_labels = ['0°\n(Red)', '30°', '60°', '90°', '120°', '150°',
                    '180°', '210°', '240°', '270°', '300°', '330°']
    ax.set_xticklabels(angle_labels)

    ax.grid(True)
    plt.tight_layout()
    plt.show()


def plot_specific_colors(rgb_colors, labels=None):
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
                  color=rgb_normalized, width=0.002, headwidth=0, alpha=.4,
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