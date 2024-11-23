import numpy as np
import matplotlib.pyplot as plt
import colorsys


def rgb_to_hsv(r, g, b):
    """Convert RGB [0-255] to HSV [0-360, 0-100, 0-100]"""
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 360, s * 100, v * 100


def hsv_to_rgb(h, s, v):
    """Convert HSV [0-360, 0-100, 0-100] to RGB [0-1]"""
    h, s, v = h / 360, s / 100, v / 100
    return colorsys.hsv_to_rgb(h, s, v)


def create_color_wheel(resolution=30):
    """Create points and colors for the color wheel"""
    # Create a grid of hue and saturation values
    hue_steps = np.linspace(0, 360, resolution)
    sat_steps = np.linspace(0, 100, resolution // 2)

    points = []
    colors = []

    for h in hue_steps:
        for s in sat_steps:
            # Convert HSV to polar coordinates
            theta = np.radians(h)
            radius = s / 100.0

            # Convert polar to cartesian coordinates
            x = radius * np.cos(theta)
            y = radius * np.sin(theta)

            # Add point
            points.append([x, y])

            # Convert HSV to RGB for coloring
            rgb = hsv_to_rgb(h, s, 100)  # Full value for maximum brightness
            colors.append(rgb)

    return np.array(points), np.array(colors)


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
