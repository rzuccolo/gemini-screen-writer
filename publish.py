"""
Screenplay Publisher - PDF Generator
Converts markdown scripts into industry-standard PDF format.

Standards:
- Font: Courier 12pt
- Page Size: Letter (8.5 x 11)
- Margins: Left 1.5", Right 1.0", Top 1.0", Bottom 1.0"
"""
import os
import sys
import re
from fpdf import FPDF

# Constants for Screenplay Formatting (in mm)
# 1 inch = 25.4 mm
MARGIN_LEFT = 38.1     # 1.5 inches
MARGIN_RIGHT = 25.4    # 1.0 inches
MARGIN_TOP = 25.4      # 1.0 inches
MARGIN_BOTTOM = 25.4   # 1.0 inches

# Indentations (relative to Left Margin)
INDENT_ACTION = 0
INDENT_DIALOGUE = 25.4      # ~1.0 inch from margin (Total 2.5" from page edge)
INDENT_CHARACTER = 50.8     # ~2.0 inches from margin (Total 3.5" from page edge)
INDENT_PARENTHETICAL = 38.1 # ~1.5 inches from margin
INDENT_TRANSITION = 101.6   # ~4.0 inches from margin

# Widths
WIDTH_DIALOGUE = 88.9       # ~3.5 inches wide
WIDTH_ACTION = 0            # 0 means full width (up to right margin)

