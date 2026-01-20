import streamlit as st
import re

# ---------------------------------------------------------
# PAGE CONFIGURATION (MUST BE FIRST)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Mareero System",
    page_icon="🏢",
    layout="wide"
)

# --- IMPORTS ---
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

# Try importing the connection; handle potential install name mismatches gracefully
try:
    from streamlit_gsheets import GSheetsConnection
except ImportError:
    st.error("⚠️ Library Error: 'st-gsheets-connection' is missing. Please add it to requirements.txt")
    st.stop()

import pandas as pd
from datetime import datetime
import pytz 
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
import io
import random
import os

# --- BACKUP FUNCTION ---
def perform_auto_backup(df):
    try:
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        # Keep it simple: standard CSV backup
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_path = os.path.join(backup_dir, f"backup_{timestamp}.csv")
        df.to_csv(file_path, index=False)
    except Exception as e:
        pass # Fail silently in background

# Check for xlsxwriter availability to prevent crashes
try:
    import xlsxwriter
    HAS_XLSXWRITER = True
except ImportError:
    HAS_XLSXWRITER = False

# --- 1. SETUP TIMEZONE (Somalia) ---
def get_local_time():
    tz = pytz.timezone('Africa/Mogadishu') 
    return datetime.now(tz)

# --- 2. CSS: RESPONSIVE THEME (Auto Dark/Light) ---
st.markdown("""
<style>
    /* 1. Hide Default Menus */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 2. Responsive Inputs */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: var(--secondary-background-color) !important;
        color: var(--text-color) !important;
        border-radius: 5px;
        border: 1px solid rgba(128, 128, 128, 0.2);
    }
    
    /* 3. Metric Cards */
    div[data-testid="stMetric"] {
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 15px;
        border-radius: 8px;
    }
    
    /* 4. BRANDING: Buttons (Navy Blue) */
    div[data-testid="stButton"] button {
        background-color: #1E3A8A; /* Navy Blue */
        color: white;
        border-radius: 5px;
        font-weight: bold;
        border: none;
    }
    div[data-testid="stButton"] button:hover {
        background-color: #8B0000; /* Red Hover */
        color: white;
    }
    
    /* 5. Tabs */
    .stTabs [aria-selected="true"] {
        background-color: #1E3A8A !important;
        color: white !important;
    }
    
    /* 6. Headers */
    h1, h2, h3 {
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. HYBRID DATA CONNECTION ---
# We read from Google Sheets (since it is public/shared) so you can see your existing data.
# We save new data locally to ensure it works without complex API keys.

GSHEET_ID = "1ZcYgQfWoexjj1bpwsgRywFw4L05lD2I4Zg3MCGr_2f0"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{GSHEET_ID}/export?format=csv"
LOCAL_FILE = "mareero_data.csv"

def load_data():
    # 🩹 FIX: Prevent Duplicate Data Logic
    # If we have a local file, it IS the master database. Do not merge with Google Sheet again.
    
    if os.path.exists(LOCAL_FILE):
        try:
            df = pd.read_csv(LOCAL_FILE)
            # Auto-clean duplicates that might have been created by previous bug
            df.drop_duplicates(inplace=True)
            return df
        except Exception:
            pass # If local file is corrupt, fall back to Sheet

    # Only load from Google Sheet if Local File doesn't exist yet
    try:
        df_sheet = pd.read_csv(CSV_URL)
        # Ensure columns match our expected schema
        expected_cols = ["Date", "Branch", "Employee", "Category", "Item", "Note"]
        for col in expected_cols:
            if col not in df_sheet.columns:
                df_sheet[col] = "" # Fill missing cols
        
        # Save meaningful initial data to local immediately so we switch to local mode
        df_sheet.to_csv(LOCAL_FILE, index=False)
        return df_sheet
        
    except Exception as e:
        # Fallback if both fail
        return pd.DataFrame(columns=["Date", "Branch", "Employee", "Category", "Item", "Note"])

def save_data(df):
    # We save the *Full* dataset locally so we don't lose anything
    # Note: This means the Google Sheet won't update, but the App will show the new data.
    df.to_csv(LOCAL_FILE, index=False)
    perform_auto_backup(df)


# --- 4. EXCEL ENGINE (ADVANCED MULTI-SHEET) ---
def generate_excel(df):
    output = io.BytesIO()
    
    # 🛡️ SANITIZE DATA: Prevent NAN/INF errors in Excel
    # Deep clean: Replace Infs, NaNs with empty string
    df = df.replace([float('inf'), float('-inf')], "").fillna("")
    
    # 📅 FIX DATE FORMAT
    if 'Date' in df.columns:
        try:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
            df['Date'] = df['Date'].replace("NaT", "")
        except Exception:
            pass

    if HAS_XLSXWRITER:
        # --- ADVANCED MODE ---
        # Enable nan_inf_to_errors to prevent crashes if any slip through
        with pd.ExcelWriter(output, engine='xlsxwriter', engine_kwargs={'options':{'nan_inf_to_errors': True}}) as writer:
            workbook = writer.book
            
            # --- STYLES ---
            header_fmt = workbook.add_format({
                'bold': True, 'bg_color': '#2C3E50', 'font_color': 'white', 'border': 1, 'align': 'center', 'valign': 'vcenter'
            })
            
            # Branch Color Palette
            branch_colors = {
                "Head Q": '#D6EAF8', "Branch 1": '#D5E8D4', "Branch 3": '#FFE6CC',
                "Branch 4": '#E1D5E7', "Branch 5": '#FADBD8', "Kaydka M.hassan": '#D0ECE7'
            }
            default_bg = '#FFFFFF'
            high_freq_font_color = '#C0392B'

            # ==========================================
            # SHEET 1: WARBIXIN (Data Report)
            # ==========================================
            sheet_main = workbook.add_worksheet('Warbixin')
            
            # Prepare Data
            df_report = df.copy()
            if not df_report.empty and 'Item' in df_report.columns:
                item_counts = df_report['Item'].value_counts()
                df_report['Count'] = df_report['Item'].map(item_counts).fillna(0).astype(int)
            else:
                df_report['Count'] = 1

            # Headers
            cols = list(df_report.columns)
            for col_num, value in enumerate(cols):
                sheet_main.write(0, col_num, value, header_fmt)

            # Rows
            for row_num, row_data in enumerate(df_report.values):
                branch_val = str(row_data[cols.index('Branch')]) if 'Branch' in cols else ''
                bg_color = branch_colors.get(branch_val, default_bg)
                
                # Formats
                row_fmt = workbook.add_format({'bg_color': bg_color, 'border': 1, 'align': 'left', 'valign': 'vcenter'})
                
                freq_val = row_data[cols.index('Count')] if 'Count' in cols else 0
                item_special_fmt = workbook.add_format({
                    'bg_color': bg_color, 'border': 1, 'align': 'left', 'valign': 'vcenter',
                    'font_color': high_freq_font_color, 'bold': True
                })

                for col_num, cell_value in enumerate(row_data):
                    cell_format = row_fmt
                    if cols[col_num] == 'Item' and isinstance(freq_val, (int, float)) and freq_val > 1:
                        cell_format = item_special_fmt
                    
                    # Safe Write
                    try:
                        sheet_main.write(row_num + 1, col_num, cell_value, cell_format)
                    except TypeError:
                        sheet_main.write(row_num + 1, col_num, str(cell_value), cell_format)

            # Auto-Fit
            for i, col in enumerate(cols):
                max_len = max(df_report[col].astype(str).map(len).max(), len(str(col))) + 4
                sheet_main.set_column(i, i, min(max_len, 50))

            # ==========================================
            # SHEET 2: WARBIXIN QORAN (Somali Text Report)
            # ==========================================
            sheet_analysis = workbook.add_worksheet('Falanqeyn')
            sheet_analysis.hide_gridlines(2)
            
            # Formats
            title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'font_color': '#1E3A8A'})
            subtitle_fmt = workbook.add_format({'bold': True, 'font_size': 12, 'underline': True, 'font_color': '#b91c1c'})
            cat_header_fmt = workbook.add_format({'bold': True, 'font_size': 12, 'font_color': '#2C3E50', 'bg_color': '#EAEDED', 'border': 1})
            text_fmt = workbook.add_format({'font_size': 11})
            text_bold_fmt = workbook.add_format({'font_size': 11, 'bold': True, 'font_color': '#C0392B'})
            
            row_cursor = 1
            sheet_analysis.write(row_cursor, 0, "WARBIXINTA GUUD EE MAREERO SYSTEM", title_fmt)
            row_cursor += 2
            
            # --- 1. Item Deep Dive (Grouped by Category) ---
            if 'Item' in df.columns:
                counts = df['Item'].value_counts()
                valid_items = counts[counts > 1].index.tolist()
                analysis_df = df[df['Item'].isin(valid_items)].copy()
            else:
                analysis_df = df.copy()

            if not analysis_df.empty and 'Category' in analysis_df.columns:
                categories = analysis_df['Category'].unique()
                
                for cat in categories:
                    # Header
                    sheet_analysis.write(row_cursor, 0, f"📂 SECTION: {cat}", cat_header_fmt)
                    sheet_analysis.write(row_cursor, 1, "", cat_header_fmt) # Merge effect
                    
                    row_cursor += 1
                    
                    cat_items = analysis_df[analysis_df['Category'] == cat]
                    grouped = cat_items.groupby('Item')
                    
                    for item_name, group in grouped:
                        # Item Name
                        sheet_analysis.write(row_cursor, 0, f"📦 {item_name}", text_bold_fmt)
                        
                        # Branch Breakdown
                        branch_summary = []
                        branch_counts = group['Branch'].value_counts()
                        for br, count in branch_counts.items():
                            branch_summary.append(f"{br} ({count})")
                        
                        summary_str = ", ".join(branch_summary)
                        total_count = len(group)
                        
                        sheet_analysis.write(row_cursor, 1, f"Total: {total_count} | {summary_str}", text_fmt)
                        row_cursor += 1
                    
                    row_cursor += 1
            else:
                sheet_analysis.write(row_cursor, 0, "Ma jiraan alaab soo noqnoqotay (No recurring items found).", text_fmt)
                
            row_cursor += 1

            # --- 2. Branches ---
            sheet_analysis.write(row_cursor, 0, "2. Kala Horeynta Laamaha (Branch Activity):", subtitle_fmt)
            row_cursor += 1
            if not df.empty and 'Branch' in df.columns:
                branch_counts = df['Branch'].value_counts()
                if not branch_counts.empty:
                    top_branch = branch_counts.idxmax()
                    sheet_analysis.write(row_cursor, 0, f"Laanta ugu shaqada badan wakhtigan waa '{top_branch}' oo soo dirtay {branch_counts.max()} warbixin.", text_fmt)
                    row_cursor += 2
                    for branch, count in branch_counts.items():
                         sheet_analysis.write(row_cursor, 0, f"• {branch}: {count} warbixin", text_fmt)
                         row_cursor += 1
            row_cursor += 2
            
            # --- 3. Staff ---
            sheet_analysis.write(row_cursor, 0, "3. Warbixinta Shaqaalaha (Staff Report):", subtitle_fmt)
            row_cursor += 1
            if not df.empty and 'Employee' in df.columns:
                staff_counts = df['Employee'].value_counts().head(5)
                if not staff_counts.empty:
                    top_staff = staff_counts.idxmax()
                    sheet_analysis.write(row_cursor, 0, f"Shaqaalaha ugu firfircoon waa '{top_staff}'.", text_fmt)
                    row_cursor += 2
                    for staff, count in staff_counts.items():
                        sheet_analysis.write(row_cursor, 0, f"• {staff}: {count} warbixin", text_fmt)
                        row_cursor += 1

            sheet_analysis.set_column(0, 0, 70)

    else:
        # --- BASIC FALLBACK ---
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Warbixin')

    output.seek(0)
    return output

# --- 5. PDF ENGINE ---
# --- 5. PDF ENGINE (ULTRA-PREMIUM FIXED) ---
def generate_pdf(df):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # --- DESIGN SYSTEM ---
    # Colors
    primary_col = colors.HexColor("#1E3A8A")    # Brand Blue
    accent_col = colors.HexColor("#EF4444")     # Brand Red
    text_col = colors.HexColor("#1e293b")       # Dark Slate
    subtext_col = colors.HexColor("#64748B")    # Light Slate
    border_col = colors.HexColor("#E2E8F0")     # Border
    
    # Helper to clean/truncate text
    def clean_text(text, max_len=20):
        t = str(text).strip().replace("\n", " ").replace("\r", "")
        return (t[:max_len] + '..') if len(t) > max_len else t

    # ==========================
    # 1. HEADER & BRANDING
    # ==========================
    # Top Strip
    c.setFillColor(primary_col)
    c.rect(0, height-25, width, 25, fill=1, stroke=0)
    
    # Logo Area (Text Based Fallback or Image if exists)
    # We will simulate the logo aesthetic with shapes/text if image missing
    
    # Draw "MAREERO"
    c.setFillColor(primary_col)
    c.setFont("Helvetica-Bold", 32)
    c.drawString(40, height-75, "MAREERO")
    
    # Red Swooshes (Simulated with text accents)
    c.setFillColor(accent_col)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(220, height-60, "GENERAL TRADING LLC")
    
    c.setFillColor(subtext_col)
    c.setFont("Helvetica", 9)
    c.drawString(40, height-95, "Automotive Parts & General Supplies | Advanced Reporting System")

    # Date Stamp (Right Side)
    now = get_local_time()
    c.setStrokeColor(border_col)
    c.setLineWidth(1)
    c.line(width-170, height-50, width-170, height-90) # Vertical Divider
    
    c.setFillColor(text_col)
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(width-40, height-65, now.strftime("%d %B %Y").upper())
    c.setFillColor(subtext_col)
    c.setFont("Helvetica", 8)
    c.drawRightString(width-40, height-80, now.strftime("%I:%M %p") + " | GENERATED")

    y_cursor = height - 140

    # ==========================
    # 2. EXECUTIVE DASHBOARD
    # ==========================
    c.setFillColor(primary_col)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y_cursor, "EXECUTIVE SUMMARY")
    c.setStrokeColor(accent_col)
    c.setLineWidth(2)
    c.line(40, y_cursor-6, 160, y_cursor-6) 
    y_cursor -= 30

    # Metrics
    total_reps = len(df)
    missing = len(df[df['Category'] == "Alaabta go'an"]) if not df.empty else 0
    requests = len(df[df['Category'] == "bahiyaha Dadweynaha"]) if not df.empty else 0
    market = len(df[df['Category'] == "alaabta Suuqa leh"]) if not df.empty else 0
    
    metrics_data = [
        {"lbl": "TOTAL REPORTS", "val": str(total_reps), "col": "#F8FAFC", "txt": "#0F172A"},
        {"lbl": "MISSING / DAMAGED", "val": str(missing), "col": "#FEF2F2", "txt": "#DC2626"},
        {"lbl": "MARKET STOCK", "val": str(market), "col": "#F0FDF4", "txt": "#15803d"},
        {"lbl": "NEW REQUESTS", "val": str(requests), "col": "#FFFBEB", "txt": "#B45309"}
    ]

    card_w = 120
    card_h = 55
    card_gap = 15
    for i, m in enumerate(metrics_data):
        cx = 40 + (i * (card_w + card_gap))
        
        c.setFillColor(colors.HexColor(m['col']))
        c.setStrokeColor(border_col)
        c.setLineWidth(0.5)
        c.roundRect(cx, y_cursor-card_h, card_w, card_h, 4, fill=1, stroke=1)
        
        c.setFillColor(colors.HexColor(m['txt']))
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(cx + card_w/2, y_cursor-28, m['val'])
        
        c.setFillColor(subtext_col)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(cx + card_w/2, y_cursor-45, m['lbl'])
    
    y_cursor -= (card_h + 40)

    # ==========================
    # 3. ANALYTICS (Charts)
    # ==========================
    c.setFillColor(primary_col)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y_cursor, "PERFORMANCE ANALYTICS")
    c.setStrokeColor(primary_col) 
    c.line(40, y_cursor-6, 200, y_cursor-6)
    y_cursor -= 20

    if not df.empty:
        try:
            plt.style.use('default') 
            
            # Bar Chart
            fig1, ax1 = plt.subplots(figsize=(5, 2.2))
            branch_counts = df['Branch'].value_counts().head(5)
            ax1.bar(branch_counts.index, branch_counts.values, color="#1E3A8A", width=0.5)
            ax1.set_title("Reports Volume by Branch", fontsize=8, fontweight='bold', color="#334155")
            ax1.tick_params(axis='x', labelsize=6, rotation=20, colors="#64748B")
            ax1.tick_params(axis='y', labelsize=6, colors="#64748B")
            ax1.spines['top'].set_visible(False)
            ax1.spines['right'].set_visible(False)
            ax1.spines['left'].set_color('#E2E8F0')
            ax1.spines['bottom'].set_color('#E2E8F0')
            
            img1 = io.BytesIO()
            plt.savefig(img1, format='png', dpi=150, bbox_inches='tight')
            img1.seek(0)
            c.drawImage(ImageReader(img1), 40, y_cursor-150, width=300, height=140)
            plt.close(fig1)

            # Donut Chart
            fig2, ax2 = plt.subplots(figsize=(2.5, 2.5))
            cat_counts = df['Category'].value_counts()
            patches, texts, autotexts = ax2.pie(cat_counts, labels=None, autopct='%1.0f%%', 
                colors=['#EF4444', '#F59E0B', '#10B981'], startangle=90, pctdistance=0.85)
            
            centre_circle = plt.Circle((0,0),0.60,fc='white')
            fig2.gca().add_artist(centre_circle)
            ax2.set_title("Category Split", fontsize=8, fontweight='bold', color="#334155")
            plt.setp(autotexts, size=6, weight="bold", color="white")
            
            img2 = io.BytesIO()
            plt.savefig(img2, format='png', dpi=150, bbox_inches='tight')
            img2.seek(0)
            c.drawImage(ImageReader(img2), 360, y_cursor-150, width=140, height=140)
            plt.close(fig2)

        except Exception:
            c.drawString(40, y_cursor-50, "Data insufficient for charts.")

    y_cursor -= 170

    # ==========================
    # 4. DATA TABLE (Grid Layout)
    # ==========================
    c.setFillColor(primary_col)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y_cursor, "DETAILED RECENT LOGS")
    c.setStrokeColor(primary_col)
    c.line(40, y_cursor-6, 170, y_cursor-6)
    y_cursor -= 25

    # Table Config
    col_widths = [100, 145, 90, 90, 90]
    headers = ["CATEGORY", "ITEM", "BRANCH", "STAFF", "NOTES"]
    x_starts = [40]
    for w in col_widths:
        x_starts.append(x_starts[-1] + w)

    # Header Row
    c.setFillColor(primary_col)
    c.rect(40, y_cursor-15, sum(col_widths), 20, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 7)
    for i, h in enumerate(headers):
        c.drawString(x_starts[i] + 5, y_cursor-8, h)
    
    y_cursor -= 15

    # Rows
    if not df.empty:
        df_sorted = df.sort_values(by='Date', ascending=False).head(35)
        
        c.setFont("Helvetica", 7)
        c.setLineWidth(0.5)
        c.setStrokeColor(border_col)
        
        for idx, (_, row) in enumerate(df_sorted.iterrows()):
            bg = colors.HexColor("#F8FAFC") if idx % 2 == 0 else colors.white
            
            c.setFillColor(bg)
            c.rect(40, y_cursor-15, sum(col_widths), 15, fill=1, stroke=0)
            
            # Verticals
            for x_line in x_starts:
                c.line(x_line, y_cursor, x_line, y_cursor-15)
            
            # Data
            cat = clean_text(row.get('Category', ''), 18)
            item = clean_text(row.get('Item', ''), 28)
            branch = clean_text(row.get('Branch', ''), 16)
            staff = clean_text(row.get('Employee', ''), 16)
            note = clean_text(row.get('Note', ''), 18)
            
            row_vals = [cat, item, branch, staff, note]
            
            # Cell Text
            c.setFillColor(text_col)
            # Conditional Color for Category
            if "go'an" in str(row.get('Category', '')): c.setFillColor(colors.HexColor("#DC2626")) 
            elif "Dadweynaha" in str(row.get('Category', '')): c.setFillColor(colors.HexColor("#D97706"))
            
            c.drawString(x_starts[0] + 5, y_cursor-10, row_vals[0]) # Cat
            
            c.setFillColor(text_col)
            for i in range(1, 5):
                c.drawString(x_starts[i] + 5, y_cursor-10, row_vals[i])
            
            # Horizontal Line
            c.setStrokeColor(border_col)
            c.line(40, y_cursor-15, 40+sum(col_widths), y_cursor-15)
            
            y_cursor -= 15
            
            # Page Break
            if y_cursor < 40:
                c.showPage()
                y_cursor = height - 50
                # Reprint Header
                c.setFillColor(primary_col)
                c.rect(40, y_cursor-15, sum(col_widths), 20, fill=1, stroke=0)
                c.setFillColor(colors.white)
                c.setFont("Helvetica-Bold", 7)
                for i, h in enumerate(headers):
                    c.drawString(x_starts[i] + 5, y_cursor-8, h)
                y_cursor -= 15
                c.setFont("Helvetica", 7)
                c.setStrokeColor(border_col)

    c.save()
    buffer.seek(0)
    return buffer

# --- 6. APP UI (ADVANCED ULTRA-MODERN DESIGN) ---
# Custom CSS for Premium Look
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
        
        html, body, [class*="css"]  {
            font-family: 'Inter', sans-serif;
        }
        
        /* Main Background - Use Native Theme, or transparent */
        .stApp {
            /* Removing hardcoded white background so Dark Mode works */
            background-color: transparent; 
        }
        
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 5rem !important;
        }
        header[data-testid="stHeader"] {
            background: transparent;
        }
        
        /* Premium Header Container */
        .header-container {
            background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%);
            padding: 35px 20px;
            border-radius: 0px 0px 24px 24px;
            color: white;
            text-align: center;
            box-shadow: 0 10px 25px -5px rgba(30, 58, 138, 0.4);
            margin-bottom: 30px;
            margin-top: -60px;
            position: relative;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        
        /* CSS Logo Component (No Image Dependency) */
        .css-logo {
            width: 80px;
            height: 80px;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 40px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            border: 1px solid rgba(255,255,255,0.2);
            margin-bottom: 15px;
            z-index: 10;
        }
        
        .header-title {
            font-size: 32px;
            font-weight: 800;
            margin: 0;
            letter-spacing: -0.5px;
            text-transform: uppercase;
            background: linear-gradient(to right, #ffffff, #e2e8f0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            z-index: 10;
        }
        .header-subtitle {
            font-size: 14px;
            color: #94A3B8;
            margin-top: 5px;
            font-weight: 500;
            letter-spacing: 0.5px;
            z-index: 10;
        }
        
        /* Modern Tabs - Theme Aware */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: var(--secondary-background-color);
            padding: 8px;
            border-radius: 50px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            display: inline-flex;
            justify-content: center;
            margin: 0 auto 20px auto;
            border: 1px solid rgba(128, 128, 128, 0.2); 
        }
        .stTabs [data-baseweb="tab"] {
            height: 40px;
            border-radius: 40px;
            color: var(--text-color);
            font-weight: 600;
            font-size: 14px;
            padding: 0 24px;
            border: none;
        }
        .stTabs [aria-selected="true"] {
            background-color: #1E3A8A;
            color: white;
            box-shadow: 0 2px 4px rgba(30, 58, 138, 0.3);
        }
        
        /* Mobile Responsive Rules */
        @media only screen and (max-width: 640px) {
            /* Compact Header */
            .header-container {
                padding: 20px 15px;
                border-radius: 0 0 20px 20px;
                margin-top: -50px;
            }
            .css-logo {
                width: 60px;
                height: 60px;
                font-size: 30px;
            }
            .header-title {
                font-size: 22px; /* Smaller title */
                line-height: 1.2;
            }
            .header-subtitle {
                font-size: 11px; /* Smaller subtitle */
            }
            
            /* Scrollable Tabs */
            .stTabs [data-baseweb="tab-list"] {
                display: flex;
                overflow-x: auto;
                white-space: nowrap;
                justify-content: flex-start; /* Left align on mobile for scrolling */
                padding: 5px;
                width: 100%;
                -webkit-overflow-scrolling: touch; /* Smooth scroll on iOS */
            }
            .stTabs [data-baseweb="tab"] {
                padding: 0 15px;
                font-size: 12px;
                height: 35px;
                flex-shrink: 0; /* Prevent squishing */
            }
            
            /* Full Width Buttons */
            div.stButton > button {
                width: 100%;
                padding: 12px 10px;
                font-size: 14px;
            }
            
            /* Form Input Spacing */
            .stTextInput, .stSelectbox {
                margin-bottom: -10px;
            }
            
            /* Reduce whitespace inside cards */
            div[data-testid="stVerticalBlock"] > div {
                gap: 0.5rem;
            }
        }

        /* Gradient Button */
        div.stButton > button {
            background: linear-gradient(135deg, #2563EB, #1D4ED8);
            color: white;
            border: none;
            border-radius: 12px;
            padding: 12px 28px;
            font-weight: 600;
            box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.3);
            transition: all 0.3s ease;
        }
        div.stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.4);
        }
    </style>
""", unsafe_allow_html=True)

