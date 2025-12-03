import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
import io

# --- PAGE CONFIG ---
st.set_page_config(page_title="Mareero System", page_icon="🏢", layout="wide")

# --- CSS: HIDE WATERMARKS & STYLE BUTTONS ---
st.markdown("""
<style>
    /* Hide Streamlit Logos */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    div[data-testid="stStatusWidget"] {visibility: hidden;}
    
    /* Adjust top padding */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 5rem;
    }
    
    /* Make the Delete Icon Button Red and Round-ish */
    div[data-testid="stButton"] button {
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. SETUP DATABASE ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    SHEET_URL = st.secrets["gcp_sheet_url"] 
except Exception as e:
    st.error(f"⚠️ Error: Fadlan hubi internetkaaga ama Database-ka. ({e})")
    st.stop()

# --- 2. PROFESSIONAL REPORT ENGINES ---

def generate_excel(df):
    output = io.BytesIO()
    # Use OpenPyXL engine to allow formatting
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Warbixin')
        
        # --- FIX: Auto-Adjust Column Widths so Dates/Names show correctly ---
        worksheet = writer.sheets['Warbixin']
        for i, col in enumerate(df.columns):
            # Calculate the maximum length of data in the column
            max_len = max(
                df[col].astype(str).map(len).max(), # Length of longest data cell
                len(str(col)) # Length of the header name
            ) + 2 # Add a little extra space padding
            
            # Set the column width (A, B, C, etc.)
            col_letter = chr(65 + i) # 65 is ASCII for 'A'
            worksheet.column_dimensions[col_letter].width = max_len
            
    output.seek(0)
    return output

def generate_pdf(df):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # --- COLORS & STYLES ---
    primary_color = colors.HexColor("#8B0000") # Dark Red
    text_color = colors.HexColor("#2C3E50")    # Dark Blue/Grey
    
    # --- HEADER ---
    c.setFillColor(primary_color)
    c.rect(0, height-100, width, 100, fill=1, stroke=0)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(width/2, height-60, "MAREERO OPERATION REPORT")
    
    c.setFont("Helvetica", 12)
    date_str = datetime.now().strftime('%d %B %Y')
    c.drawCentredString(width/2, height-80, f"Taariikhda: {date_str}")

    # --- SECTION 1: SUMMARY ---
    c.setFillColor(text_color)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height-140, "1. KOOBITAAN (SUMMARY):")
    
    # SOMALI DESCRIPTION
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.darkgrey)
    c.drawString(40, height-160, "Halkan waxaa ku qoran warbixinta guud ee maanta, oo ay ku jiraan tirada shaqooyinka,")
    c.drawString(40, height-175, "alaabta maqan, iyo dalabyada cusub ee la diiwaangeliyay.")
    
    # Calc Metrics
    total = len(df)
    missing = len(df[df['Category'] == 'Maqan']) if not df.empty and 'Category' in df.columns else 0
    new_req = len(df[df['Category'] == 'Dalab Cusub']) if not df.empty and 'Category' in df.columns else 0
    
    # Draw Summary Box
    c.setStrokeColor(colors.lightgrey)
    c.rect(40, height-250, 515, 60, fill=0)
    
    c.setFillColor(text_color)
    c.setFont("Helvetica", 12)
    c.drawString(60, height-210, f"Wadarta (Total): {total}")
    c.drawString(240, height-210, f"Maqan (Missing): {missing}")
    c.drawString(420, height-210, f"Dalab (Requests): {new_req}")

    # --- SECTION 2: CHARTS ---
    y_chart = height-300
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y_chart, "2. SHAXDA XOGTA (CHARTS):")
    
    # SOMALI DESCRIPTION
    c.setFont("Helvetica", 10
