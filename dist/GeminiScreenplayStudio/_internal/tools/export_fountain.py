"""
Fountain Exporter
Converts markdown scripts into Fountain format (.fountain).
"""
import os
import argparse

def export_to_fountain(project_path):
    if not os.path.exists(project_path):
        print(f"Error: Project path {project_path} does not exist.")
        return

    script_path = os.path.join(project_path, "script.md")
    if not os.path.exists(script_path):
        print(f"Error: script.md not found in {project_path}")
        return

    # Read markdown script
    with open(script_path, 'r', encoding='utf-8') as f:
        raw_script = f.read()

    lines = raw_script.split('\n')
    fountain_lines = []
    
    # Process lines
    for line in lines:
        line = line.strip()
        
        # Keep empty lines for spacing
        if not line:
            fountain_lines.append("")
            continue
            
        # Clean markdown formatting (standard Fountain doesn't use ** for bold scenes keywods)
        clean_line = line.replace('**', '').replace('*', '').strip()
        
        # Add to output
        fountain_lines.append(clean_line)

    # Output file
    project_name = os.path.basename(project_path)
    output_file = os.path.join(project_path, f"{project_name}.fountain")
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(fountain_lines))
        
    print(f"Successfully exported Fountain file: {output_file}")
    return output_file

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gemini Fountain Exporter - Convert markdown scripts to .fountain",
        epilog="Example: python tools/export_fountain.py output/project_name"
    )
    
    parser.add_argument(
        'project_folder',
        help='Path to the project folder containing script.md'
    )
    
    args = parser.parse_args()
    
    export_to_fountain(args.project_folder)