# Advanced Banner with CSS Logo
st.markdown("""
<div class="header-container">
    <div class="css-logo">⚙️</div>
    <div class="header-title">MAREERO GENERAL TRADING</div>
    <div class="header-subtitle">Advanced Operational Management System v2.1</div>
</div>
""", unsafe_allow_html=True)

tab_staff, tab_manager = st.tabs(["📝 Qeybta Shaqaalaha (Staff)", "🔐 Maamulka (Manager)"])

# --- STAFF TAB ---
with tab_staff:
    
    with st.container(border=True):
        with st.form("log_form", clear_on_submit=True):
            st.markdown("### 📋 Diiwaangelinta Warbixinta Cusub") 
            c1, c2 = st.columns(2)
            with c1:
                branch_options = ["Head Q", "Branch 1", "Branch 3", "Branch 4", "Branch 5" , "Kaydka M.hassan"]
                branch = st.selectbox("📍 Xulo Laanta (Select Branch)", branch_options)
                employee = st.text_input("👤 Magacaaga (Your Name)")
            with c2:
                cat_map = {
                    "Alaabta go'an (Missing)": "Alaabta go'an",
                    "alaabta Suuqa leh (High Demand)": "alaabta Suuqa leh",
                    "bahiyaha Dadweynaha (New Request)": "bahiyaha Dadweynaha"
                }
                category_selection = st.selectbox("📂 Nooca Warbixinta (Type)", list(cat_map.keys()))
                item = st.text_input("📦 Magaca Alaabta (Item Name)")
            
            note = st.text_input("📝 Faahfaahin / Tirada (Note/Qty)", placeholder="Ex: 5 pieces required...")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("🚀 Gudbi Warbixinta (Submit Report)", use_container_width=True):
                if employee and item:
                    try:
                        data = load_data()
                        
                        real_category = cat_map[category_selection]
                        # Use format compatible with pd.to_datetime default parsing
                        current_local_time = get_local_time().strftime("%Y-%m-%d %H:%M")
                        
                        new_row = pd.DataFrame([{
                            "Date": current_local_time,
                            "Branch": branch,
                            "Employee": employee,
                            "Category": real_category,
                            "Item": item,
                            "Note": note
                        }])
                        
                        updated = pd.concat([data, new_row], ignore_index=True)
                        save_data(updated)
                        st.cache_data.clear()

                        st.success(f"✅ Waa la gudbiyay! ({current_local_time})")
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("⚠️ Fadlan buuxi Magacaaga iyo Alaabta.")

