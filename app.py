import streamlit as st

# ---------------------------------------------------------
# PAGE CONFIGURATION
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
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz # NEW: For real timezone handling
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
import io
import random

# --- SET TIMEZONE (SOMALIA/EAST AFRICA) ---
def get_local_time():
    # Defines East Africa Time (Somalia)
    tz = pytz.timezone('Africa/Mogadishu') 
    return datetime.now(tz)

# --- CSS: PROFESSIONAL UI THEME ---
st.markdown("""
<style>
    /* Main Background adjustments */
    .block-container { padding-top: 1.5rem; padding-bottom: 3rem; }
    
    /* Hide Default Streamlit Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom Card Style for Metrics */
    div[data-testid="stMetric"] {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
        text-align: center;
    }
    
    /* Buttons */
    div[data-testid="stButton"] button {
        border-radius: 8px;
        font-weight: bold;
        transition: 0.3s;
    }
    
    /* Submit Button Color */
    button[kind="secondary"] {
        border-color: #8B0000;
        color: #8B0000;
    }
    button[kind="secondary"]:hover {
        background-color: #8B0000;
        color: white !important;
    }
    
    /* Tabs Design */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #fff;
        border-radius: 5px;
        padding: 10px 20px;
        box-shadow: 0px 1px 3px rgba(0,0,0,0.1);
    }
    .stTabs [aria-selected="true"] {
        background-color: #8B0000 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. SETUP DATABASE ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    SHEET_URL = st.secrets["gcp_sheet_url"] 
except Exception as e:
    st.error(f"⚠️ Connection Error: {e}")
    st.stop()

# --- 2. PROFESSIONAL REPORT ENGINES ---

def generate_excel(df):
    output = io.BytesIO()
    # Add the download timestamp to the filename logic later
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Warbixin')
            worksheet = writer.sheets['Warbixin']
            # Auto-adjust column width
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(str(col))) + 2
                col_letter = chr(65 + i)
                worksheet.column_dimensions[col_letter].width = max_len
    except:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
    output.seek(0)
    return output

def generate_pdf(df):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # --- COLORS ---
    brand_red = colors.HexColor("#8B0000") 
    brand_dark = colors.HexColor("#1A1A1A")
    light_grey = colors.HexColor("#F0F0F0")
    
    # --- HEADER DESIGN ---
    # Top Banner
    c.setFillColor(brand_red)
    c.rect(0, height-110, width, 110, fill=1, stroke=0)
    
    # Title
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 28)
    c.drawString(30, height-50, "MAREERO SYSTEM")
    
    c.setFont("Helvetica", 12)
    c.drawString(30, height-70, "General Trading & Spare Parts")
    
    # Report Info (Right Side)
    current_time = get_local_time()
    report_id = f"RPT-{current_time.strftime('%Y%m%d')}-{random.randint(100,999)}"
    
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(width-30, height-40, "DAILY OPERATION REPORT")
    c.setFont("Helvetica", 10)
    c.drawRightString(width-30, height-55, f"Date: {current_time.strftime('%d-%b-%Y')}")
    c.drawRightString(width-30, height-70, f"Time: {current_time.strftime('%I:%M %p')}")
    c.drawRightString(width-30, height-85, f"ID: {report_id}")

    # --- SUMMARY METRICS SECTION ---
    y_summary = height - 150
    c.setFillColor(brand_dark)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(30, y_summary, "1. EXECUTIVE SUMMARY (Koobitaan)")
    
    total = len(df)
    missing = len(df[df['Category'] == 'Maqan']) if not df.empty else 0
    requests = len(df[df['Category'] == 'Dadweynaha']) if not df.empty else 0 # Corrected mapping
    
    # Draw 3 Boxes
    box_w = 170
    box_h = 50
    gap = 15
    start_x = 30
    
    metrics = [("Total Entries", str(total)), ("Items Missing", str(missing)), ("New Requests", str(requests))]
    
    for i, (label, value) in enumerate(metrics):
        x = start_x + (i * (box_w + gap))
        # Box background
        c.setFillColor(colors.white)
        c.setStrokeColor(colors.lightgrey)
        c.roundRect(x, y_summary-60, box_w, box_h, 8, fill=1, stroke=1)
        # Text
        c.setFillColor(brand_red)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(x + box_w/2, y_summary-35, value)
        c.setFillColor(colors.grey)
        c.setFont("Helvetica", 10)
        c.drawCentredString(x + box_w/2, y_summary-50, label)

    # --- DATA TABLE SECTION ---
    y_table = y_summary - 100
    c.setFillColor(brand_dark)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(30, y_table, "2. DETAILED LIST (Liiska Faahfaahsan)")
    
    # Table Header Settings
    y_curr = y_table - 30
    col_widths = [80, 160, 80, 80, 140] # Category, Item, Branch, Employee, Note
    headers = ["CATEGORY", "ITEM NAME", "BRANCH", "STAFF", "NOTE"]
    
    # Draw Header Row
    c.setFillColor(brand_red)
    c.rect(30, y_curr-5, sum(col_widths), 20, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    
    x_pos = 35
    for i, h in enumerate(headers):
        c.drawString(x_pos, y_curr+2, h)
        x_pos += col_widths[i]
        
    y_curr -= 20
    
    # Draw Data Rows
    c.setFont("Helvetica", 9)
    row_count = 0
    
    if not df.empty:
        # Sort to show 'Maqan' first for priority
        if 'Category' in df.columns:
            df['sort_val'] = df['Category'].apply(lambda x: 0 if x == 'Maqan' else 1)
            df = df.sort_values('sort_val').drop(columns=['sort_val'])
            
        for _, row in df.iterrows():
            # Alternating background color
            if row_count % 2 == 0:
                c.setFillColor(light_grey)
                c.rect(30, y_curr-5, sum(col_widths), 15, fill=1, stroke=0)
            
            # Check for critical items to highlight text
            is_critical = row.get('Category', '') == 'Maqan'
            c.setFillColor(brand_red if is_critical else colors.black)
            
            x_pos = 35
            vals = [
                str(row.get('Category', ''))[:15],
                str(row.get('Item', ''))[:28],
                str(row.get('Branch', '')).replace("Branch", "Br."),
                str(row.get('Employee', ''))[:12],
                str(row.get('Note', ''))[:25]
            ]
            
            for i, val in enumerate(vals):
                c.drawString(x_pos, y_curr, val)
                x_pos += col_widths[i]
            
            y_curr -= 18
            row_count += 1
            
            # Page Break if full
            if y_curr < 120:
                c.showPage()
                y_curr = height - 50

    # --- FOOTER & SIGNATURE ---
    # Only draw signature on the last page or if there is space
    if y_curr < 120:
        c.showPage()
        y_curr = height - 100
        
    y_sig = 80
    c.setStrokeColor(colors.black)
    c.line(40, y_sig, 200, y_sig)
    c.line(350, y_sig, 510, y_sig)
    
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    c.drawString(40, y_sig-15, "Manager Signature")
    c.drawString(350, y_sig-15, "Date & Stamp")
    
    # Bottom Strip
    c.setFillColor(light_grey)
    c.rect(0, 0, width, 30, fill=1, stroke=0)
    c.setFillColor(colors.grey)
    c.setFont("Helvetica", 8)
    c.drawCentredString(width/2, 10, f"Generated by Mareero System | {current_time.strftime('%Y-%m-%d')}")

    c.save()
    buffer.seek(0)
    return buffer

# --- 3. THE APP UI ---
# Banner
st.markdown("<h1 style='text-align: center; color: #8B0000;'>🏢 Mareero General Trading LLC</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; color: gray;'>System Date: {get_local_time().strftime('%d %B %Y | %I:%M %p')}</p>", unsafe_allow_html=True)

# Tabs
tab_staff, tab_manager = st.tabs(["📝 SHAQAALAHA (Staff)", "🔐 MAAMULKA (Manager)"])

# --- STAFF TAB ---
with tab_staff:
    st.markdown("### 📋 Diiwaangelinta Maalinlaha (Daily Entry)")
    
    with st.container(border=True):
        with st.form("log_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                branch_options = ["Head Q", "Branch 1", "Branch 3", "Branch 4", "Branch 5" , "Kaydka M.hassan"]
                branch = st.selectbox("📍 Xulo Laanta (Select Branch)", branch_options)
                employee = st.text_input("👤 Magacaaga (Your Name)")
            
            with col2:
                # Kept your exact mapping logic
                cat_map = {
                    "alaabta Maqan (Missing)": "Maqan",
                    "alaabta Suqqa leh (High Demand)": "Suuq leh",
                    "bahiyaha Dadweynaha (New Request)": "Dadweynaha"
                }
                category_selection = st.selectbox("📂 Nooca Warbixinta (Type)", list(cat_map.keys()))
                item = st.text_input("📦 Magaca Alaabta (Item Name)")
            
            note = st.text_input("📝 Faahfaahin / Tirada (Note/Qty)")
            
            st.write("")
            submit_btn = st.form_submit_button("🚀 GUDBI (SUBMIT REPORT)", use_container_width=True)
            
            if submit_btn:
                if employee and item:
                    try:
                        data = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=0)
                        if data is None: data = pd.DataFrame()
                        data = data.dropna(how="all")
                        
                        real_category = cat_map[category_selection]
                        # Use Local Time for the database entry too
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
                        conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=updated)
                        st.cache_data.clear()
                        st.success(f"✅ Waa la gudbiyay! {current_local_time}")
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("⚠️ Fadlan buuxi Magacaaga iyo Alaabta.")

# --- MANAGER TAB ---
with tab_manager:
    st.markdown("### 🔐 Maamulka (Admin Panel)")
    
    # Styled Login
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        c_pass, c_btn = st.columns([4, 1], vertical_alignment="bottom")
        with c_pass:
            password = st.text_input("🔒 Geli Furaha (Password)", type="password", placeholder="******")
        with c_btn:
            if st.button("Login ➡️", type="primary"):
                if password == "mareero2025":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Wrong Password")
    
    # LOGGED IN VIEW
    if st.session_state.logged_in:
        if st.button("🔓 Logout", type="secondary"):
            st.session_state.logged_in = False
            st.rerun()
            
        # Load Data
        try:
            df = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=0)
            if df is None: df = pd.DataFrame()
            df = df.dropna(how="all")
        except:
            df = pd.DataFrame()

        if not df.empty:
            # DASHBOARD METRICS
            st.markdown("---")
            m1, m2, m3, m4 = st.columns(4)
            
            count_total = len(df)
            count_missing = len(df[df['Category'] == 'Maqan']) if 'Category' in df.columns else 0
            count_new = len(df[df['Category'] == 'Dadweynaha']) if 'Category' in df.columns else 0
            
            # Dynamic greeting based on time
            hour = get_local_time().hour
            greeting = "Good Morning" if hour < 12 else "Good Afternoon"
            
            m1.metric("Status", "Active 🟢")
            m2.metric("Total Reports", count_total)
            m3.metric("⚠️ Missing Items", count_missing, delta_color="inverse")
            m4.metric("📢 New Requests", count_new)
            
            st.markdown("---")
            
            # REPORT GENERATION SECTION
            st.subheader("📄 Report Generation Center")
            
            c_pdf, c_xls = st.columns(2)
            with c_pdf:
                st.download_button(
                    label="📥 Download Professional PDF",
                    data=generate_pdf(df),
                    file_name=f"Mareero_Report_{get_local_time().strftime('%Y-%m-%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            with c_xls:
                st.download_button(
                    label="📥 Download Excel Data",
                    data=generate_excel(df),
                    file_name=f"Mareero_Data_{get_local_time().strftime('%Y-%m-%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            st.markdown("---")

            # EDIT/DELETE SECTION
            with st.expander("🛠️ Manage Data (Edit / Delete Rows)", expanded=False):
                df_with_delete = df.copy()
                df_with_delete.insert(0, "Select", False)

                edited_df = st.data_editor(
                    df_with_delete,
                    num_rows="fixed",
                    hide_index=True,
                    use_container_width=True,
                    key="data_editor",
                    column_config={
                        "Select": st.column_config.CheckboxColumn("❌", width="small")
                    }
                )
                
                col_save, col_del = st.columns([1,1])
                with col_save:
                    if st.button("💾 Save Changes", use_container_width=True):
                        try:
                            final_df = edited_df.drop(columns=["Select"])
                            conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=final_df)
                            st.cache_data.clear()
                            st.success("Data Updated!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                
                with col_del:
                    if st.button("🗑️ Delete Selected", type="primary", use_container_width=True):
                        try:
                            rows_to_keep = edited_df[edited_df["Select"] == False]
                            final_df = rows_to_keep.drop(columns=["Select"])
                            conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=final_df)
                            st.cache_data.clear()
                            st.success("Rows Deleted!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
        else:
            st.info("No data available yet.")
