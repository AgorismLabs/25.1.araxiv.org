import os
import shutil
import subprocess
import yaml
from jinja2 import Environment, FileSystemLoader

# --- Configuration ---
CONFIG_FILE = 'release-config.yml'
SUBMISSIONS_DIR = 'submissions'
TEMPLATES_DIR = 'templates'
OUTPUT_DIR = 'output'
ASSETS_DIR = 'assets'

def run_pdflatex(tex_file_path, output_dir):
    """Runs pdflatex command twice on a given .tex file."""
    try:
        subprocess.run(
            [
                'latexmk',
                '-pdf',
                #'-interaction=nonstopmode',
                f'-output-directory={output_dir}',
                tex_file_path
            ],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error compiling {tex_file_path}.")
        print(e.stdout)
        print(e.stderr)
        raise

def main():
    """Main script to build the entire release."""
    print("--- Starting ARA Release Build Process ---")

    # 1. Load Configuration
    with open(CONFIG_FILE, 'r') as f:
        config = yaml.safe_load(f)

    # 2. Setup Output Directory
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    # 3. Load all content and metadata
    release_content = []
    print("Loading content and metadata...")
    for item_id in config['content_ids']:
        item_dir = os.path.join(SUBMISSIONS_DIR, str(item_id))
        
        # Find metadata and content files
        metadata_file = next((f for f in os.listdir(item_dir) if f.endswith('.yml')), None)
        tex_file = next((f for f in os.listdir(item_dir) if f.endswith('.tex')), None)

        if not metadata_file or not tex_file:
            print(f"Warning: Missing files in submission directory '{item_id}'. Skipping.")
            continue

        with open(os.path.join(item_dir, metadata_file), 'r') as f:
            metadata = yaml.safe_load(f)
            metadata['id'] = item_id # Ensure ID is part of the metadata
            metadata['pdf_link'] = f"{metadata['permalink']}.pdf"
        
        content_data = {
            'metadata': metadata,
            'tex_path': os.path.join(item_dir, tex_file)
        }
        release_content.append(content_data)
        print(f"  - Loaded '{metadata['title']}'")

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

    # 4. Build Individual PDFs
    print("\nBuilding individual PDFs...")
    for item in release_content:
        print(f"  - Compiling {item['metadata']['permalink']}.pdf...")
        # We need to change to the submission directory to resolve local paths if any
        run_pdflatex(item['tex_path'], OUTPUT_DIR)
        # Rename the output to the issue ID
        base_name = os.path.splitext(os.path.basename(item['tex_path']))[0]
        shutil.move(
            os.path.join(OUTPUT_DIR, f"{base_name}.pdf"),
            os.path.join(OUTPUT_DIR, f"{item['metadata']['permalink']}.pdf"), # perhaps add volume prefix?
        )
        print("\nBuilding metadata page...")
        web_template = env.get_template('paper.html.j2')
        web_html_content = web_template.render(
            release=config,
            content_list=release_content,
            item=item,
        )
        with open(os.path.join(OUTPUT_DIR, f"{item['metadata']['permalink']}.html"), 'w') as f:
            f.write(web_html_content)

    # 5. Build Master PDF Volume
    # Not honestly sure about this. Probably skip for now.
    print("\nBuilding master release volume PDF...")
    '''
    master_template = env.get_template('master_release.tex.j2')
    master_tex_content = master_template.render(
        release=config,
        content_list=release_content
    )
    master_tex_path = os.path.join(OUTPUT_DIR, 'master_release.tex')
    with open(master_tex_path, 'w') as f:
        f.write(master_tex_content)
    
    run_pdflatex(master_tex_path, OUTPUT_DIR)
    shutil.move(
        os.path.join(OUTPUT_DIR, 'master_release.pdf'),
        os.path.join(OUTPUT_DIR, f"ARA-Volume-{config['release_volume']}.pdf")
    )
    print(f"  - Successfully created ARA-Volume-{config['release_volume']}.pdf")
    '''

    # 6. Build Website
    print("\nBuilding static website...")
    web_template = env.get_template('release.html.j2')
    web_html_content = web_template.render(
        release=config,
        content_list=release_content
    )
    with open(os.path.join(OUTPUT_DIR, 'index.html'), 'w') as f:
        f.write(web_html_content)
    
    # Copy assets
    if os.path.exists(ASSETS_DIR):
        shutil.copytree(ASSETS_DIR, os.path.join(OUTPUT_DIR, ASSETS_DIR))
    print("  - Website created successfully.")

    print("\n🎉 ARA Release Build Complete! Artifacts are in the 'output' directory.")

if __name__ == "__main__":
    main()