def clean_text(text):
    """Replaces Unicode characters with ASCII equivalents."""
    replacements = {
        '\u2018': "'", '\u2019': "'", # Smart Quotes
        '\u201c': '"', '\u201d': '"', # Smart Double Quotes
        '\u2026': '...',              # Ellipsis
        '\u2013': '-', '\u2014': '-'  # Dashes
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text

class ScreenplayPDF(FPDF):
    def __init__(self, title="Screenplay"):
        # Format: Letter, Unit: mm
        super().__init__(format='Letter', unit='mm')
        self.set_margins(MARGIN_LEFT, MARGIN_TOP, MARGIN_RIGHT)
        self.set_auto_page_break(auto=True, margin=MARGIN_BOTTOM)
        self.title_val = title
        
        # Add Courier font (standard)
        self.set_font('Courier', '', 12)

    def header(self):
        # Page numbers hidden on page 1
        if self.page_no() > 1:
            self.set_font('Courier', '', 12)
            self.set_y(12)  # 0.5 inches from top
            # Page number at top right
            self.cell(0, 10, f'{self.page_no()}.', new_x="RIGHT", new_y="TOP", align='R')
            self.ln(15) # Space after header

class ScriptParser:
    """Parses Markdown script into typed elements."""
    
    ELEMENT_SCENE = 'scene'
    ELEMENT_ACTION = 'action'
    ELEMENT_CHARACTER = 'character'
    ELEMENT_DIALOGUE = 'dialogue'
    ELEMENT_PARENTHETICAL = 'parenthetical'
    ELEMENT_TRANSITION = 'transition'
    ELEMENT_NOTE = 'note'
    
    @staticmethod
    def parse(text):
        lines = text.split('\n')
        elements = []
        last_element = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Clean markdown bold/italics for processing checks
            clean_line = line.replace('**', '').replace('*', '').strip()
            
            # 1. SCENE HEADING (INT./EXT.)
            # Usually BOLD in our markdown: **INT. LOCATION - DAY**
            if (clean_line.startswith('INT.') or 
                clean_line.startswith('EXT.') or 
                clean_line.startswith('INT/') or 
                clean_line.startswith('EXT/')):
                elements.append({'type': ScriptParser.ELEMENT_SCENE, 'content': clean_line.upper()})
                last_element = ScriptParser.ELEMENT_SCENE
                
            # 2. TRANSITION (CUT TO:)
            elif clean_line.endswith('TO:') or clean_line.upper() == 'FADE OUT.' or clean_line.upper() == 'FADE IN:':
                elements.append({'type': ScriptParser.ELEMENT_TRANSITION, 'content': clean_line.upper()})
                last_element = ScriptParser.ELEMENT_TRANSITION
            
            # 3. CHARACTER (ALL CAPS, usually centered logic, but here we detect strictly)
            # In our markdown, characters are often **CHARACTER**
            # If the previous element was Scene or Action, and this is short and CAPS...
            elif (clean_line.isupper() and len(clean_line) < 50 and 
                  last_element not in [ScriptParser.ELEMENT_DIALOGUE, ScriptParser.ELEMENT_PARENTHETICAL]):
                elements.append({'type': ScriptParser.ELEMENT_CHARACTER, 'content': clean_line})
                last_element = ScriptParser.ELEMENT_CHARACTER
            
            # 3b. PARENTHETICAL (starts with ()
            elif clean_line.startswith('(') and clean_line.endswith(')'):
                elements.append({'type': ScriptParser.ELEMENT_PARENTHETICAL, 'content': clean_line})
                last_element = ScriptParser.ELEMENT_PARENTHETICAL
                
            # 4. DIALOGUE
            # If previous was Character or Parenthetical, this is Dialogue
            elif last_element in [ScriptParser.ELEMENT_CHARACTER, ScriptParser.ELEMENT_PARENTHETICAL]:
                elements.append({'type': ScriptParser.ELEMENT_DIALOGUE, 'content': clean_line})
                last_element = ScriptParser.ELEMENT_DIALOGUE
                
            # 5. ACTION (Default)
            else:
                elements.append({'type': ScriptParser.ELEMENT_ACTION, 'content': clean_line})
                last_element = ScriptParser.ELEMENT_ACTION
                
        return elements

def publish_screenplay(project_path):
    if not os.path.isdir(project_path):
        print(f"Error: {project_path} is not a directory.")
        return

    # Look for script.md
    script_path = os.path.join(project_path, "script.md")
    if not os.path.exists(script_path):
        print("Error: script.md not found in project folder.")
        return
        
    # Look for cover data
    cover_path = os.path.join(project_path, "cover.md")
    title = "Untitled Screenplay"
    author = "Gemini Screenwriter"
    
    if os.path.exists(cover_path):
        with open(cover_path, 'r') as f:
            content = f.read()
            # Extract title if possible
            match = re.search(r'# (.*)', content)
            if match:
                title = match.group(1).strip()
    
    with open(script_path, 'r', encoding='utf-8') as f:
        raw_script = f.read()
        
    elements = ScriptParser.parse(raw_script)
    
    pdf = ScreenplayPDF(title)
    pdf.add_page()
    
    # Title Page
    pdf.set_y(80)
    pdf.set_font('Courier', 'B', 24)
    pdf.cell(0, 10, clean_text(title.upper()), new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(10)
    pdf.set_font('Courier', '', 12)
    pdf.cell(0, 10, "Written by", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.cell(0, 10, clean_text(author), new_x="LMARGIN", new_y="NEXT", align='C')
    
    pdf.add_page() # Begin Script
    
    for el in elements:
        typ = el['type']
        text = clean_text(el['content']) # Clean text before processing
        
        # Clean formatting for PDF (remove markdown bold chars)
        text = text.replace('**', '').replace('*', '')
        
        if typ == ScriptParser.ELEMENT_SCENE:
            pdf.ln(4) # Double space before scene
            pdf.set_font('Courier', 'B', 12)
            pdf.set_x(MARGIN_LEFT + INDENT_ACTION)
            pdf.multi_cell(0, 5, text.upper())
            pdf.set_font('Courier', '', 12)
            
        elif typ == ScriptParser.ELEMENT_ACTION:
            pdf.ln(4)
            pdf.set_x(MARGIN_LEFT + INDENT_ACTION)
            pdf.multi_cell(0, 5, text)
            
        elif typ == ScriptParser.ELEMENT_CHARACTER:
            pdf.ln(4) # Space before character speaks
            pdf.set_x(MARGIN_LEFT + INDENT_CHARACTER)
            # Character names upper case
            pdf.cell(0, 5, text.upper(), new_x="LMARGIN", new_y="NEXT")
            
        elif typ == ScriptParser.ELEMENT_PARENTHETICAL:
            pdf.set_x(MARGIN_LEFT + INDENT_PARENTHETICAL)
            pdf.multi_cell(WIDTH_DIALOGUE, 5, text)
            
        elif typ == ScriptParser.ELEMENT_DIALOGUE:
            pdf.set_x(MARGIN_LEFT + INDENT_DIALOGUE)
            pdf.multi_cell(WIDTH_DIALOGUE, 5, text)
            
        elif typ == ScriptParser.ELEMENT_TRANSITION:
            pdf.ln(4)
            pdf.set_x(MARGIN_LEFT + INDENT_TRANSITION)
            pdf.cell(0, 5, text.upper(), new_x="LMARGIN", new_y="NEXT")
            
    # Output
    output_filename = os.path.join(project_path, f"{os.path.basename(project_path)}_script.pdf")
    pdf.output(output_filename)
    print(f"Successfully published Screenplay PDF: {output_filename}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python publish.py [project_folder]")
    else:
        publish_screenplay(sys.argv[1])