# --- MANAGER TAB ---
with tab_manager:
    
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        c_pass, c_btn = st.columns([4, 1], vertical_alignment="bottom")
        with c_pass:
            password = st.text_input("Geli Furaha (Password)", type="password")
        with c_btn:
            if st.button("➡️", type="primary"):
                if password == "mareero2025":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Wrong Password")

    if st.session_state.logged_in:
        c_head, c_logout = st.columns([4,1])
        with c_head:
            st.success("🔓 Soo dhawoow Maamule")
        with c_logout:
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.rerun()
        
        try:
            df = load_data()
            if not df.empty and 'Date' in df.columns:
                # 📅 ROBUST DATE PARSING
                # 1. Attempt standard datetime conversion
                df['Date_Parsed'] = pd.to_datetime(df['Date'], errors='coerce')
                
                # 2. Fill NaT (failed parses) with the original string so we don't show "None"
                # This ensures if the date is just text like "Last Monday", it still shows up!
                df['Date'] = df['Date_Parsed'].dt.strftime('%d %b %Y, %I:%M %p').fillna(df['Date'])
                
                # Drop the temp column
                df.drop(columns=['Date_Parsed'], inplace=True)
                
        except Exception as e:
            st.error(f"⚠️ Data Load Error: {e}")
            df = pd.DataFrame()

        if not df.empty:
            st.markdown("---")
            
            # METRICS
            count_total = len(df)
            count_missing = len(df[df['Category'] == 'Alaabta go\'an']) if 'Category' in df.columns else 0
            count_new = len(df[df['Category'] == 'bahiyaha Dadweynaha']) if 'Category' in df.columns else 0
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Wadarta (Total)", count_total)
            m2.metric("Alaabta go'an", count_missing, delta_color="inverse")
            m3.metric("Dalab", count_new)
            
            st.markdown("---")

            # --- 📈 ANALYTICS DASHBOARD ---
            st.subheader("📊 Analytics & Trends")
            
            if not df.empty and 'Date' in df.columns:
                # Prepare data
                chart_df = df.copy()
                # Safe Convert for Charts: If conversion fails, row becomes NaT and is dropped safely for plotting
                chart_df['Date'] = pd.to_datetime(chart_df['Date'], errors='coerce')
                chart_df = chart_df.dropna(subset=['Date']) # Remove invalid dates from chart to prevent crash
                
                # Layout
                col_chart1, col_chart2 = st.columns(2)
                
                with col_chart1:
                    st.markdown("**📈 Activity Over Time**")
                    # Group by Date
                    daily_data = chart_df.groupby(chart_df['Date'].dt.date).size()
                    st.bar_chart(daily_data, color="#1E3A8A")
                    
                with col_chart2:
                    st.markdown("**🏢 Branch Performance**")
                    # Group by Branch
                    branch_data = chart_df['Branch'].value_counts()
                    st.bar_chart(branch_data, color="#ffaa00", horizontal=True)

            st.markdown("---")
            
            # --- SEARCH & FILTER ---
            st.subheader("🔍 Search & Filter")
            
            # Prepare Search Options (Auto-Complete)
            search_options = []
            if not df.empty:
                # We collect unique values from key columns to show as suggestions
                for col in ['Branch', 'Employee', 'Item', 'Category']:
                    if col in df.columns:
                        unique_vals = df[col].dropna().unique().tolist()
                        search_options.extend(unique_vals)
            
            # Remove duplicates and sort
            search_options = sorted(list(set(map(str, search_options))))

            col_search, col_filter = st.columns(2)
            
            with col_search:
                # Replaced text_input with multiselect for "Suggestions"
                selected_terms = st.multiselect(
                    "🔍 Raadi (Select Branch, Staff, or Item)", 
                    options=search_options,
                    placeholder="Click to select or type to search..."
                )
                
            with col_filter:
                date_filter = st.selectbox("📅 Waqtiga (Time Filter)", ["All Time", "Today (Maanta)", "This Week (Isbuucan)"])
            
            filtered_df = df.copy()
            now = get_local_time()
            
            if date_filter == "Today (Maanta)":
                filtered_df = filtered_df[filtered_df['Date'].dt.date == now.date()]
            elif date_filter == "This Week (Isbuucan)":
                start_week = now - pd.Timedelta(days=7)
                filtered_df = filtered_df[filtered_df['Date'] >= start_week]
                
            # Filter Logic: AND (Must match all selected terms - e.g. "Branch 1" AND "Ali")
            if selected_terms:
                for term in selected_terms:
                    # Filter rows where ANY column contains the term
                    filtered_df = filtered_df[filtered_df.astype(str).apply(lambda x: x.str.contains(term, case=False, regex=False).any(), axis=1)]

            

            # --- DOWNLOAD BUTTONS ---
            st.subheader("📄 Warbixinada (Reports)")
            if not filtered_df.empty:
                c1, c2 = st.columns(2)
                with c1:
                    st.download_button(
                        label=f"📥 Download PDF ({len(filtered_df)} items)",
                        data=generate_pdf(filtered_df),
                        file_name=f"Mareero_Report_{get_local_time().strftime('%Y-%m-%d')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                with c2:
                    if not HAS_XLSXWRITER:
                        st.caption("⚠️ Install 'xlsxwriter' for advanced charts. Using basic mode.")
                    
                    st.download_button(
                        label=f"📥 Download Excel ({len(filtered_df)} items)",
                        data=generate_excel(filtered_df),
                        file_name=f"Mareero_Data_{get_local_time().strftime('%Y-%m-%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            else:
                st.warning("⚠️ No data matches your search/filter.")

            st.markdown("---")
            
            # --- 💾 BACKUP SECTION ---
            with st.expander("💾 Backup & Restore", expanded=False):
                st.warning("Ensure you download regular backups of your data.")
                
                # Manual Download
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Full System Backup (CSV)",
                    data=csv_data,
                    file_name=f"Mareero_Full_Backup_{get_local_time().strftime('%Y-%m-%d')}.csv",
                    mime="text/csv",
                    type="primary"
                )
                
                st.info(f"ℹ️ Auto-backups are saved locally in the 'backups/' folder.")

            # --- SMOOTH BATCH DELETE SECTION ---
            st.markdown("---")
            st.subheader("🛠️ Management Studio")
            
            with st.container(border=True):
                if not filtered_df.empty:
                    # Prepare Data
                    df_with_delete = filtered_df.copy()
                    df_with_delete.insert(0, "Select", False)
                    
                    # Dropdown Options
                    branch_options = ["Head Q", "Branch 1", "Branch 3", "Branch 4", "Branch 5" , "Kaydka M.hassan"]
                    cat_options = ["Alaabta go'an", "alaabta Suuqa leh", "bahiyaha Dadweynaha"]

                    # 🔴 START FORM
                    with st.form("delete_form", border=False):
                        st.caption("💡 **Tip:** Double-click any cell to edit details. Check the box on the left to mark for deletion.")
                        
                        edited_df = st.data_editor(
                            df_with_delete,
                            num_rows="fixed",
                            hide_index=True,
                            use_container_width=True,
                            key="data_editor",
                            column_config={
                                "Select": st.column_config.CheckboxColumn(
                                    "🗑️",
                                    help="Mark for Deletion",
                                    default=False,
                                    width="small",
                                ),
                                "Date": st.column_config.DatetimeColumn(
                                    "📅 Date/Time",
                                    format="D MMM YYYY, h:mm a",
                                    disabled=True, # Prevent accidental date changes
                                    width="medium"
                                ),
                                "Branch": st.column_config.SelectboxColumn(
                                    "📍 Branch",
                                    options=branch_options,
                                    required=True,
                                    width="medium"
                                ),
                                "Category": st.column_config.SelectboxColumn(
                                    "📂 Category",
                                    options=cat_options,
                                    required=True,
                                    width="medium"
                                ),
                                "Employee": st.column_config.TextColumn(
                                    "👤 Staff Name",
                                    width="medium"
                                ),
                                "Item": st.column_config.TextColumn(
                                    "📦 Item Name",
                                    width="large",
                                    required=True
                                ),
                                "Note": st.column_config.TextColumn(
                                    "📝 Notes",
                                    width="large"
                                )
                            }
                        )
                        
                        st.markdown("<br>", unsafe_allow_html=True) # Spacer
                        
                        c_info, c_save, c_del = st.columns([2, 1, 1])
                        with c_info:
                             st.markdown(f"**🔢 Total Records:** {len(edited_df)}")
                        with c_save:
                            # Button 1: Save Changes (Edits)
                            save_btn = st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True)
                        with c_del:
                            # Button 2: Trigger Delete Logic
                            delete_btn = st.form_submit_button("❌ Delete Selected", use_container_width=True)
                    # 🔴 END FORM

                    # --- LOGIC HANDLER (Runs only after button click) ---
                    
                    # 1. Handle Save
                    if save_btn:
                        try:
                            final_df = edited_df.drop(columns=["Select"])
                            save_data(final_df)
                            st.cache_data.clear()
                            st.success("✅ Saved Successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

                    # 2. Handle Delete Request
                    if delete_btn:
                        if edited_df["Select"].any():
                            st.session_state.confirm_delete = True
                        else:
                            st.warning("⚠️ Fadlan xulo safafka (Please select rows first).")

                    # 3. Confirmation Box (Outside the form for safety)
                    if st.session_state.get("confirm_delete", False):
                        st.warning("⚠️ Ma hubtaa inaad tirtirto? (Are you sure?)")
                        col_yes, col_no = st.columns(2)
                        
                        with col_yes:
                            if st.button("✅ Haa (Yes, Delete)", type="primary", use_container_width=True):
                                try:
                                    # Filter out selected rows
                                    rows_to_keep = edited_df[edited_df["Select"] == False]
                                    final_df = rows_to_keep.drop(columns=["Select"])
                                    
                                    # Update Google Sheet
                                    save_data(final_df)
                                    
                                    # Reset State
                                    st.cache_data.clear()
                                    st.session_state.confirm_delete = False
                                    st.success("✅ Deleted Successfully!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                        
                        with col_no:
                            if st.button("❌ Maya (Cancel)", use_container_width=True):
                                st.session_state.confirm_delete = False
                                st.rerun()
                else:
                    st.info("No data found for this filter.")
        else:
            st.info("ℹ️ No data available yet. Add entries in the Staff tab to see them here.")



