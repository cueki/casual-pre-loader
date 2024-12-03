import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import hsv_to_rgb

def create_hsv_visualization(s_range=(75, 100), v=100, width=1000, height=100):
    h = np.linspace(0, 1, width)  # Hue from 0 to 1
    s = np.linspace(s_range[0] / 100, s_range[1] / 100, height)  # Saturation range

    H, S = np.meshgrid(h, s)
    V = np.full_like(H, v / 100)  # Value is constant (1)

    hsv = np.dstack((H, S, V))

    rgb = hsv_to_rgb(hsv)

    plt.figure(figsize=(12, 4))
    plt.imshow(rgb, extent=(0, 360, s_range[0], s_range[1]))

    # Add colorbar
    plt.colorbar(label='Hue', orientation='horizontal', ticks=np.linspace(0, 360, 7))

    # Add grid
    plt.grid(True, alpha=0.3)

    return plt


# Create and display the visualization
plt = create_hsv_visualization(s_range=(50, 100), v=100)
plt.tight_layout()
plt.show()

# Optional: Save the plot
# plt.savefig('hsv_visualization.png', dpi=300, bbox_inches='tight')
# plt.close()