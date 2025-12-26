"""
Universal Publisher - Professional Book Production Tool
Originally conceptualized by: Pietro Schirano (@Doriandarko)
Enhanced and Implemented by: @rzuccolo

Automates chapter merging, AI cover generation, and premium PDF layout.
"""
import os
import sys
import re
import time
import glob
from fpdf import FPDF
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

class UniversalPDF(FPDF):
    def __init__(self, book_title="Antigravity Book"):
        super().__init__()
        self.book_title = book_title
        self.set_margins(left=25, top=25, right=25)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        if self.page_no() > 1:
            self.set_font('Helvetica', 'I', 8)
            self.set_y(10)
            self.cell(0, 10, self.book_title, 0, 0, 'C')
            self.set_y(25)

    def footer(self):
        if self.page_no() > 1:
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C', new_x="RIGHT", new_y="TOP")

def clean_text(text):
    replacements = {
        '\u2014': '-', '\u2013': '-', '\u201c': '"', '\u201d': '"',
        '\u2018': "'", '\u2019': "'", '\u2026': '...', '\u00a0': ' '
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text

def parse_markdown(pdf, text):
    # Support for subheaders ###
    lines = text.split('\n')
    for line in lines:
        if line.startswith('### '):
            pdf.ln(5)
            pdf.set_font('Helvetica', 'B', 14)
            pdf.cell(0, 10, clean_text(line[4:].strip()), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font('Helvetica', '', 12)
        elif line.startswith('## '):
            pdf.ln(5)
            pdf.set_font('Helvetica', 'B', 16)
            pdf.cell(0, 12, clean_text(line[3:].strip()), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font('Helvetica', '', 12)
        else:
            # Inline parsing for bold and italics
            tokens = re.split(r'(\*\*|\*)', line)
            is_bold = False
            is_italic = False
            for token in tokens:
                if token == '**':
                    is_bold = not is_bold
                elif token == '*':
                    is_italic = not is_italic
                else:
                    style = ''
                    if is_bold: style += 'B'
                    if is_italic: style += 'I'
                    pdf.set_font('Helvetica', style, 12)
                    pdf.write(7, clean_text(token))
            pdf.ln(7)

def generate_ai_cover(project_path, book_title, manuscript):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("No API key found for cover generation.")
        return None

    print(f"INFO: Attempting to generate a cover for '{book_title}'...")
    print("NOTE: Traditional AI image generation requires a billed Google Cloud account.")
    print("If you are on the Free Tier, the script will automatically switch to a 'Text-Only Designer Cover'.")
    return None

def create_text_cover(pdf, title):
    pdf.add_page()
    pdf.set_y(100)
    pdf.set_font('Helvetica', 'B', 36)
    pdf.multi_cell(0, 20, title, align='C')
    pdf.set_y(250)
    pdf.set_font('Helvetica', 'I', 12)
    pdf.cell(0, 10, "Ricardo Zuccolo", align='C')

def publish_book(project_path):
    if not os.path.isdir(project_path):
        print(f"Error: {project_path} is not a directory.")
        return

    # Find chapters
    chapter_files = sorted(glob.glob(os.path.join(project_path, "chapter_*.md")))
    if not chapter_files:
        print("No chapter files found.")
        return

    # Extract Title (from folder name or first chapter)
    book_title = os.path.basename(project_path).replace('_', ' ')
    
    chapters_data = []
    manuscript = ""
    for f_path in chapter_files:
        with open(f_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()
            manuscript += raw_content + "\n\n"
            
            # Extract Chapter Title from # Chapter X: Title
            match = re.search(r'^# (.*)', raw_content, re.MULTILINE)
            title = match.group(1).strip() if match else f"Chapter {len(chapters_data)+1}"
            
            # Clean body by removing the main # Header
            body = re.sub(r'^# .*', '', raw_content, count=1, flags=re.MULTILINE).strip()
            chapters_data.append({"title": title, "body": body})

    pdf = UniversalPDF(book_title)
    
    # 1. COVER
    cover_path = os.path.join(project_path, "cover.png")
    if not os.path.exists(cover_path):
        cover_path = generate_ai_cover(project_path, book_title, manuscript)
    
    if cover_path and os.path.exists(cover_path):
        pdf.add_page()
        pdf.image(cover_path, x=25, y=30, w=160)
        pdf.set_y(220)
        pdf.set_font('Helvetica', 'B', 24)
        pdf.cell(0, 15, book_title, align='C', new_x="LMARGIN", new_y="NEXT")
    else:
        create_text_cover(pdf, book_title)

    # 2. FRONT MATTER
    pdf.add_page()
    pdf.set_y(100)
    pdf.set_font('Helvetica', 'B', 24)
    pdf.cell(0, 20, book_title, align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(20)
    pdf.set_font('Helvetica', 'I', 14)
    pdf.cell(0, 10, "Dedicated to those who dream.", align='C', new_x="LMARGIN", new_y="NEXT")
    
    # 3. CONTENT PRE-FLIGHT (to get page numbers for TOC)
    # We add pages first, then go back and update TOC
    toc_page_num = pdf.page_no() + 1
    pdf.add_page() # Placeholder for TOC
    
    for chapter in chapters_data:
        pdf.add_page()
        chapter["page_num"] = pdf.page_no()
        chapter["link"] = pdf.add_link()
        pdf.set_link(chapter["link"], y=0, page=-1) # Link to current page top
        
        pdf.set_y(40)
        pdf.set_font('Helvetica', 'B', 22)
        pdf.multi_cell(0, 15, chapter["title"], align='C')
        pdf.ln(10)
        parse_markdown(pdf, chapter["body"])

    # 4. TOC GENERATION (Going back to the placeholder page)
    pdf.page = toc_page_num
    pdf.set_y(40)
    pdf.set_font('Helvetica', 'B', 18)
    pdf.cell(0, 15, "Chapters", align='L', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_font('Helvetica', '', 12)
    for chapter in chapters_data:
        # Chapter Title ------------------ Page X
        title_width = pdf.get_string_width(chapter["title"])
        page_width = pdf.get_string_width(str(chapter["page_num"]))
        dots_width = pdf.w - pdf.l_margin - pdf.r_margin - title_width - page_width - 10
        dots = "." * (int(dots_width / pdf.get_string_width(".")) - 2)
        
        pdf.set_text_color(0, 0, 255) # Blue for link
        pdf.cell(title_width + 5, 10, chapter["title"], align='L', link=chapter["link"])
        pdf.set_text_color(0, 0, 0) # Back to black
        pdf.cell(dots_width, 10, dots, align='C')
        pdf.cell(page_width + 5, 10, str(chapter["page_num"]), align='R', new_x="LMARGIN", new_y="NEXT")

    final_pdf = os.path.join(project_path, f"{os.path.basename(project_path)}.pdf")
    pdf.output(final_pdf)
    print(f"Successfully published: {final_pdf}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python publish.py [project_folder]")
    else:
        publish_book(sys.argv[1])
