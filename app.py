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
import pytz 
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
import io
import random

# --- SET TIMEZONE ---
def get_local_time():
    tz = pytz.timezone('Africa/Mogadishu') 
    return datetime.now(tz)

# --- CSS: PROFESSIONAL CORPORATE THEME (BLUE & SLATE) ---
st.markdown("""
<style>
    /* MAIN CONTAINER */
    .block-container { padding-top: 1.5rem; padding-bottom: 3rem; }
    
    /* HIDE STREAMLIT UI */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* CARDS & METRICS (Glassmorphism Slate) */
    div[data-testid="stMetric"], div[data-testid="stForm"] {
        background-color: #1e293b; /* Slate 800 */
        border: 1px solid #334155; /* Slate 700 */
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    div[data-testid="stMetricLabel"] { color: #94a3b8 !important; } /* Slate 400 */
    div[data-testid="stMetricValue"] { color: #f8fafc !important; } /* Slate 50 */
    
    /* TABS DESIGN (Professional Blue) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #0f172a; /* Slate 900 */
        border: 1px solid #334155;
        border-radius: 6px;
        color: #cbd5e1;
        font-weight: 500;
    }
    
    /* Selected Tab */
    .stTabs [aria-selected="true"] {
        background-color: #2563eb !important; /* Corporate Blue */
        color: white !important;
        border: 1px solid #2563eb;
    }

    /* INPUT FIELDS */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #0f172a !important; /* Darker Input Background */
        color: white !important;
        border: 1px solid #475569 !important;
    }

    /* BUTTONS */
    div[data-testid="stButton"] button {
        border-radius: 6px;
        font-weight: 600;
        border: none;
    }
    
    /* Primary Action Buttons */
    button[kind="secondary"] {
        background-color: #3b82f6;
        color: white;
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

def clean_text(text):
    """Removes NaN and converts to string"""
    if pd.isna(text) or str(text).lower() == 'nan':
        return "-"
    return str(text)

def generate_excel(df):
    output = io.BytesIO()
    # Clean data before export
    df_export = df.fillna("-")
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Warbixin')
            worksheet = writer.sheets['Warbixin']
            for i, col in enumerate(df_export.columns):
                max_len = max(df_export[col].astype(str).map(len).max(), len(str(col))) + 2
                col_letter = chr(65 + i)
                worksheet.column_dimensions[col_letter].width = max_len
    except:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, index=False)
    output.seek(0)
    return output

def generate_pdf(df):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # --- NEW PROFESSIONAL COLOR PALETTE ---
    brand_primary = colors.HexColor("#0f172a") # Slate 900 (Dark Navy)
    brand_accent  = colors.HexColor("#2563eb") # Corporate Blue
    text_dark     = colors.HexColor("#334155") # Slate 700
    row_even      = colors.HexColor("#f1f5f9") # Very light slate
    
    # --- HEADER ---
    c.setFillColor(brand_primary)
    c.rect(0, height-110, width, 110, fill=1, stroke=0)
    
    # Logo Area / Title
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(40, height-50, "MAREERO SYSTEM")
    c.setFont("Helvetica", 12)
    c.setFillColor(colors.HexColor("#94a3b8")) # Lighter text
    c.drawString(40, height-70, "General Trading & Spare Parts LLC")
    
    # Report Meta Data
    current_time = get_local_time()
    report_id = f"REF-{current_time.strftime('%Y%m%d')}-{random.randint(100,999)}"
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(width-40, height-40, "OPERATIONAL REPORT")
    c.setFont("Helvetica", 10)
    c.drawRightString(width-40, height-55, f"Date: {current_time.strftime('%d %b %Y')}")
    c.drawRightString(width-40, height-70, f"Time: {current_time.strftime('%I:%M %p')}")
    c.drawRightString(width-40, height-85, f"ID: {report_id}")

    # --- METRICS SECTION ---
    y_pos = height - 150
    c.setFillColor(brand_primary)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y_pos, "1. EXECUTIVE SUMMARY")
    
    total = len(df)
    missing = len(df[df['Category'] == 'Maqan']) if not df.empty else 0
    requests = len(df[df['Category'] == 'Dadweynaha']) if not df.empty else 0
    
    metrics = [("Total Reports", str(total)), ("Missing Stock", str(missing)), ("New Requests", str(requests))]
    box_w, box_h, gap = 160, 50, 15
    start_x = 40
    
    for i, (label, value) in enumerate(metrics):
        x = start_x + (i * (box_w + gap))
        # Box shadow effect (simulated with offset gray rect)
        c.setFillColor(colors.lightgrey)
        c.roundRect(x+2, y_pos-62, box_w, box_h, 6, fill=1, stroke=0)
        # Main box
        c.setFillColor(colors.white)
        c.setStrokeColor(colors.lightgrey)
        c.roundRect(x, y_pos-60, box_w, box_h, 6, fill=1, stroke=1)
        
        c.setFillColor(brand_accent)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(x + box_w/2, y_pos-35, value)
        
        c.setFillColor(text_dark)
        c.setFont("Helvetica", 9)
        c.drawCentredString(x + box_w/2, y_pos-50, label)

    # --- CHARTS SECTION ---
    y_pos -= 80
    c.setFillColor(brand_primary)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y_pos, "2. VISUAL ANALYTICS")
    
    if not df.empty:
        try:
            # Pie Chart
            fig1, ax1 = plt.subplots(figsize=(4, 3))
            cat_counts = df['Category'].value_counts()
            # Professional Blue/Slate colors for chart
            ax1.pie(cat_counts, labels=cat_counts.index, autopct='%1.0f%%', startangle=90, colors=['#2563eb', '#64748b', '#94a3b8'])
            
            img1 = io.BytesIO()
            plt.savefig(img1, format='png', bbox_inches='tight', transparent=True)
            img1.seek(0)
            c.drawImage(ImageReader(img1), 40, y_pos-220, width=220, height=165)
            plt.close(fig1)

            # Bar Chart
            fig2, ax2 = plt.subplots(figsize=(4, 3))
            branch_counts = df['Branch'].value_counts()
            branch_counts.plot(kind='bar', color='#0f172a', ax=ax2) # Dark navy bars
            plt.xticks(rotation=45, ha='right', fontsize=8)
            ax2.spines['top'].set_visible(False)
            ax2.spines['right'].set_visible(False)
            
            img2 = io.BytesIO()
            plt.savefig(img2, format='png', bbox_inches='tight', transparent=True)
            img2.seek(0)
            c.drawImage(ImageReader(img2), 300, y_pos-220, width=240, height=180)
            plt.close(fig2)
            
        except Exception:
            c.drawString(40, y_pos-30, "No visual data available.")
    
    # --- TABLE SECTION ---
    y_pos -= 240
    c.setFillColor(brand_primary)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y_pos, "3. INVENTORY DETAILS")
    
    # Header Settings
    y_curr = y_pos - 30
    # ADJUSTED COLUMN WIDTHS TO FIX OVERLAP:
    # Page Width ~595. Margins ~80. Content ~515.
    # Cat(70) + Item(140) + Branch(100) + Staff(90) + Note(115) = 515
    col_widths = [70, 140, 100, 90, 115] 
    headers = ["TYPE", "ITEM NAME", "BRANCH", "STAFF", "NOTES"]
    
    # Draw Header
    c.setFillColor(brand_primary)
    c.rect(40, y_curr-6, sum(col_widths), 22, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    
    x_pos = 45
    for i, h in enumerate(headers):
        c.drawString(x_pos, y_curr+2, h)
        x_pos += col_widths[i]
        
    y_curr -= 22
    
    # Draw Rows
    c.setFont("Helvetica", 9)
    row_count = 0
    
    if not df.empty:
        # Sort logic
        if 'Item' in df.columns:
            df = df.sort_values(by=['Category', 'Item'])
            
        for _, row in df.iterrows():
            if row_count % 2 == 0:
                c.setFillColor(row_even)
                c.rect(40, y_curr-6, sum(col_widths), 18, fill=1, stroke=0)
            
            # Text Color Logic
            category = clean_text(row.get('Category', ''))
            is_missing = category == 'Maqan'
            
            # Set Text Color
            c.setFillColor(colors.red if is_missing else text_dark)
            
            # Prepare Data & Clean NaN
            vals = [
                category[:12],
                clean_text(row.get('Item', ''))[:24],   # Item Name
                clean_text(row.get('Branch', '')).replace("Branch", "Br."), # Shorten Branch
                clean_text(row.get('Employee', ''))[:14],
                clean_text(row.get('Note', ''))[:20]
            ]
            
            x_pos = 45
            for i, val in enumerate(vals):
                c.drawString(x_pos, y_curr, val)
                x_pos += col_widths[i]
            
            y_curr -= 18
            row_count += 1
            
            if y_curr < 60:
                c.showPage()
                y_curr = height - 50

    # Signature Area
    if y_curr < 120:
        c.showPage()
        y_curr = height - 100
        
    y_sig = 80
    c.setStrokeColor(colors.grey)
    c.setLineWidth(1)
    c.line(40, y_sig, 200, y_sig)
    c.line(350, y_sig, 510, y_sig)
    
    c.setFillColor(text_dark)
    c.setFont("Helvetica", 9)
    c.drawString(40, y_sig-15, "Authorized Manager")
    c.drawString(350, y_sig-15, "Date & Official Stamp")
    
    c.save()
    buffer.seek(0)
    return buffer

# --- 3. APP UI ---

# Banner
st.markdown("""
<div style="text-align: center; margin-bottom: 20px;">
    <h1 style='color: #2563eb; margin-bottom: 0;'>MAREERO SYSTEM</h1>
    <p style='color: #64748b; font-size: 0.9em;'>General Trading & Spare Parts LLC</p>
</div>
""", unsafe_allow_html=True)

# Tabs
tab_staff, tab_manager = st.tabs(["📝 SHAQAALAHA (Staff)", "🔐 MAAMULKA (Manager)"])

# --- STAFF TAB ---
with tab_staff:
    st.info("👋 Fadlan halkan ku diiwaangeli warbixintaada maalinlaha ah.")
    
    with st.form("log_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            branch_options = ["Head Q", "Branch 1", "Branch 3", "Branch 4", "Branch 5" , "Kaydka M.hassan"]
            branch = st.selectbox("📍 Branch / Laanta", branch_options)
            employee = st.text_input("👤 Your Name / Magacaaga")
        with col2:
            cat_map = {
                "alaabta Maqan (Missing)": "Maqan",
                "alaabta Suqqa leh (High Demand)": "Suuq leh",
                "bahiyaha Dadweynaha (New Request)": "Dadweynaha"
            }
            category_selection = st.selectbox("📂 Report Type / Nooca", list(cat_map.keys()))
            item = st.text_input("📦 Item Name / Alaabta")
        
        note = st.text_input("📝 Notes / Faahfaahin (Optional)")
        
        st.write("")
        submit_btn = st.form_submit_button("Submit Report 🚀", use_container_width=True)
        
        if submit_btn:
            if employee and item:
                try:
                    data = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=0)
                    if data is None: data = pd.DataFrame()
                    data = data.dropna(how="all")
                    
                    real_category = cat_map[category_selection]
                    current_local_time = get_local_time().strftime("%Y-%m-%d %H:%M")
                    
                    new_row = pd.DataFrame([{
                        "Date": current_local_time,
                        "Branch": branch,
                        "Employee": employee,
                        "Category": real_category,
                        "Item": item,
                        "Note": note if note else "-"
                    }])
                    
                    updated = pd.concat([data, new_row], ignore_index=True)
                    conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=updated)
                    st.cache_data.clear()
                    st.success(f"✅ Success! Entry logged at {current_local_time}")
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("⚠️ Please fill in Name and Item.")

# --- MANAGER TAB ---
with tab_manager:
    # LOGIN
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        c_pass, c_btn = st.columns([4, 1], vertical_alignment="bottom")
        with c_pass:
            password = st.text_input("🔑 Password", type="password", placeholder="Enter admin password")
        with c_btn:
            if st.button("Login", type="primary"):
                if password == "mareero2025":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Incorrect Password")
    
    # DASHBOARD
    if st.session_state.logged_in:
        c_head, c_logout = st.columns([4,1])
        with c_head:
            st.write(f"**System Time:** {get_local_time().strftime('%I:%M %p')}")
        with c_logout:
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.rerun()
            
        try:
            df = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=0)
            if df is None: df = pd.DataFrame()
            df = df.dropna(how="all")
        except:
            df = pd.DataFrame()

        if not df.empty:
            st.markdown("---")
            m1, m2, m3, m4 = st.columns(4)
            
            count_total = len(df)
            count_missing = len(df[df['Category'] == 'Maqan']) if 'Category' in df.columns else 0
            count_new = len(df[df['Category'] == 'Dadweynaha']) if 'Category' in df.columns else 0
            
            m1.metric("Total Entries", count_total)
            m2.metric("Missing Items", count_missing, delta_color="inverse")
            m3.metric("New Requests", count_new)
            m4.metric("Active Branches", df['Branch'].nunique() if 'Branch' in df.columns else 0)
            
            st.markdown("---")
            
            # REPORTS
            st.subheader("📄 Generate Reports")
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    label="📥 Download PDF Report",
                    data=generate_pdf(df),
                    file_name=f"Mareero_Report_{get_local_time().strftime('%Y-%m-%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            with c2:
                st.download_button(
                    label="📥 Download Excel File",
                    data=generate_excel(df),
                    file_name=f"Mareero_Data_{get_local_time().strftime('%Y-%m-%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            st.markdown("---")

            # EDIT TABLE
            with st.expander("🛠️ Manage Database (Edit / Delete)", expanded=False):
                df_with_delete = df.copy()
                df_with_delete.insert(0, "Select", False)

                edited_df = st.data_editor(
                    df_with_delete,
                    num_rows="fixed",
                    hide_index=True,
                    use_container_width=True,
                    key="data_editor",
                    column_config={"Select": st.column_config.CheckboxColumn("Del", width="small")}
                )
                
                col_save, col_del = st.columns([1,1])
                with col_save:
                    if st.button("💾 Save Changes", use_container_width=True):
                        try:
                            final_df = edited_df.drop(columns=["Select"])
                            conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=final_df)
                            st.cache_data.clear()
                            st.success("Database Updated!")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                with col_del:
                    if st.button("🗑️ Delete Selected Rows", type="primary", use_container_width=True):
                        try:
                            rows_to_keep = edited_df[edited_df["Select"] == False]
                            final_df = rows_to_keep.drop(columns=["Select"])
                            conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=final_df)
                            st.cache_data.clear()
                            st.success("Rows Deleted Successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
        else:
            st.info("Database is empty.")
