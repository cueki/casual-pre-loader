import os

def on_post_build(config, **kwargs):
    """Create .nojekyll file to disable Jekyll processing on GitHub Pages"""
    site_dir = config['site_dir']
    nojekyll_path = os.path.join(site_dir, '.nojekyll')

    # Create empty .nojekyll file
    with open(nojekyll_path, 'w') as f:
        pass

    print(f"Created .nojekyll file at {nojekyll_path}")
