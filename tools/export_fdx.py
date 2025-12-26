"""
Final Draft Exporter
Converts markdown scripts into Final Draft 12 Compatible XML (.fdx).
"""
import os
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime

class FDXBuilder:
    def __init__(self):
        self.root = ET.Element("FinalDraft", {"DocumentType": "Script", "Template": "Screenplay", "Version": "4"})
        self.content = ET.SubElement(self.root, "Content")
        self.paragraph_count = 0
        
    def add_paragraph(self, type_name, text):
        self.paragraph_count += 1
        p = ET.SubElement(self.content, "Paragraph", {"Number": str(self.paragraph_count), "Type": type_name})
        
        # Clean text
        text = text.replace('**', '').replace('*', '').strip()
        
        # Text object
        t = ET.SubElement(p, "Text")
        t.text = text
        
    def build(self):
        # Return pretty printed XML
        rough_string = ET.tostring(self.root, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

def export_to_fdx(project_path):
    if not os.path.exists(project_path):
        print(f"Error: Project path {project_path} does not exist.")
        return

    script_path = os.path.join(project_path, "script.md")
    if not os.path.exists(script_path):
        print(f"Error: script.md not found in {project_path}")
        return

    # Use a similar parsing logic to the PDF publisher
    with open(script_path, 'r', encoding='utf-8') as f:
        raw_script = f.read()

    # Reuse parser logic (simplified version here to remain standalone)
    lines = raw_script.split('\n')
    
    builder = FDXBuilder()
    last_type = "Action"
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        clean_line = line.replace('**', '').replace('*', '').strip()
        
        # Detect Type
        fdx_type = "Action"
        
        # SCENE
        if (clean_line.startswith('INT.') or clean_line.startswith('EXT.') or 
            clean_line.startswith('INT/') or clean_line.startswith('EXT/')):
            fdx_type = "Scene Heading"
            clean_line = clean_line.upper()
            
        # TRANSITION
        elif clean_line.endswith('TO:') or clean_line.upper() in ['FADE IN:', 'FADE OUT.']:
            fdx_type = "Transition"
            clean_line = clean_line.upper()
            
        # CHARACTER
        elif (clean_line.isupper() and len(clean_line) < 50 and 
              last_type not in ["Dialogue", "Parenthetical"]):
            fdx_type = "Character"
            
        # PARENTHETICAL
        elif clean_line.startswith('(') and clean_line.endswith(')'):
            fdx_type = "Parenthetical"
            
        # DIALOGUE
        elif last_type in ["Character", "Parenthetical"]:
            fdx_type = "Dialogue"
            
        # Add to XML
        builder.add_paragraph(fdx_type, clean_line)
        last_type = fdx_type

    # Output file
    project_name = os.path.basename(project_path)
    output_file = os.path.join(project_path, f"{project_name}.fdx")
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(builder.build())
        
    print(f"Successfully exported Final Draft XML: {output_file}")
    return output_file
