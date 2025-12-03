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
        
        # --- NEW FIX: Auto-Adjust Column Widths ---
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
    c.drawString(60, height-210, f"Wadarta Shaqooyinka: {total}")
    c.drawString(240, height-210, f"Alaabta Maqan: {missing}")
    c.drawString(420, height-210, f"Dalabyada Cusub: {new_req}")

    # --- SECTION 2: CHARTS ---
    y_chart = height-300
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y_chart, "2. SHAXDA XOGTA (CHARTS):")
    
    # SOMALI DESCRIPTION
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.darkgrey)
    c.drawString(40, y_chart-20, "Shaxdan hoose waxay kala dhigdhigeysaa xogta iyadoo loo eegayo Qeybaha (Categories)")
    c.drawString(40, y_chart-35, "iyo Laamaha (Branches) si loo fahmo halka shaqadu u badan tahay.")
    
    if not df.empty and 'Category' in df.columns and 'Branch' in df.columns:
        try:
            # Chart 1: Pie
            fig1, ax1 = plt.subplots(figsize=(4, 3))
            category_counts = df['Category'].value_counts()
            if not category_counts.empty:
                ax1.pie(category_counts, labels=category_counts.index, autopct='%1.0f%%', colors=['#ff9999','#66b3ff','#99ff99','#ffcc99'])
                ax1.set_title("Qeybaha", fontsize=10)
                
                img1 = io.BytesIO()
                plt.savefig(img1, format='png', bbox_inches='tight')
                plt.close(fig1)
                img1.seek(0)
                c.drawImage(ImageReader(img1), 40, y_chart-260, width=240, height=180)
            
            # Chart 2: Bar
            fig2, ax2 = plt.subplots(figsize=(4, 3))
            branch_counts = df['Branch'].value_counts()
            if not branch_counts.empty:
                branch_counts.plot(kind='bar', color='#8B0000', ax=ax2)
                ax2.set_title("Laamaha", fontsize=10)
                plt.xticks(rotation=45, ha='right')
                
                img2 = io.BytesIO()
                plt.savefig(img2, format='png', bbox_inches='tight')
                plt.close(fig2)
                img2.seek(0)
                c.drawImage(ImageReader(img2), 300, y_chart-260, width=240, height=180)
        except Exception:
            c.drawString(40, y_chart-60, "Error generating charts.")
    else:
        c.drawString(40, y_chart-60, "Xog kuma filna shaxda.")

    # --- SECTION 3: CRITICAL LIST ---
    y_list = y_chart - 290
    c.setFillColor(text_color)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y_list, "3. ALAABTA MUHIIMKA AH (CRITICAL ITEMS):")

    # SOMALI DESCRIPTION
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.darkgrey)
    c.drawString(40, y_list-20, "Liiskan wuxuu muujinayaa alaabta 'Maqan' ama 'Dalabka Sare' ah ee u baahan fiiro gaar ah.")
    
    # Table Header
    c.setFillColor(colors.lightgrey)
    c.rect(40, y_list-50, 515, 20, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y_list-45, "CATEGORY")
    c.drawString(150, y_list-45, "ITEM NAME")
    c.drawString(300, y_list-45, "BRANCH")
    c.drawString(420, y_list-45, "NOTE")
    
    y_row = y_list - 70
    c.setFont("Helvetica", 10)
    
    if not df.empty and 'Category' in df.columns:
        # Filter for Maqan or Dalab Sare
        critical_df = df[df['Category'].isin(['Maqan', 'Dalab Sare'])].head(15)
        for _, row in critical_df.iterrows():
            c.drawString(50, y_row, str(row.get('Category', '')))
            c.drawString(150, y_row, str(row.get('Item', ''))[:25]) # Cut text if too long
            c.drawString(300, y_row, str(row.get('Branch', '')))
            c.drawString(420, y_row, str(row.get('Note', ''))[:20])
            c.line(40, y_row-5, 555, y_row-5) # Underline
            y_row -= 20
            
            if y_row < 50: # New page check
                c.showPage()
                y_row = height - 50

    c.save()
    buffer.seek(0)
    return buffer

# --- 3. THE APP UI ---
st.title("🏢 Mareero System")

# TABS
tab_staff, tab_manager = st.tabs(["📝 Qeybta Shaqaalaha (Staff)", "🔐 Maamulka (Manager)"])

# --- STAFF TAB ---
with tab_staff:
    st.info("Fadlan halkan ku diiwaangeli warbixintaada maalinlaha ah.")
    
    with st.form("log_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            branch_options = ["Kaydka M.Hassan", "Branch 1", "Branch 3", "Branch 4", "Branch 5"]
            branch = st.selectbox("📍 Branch", branch_options)
            employee = st.text_input("👤 Magacaaga (Your Name)")
        with c2:
            cat_map = {
                "Alaab Maqan (Missing)": "Maqan",
                "Dalab Sare (High Demand)": "Dalab Sare",
                "Dalab Cusub (New Request)": "Dalab Cusub"
            }
            category_selection = st.selectbox("📂 Nooca Warbixinta (Report Type)", list(cat_map.keys()))
            item = st.text_input("📦 Magaca Alaabta (Item Name)")
        
        note = st.text_input("📝 Faahfaahin / Tirada (Note/Qty)")
        
        if st.form_submit_button("🚀 Gudbi (Submit)", use_container_width=True):
            if employee and item:
                try:
                    data = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=0)
                    if data is None: data = pd.DataFrame()
                    data = data.dropna(how="all")
                    
                    real_category = cat_map[category_selection]
                    
                    new_row = pd.DataFrame([{
                        "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Branch": branch,
                        "Employee": employee,
                        "Category": real_category,
                        "Item": item,
                        "Note": note
                    }])
                    
                    updated = pd.concat([data, new_row], ignore_index=True)
                    conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=updated)
                    st.cache_data.clear()
                    st.success("✅ Waa la gudbiyay! (Sent Successfully)")
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("⚠️ Fadlan buuxi Magacaaga iyo Alaabta.")

# --- MANAGER TAB ---
with tab_manager:
    
    # --- 1. LOGIN ROW WITH ENTER BUTTON ---
    # [5, 1] means input is wide, button is small
    c_pass, c_btn = st.columns([5, 1], vertical_alignment="bottom")
    
    with c_pass:
        password = st.text_input("Geli Furaha (Password)", type="password", placeholder="Enter Password...", label_visibility="collapsed")
    with c_btn:
        # The Enter Button (Arrow Icon)
        login_click = st.button("➡️", help="Enter")

    if password == "mareero2025" or login_click:
        if password == "mareero2025":
            st.success("🔓 Soo dhawoow Maamule")
            
            # Load Data
            try:
                df = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=0)
                if df is None: df = pd.DataFrame()
                df = df.dropna(how="all")
            except:
                df = pd.DataFrame()

            if not df.empty:
                # METRICS
                m1, m2, m3 = st.columns(3)
                m1.metric("Wadarta Guud", len(df))
                m2.metric("Alaabta Maqan", len(df[df['Category']
