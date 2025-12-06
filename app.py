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
matplotlib.use('Agg') # Prevent server crash
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

# --- SET TIMEZONE (SOMALIA/EAST AFRICA) ---
def get_local_time():
    tz = pytz.timezone('Africa/Mogadishu') 
    return datetime.now(tz)

# --- CSS: DARK MODE FRIENDLY & RESPONSIVE ---
st.markdown("""
<style>
    /* Global Text & Background Fixes */
    .block-container { padding-top: 1rem; padding-bottom: 3rem; }
    
    /* Hide Streamlit Default Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* METRIC CARDS (Dark Mode Compatible) */
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.05); /* Transparent White */
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 10px;
        border-radius: 10px;
        text-align: center;
    }
    
    /* TABS DESIGN (Fixed for Mobile Dark Mode) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: rgba(255, 255, 255, 0.05); /* Dark Transparent */
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 5px;
        color: #e0e0e0; /* Light Text */
        font-weight: 600;
    }
    
    /* Selected Tab - Brand Red */
    .stTabs [aria-selected="true"] {
        background-color: #8B0000 !important;
        color: white !important;
        border: 1px solid #8B0000;
    }

    /* INPUT FIELDS */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: white !important;
        border: 1px solid #444 !important;
    }

    /* BUTTONS */
    div[data-testid="stButton"] button {
        border-radius: 8px;
        font-weight: bold;
        transition: 0.3s;
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
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Warbixin')
            worksheet = writer.sheets['Warbixin']
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
    
    # COLORS
    brand_red = colors.HexColor("#8B0000") 
    brand_dark = colors.HexColor("#1A1A1A")
    light_grey = colors.HexColor("#F0F0F0")
    
    # --- HEADER ---
    c.setFillColor(brand_red)
    c.rect(0, height-110, width, 110, fill=1, stroke=0)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 28)
    c.drawString(30, height-50, "MAREERO SYSTEM")
    c.setFont("Helvetica", 12)
    c.drawString(30, height-70, "General Trading & Spare Parts")
    
    current_time = get_local_time()
    report_id = f"RPT-{current_time.strftime('%Y%m%d')}-{random.randint(100,999)}"
    
    c.drawRightString(width-30, height-40, "DAILY REPORT")
    c.setFont("Helvetica", 10)
    c.drawRightString(width-30, height-55, f"Date: {current_time.strftime('%d-%b-%Y')}")
    c.drawRightString(width-30, height-70, f"Time: {current_time.strftime('%I:%M %p')}")
    c.drawRightString(width-30, height-85, f"ID: {report_id}")

    # --- METRICS ---
    y_pos = height - 150
    c.setFillColor(brand_dark)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(30, y_pos, "1. EXECUTIVE SUMMARY")
    
    total = len(df)
    missing = len(df[df['Category'] == 'Maqan']) if not df.empty else 0
    requests = len(df[df['Category'] == 'Dadweynaha']) if not df.empty else 0
    
    metrics = [("Total Entries", str(total)), ("Missing Items", str(missing)), ("Requests", str(requests))]
    box_w, box_h, gap = 170, 50, 15
    start_x = 30
    
    for i, (label, value) in enumerate(metrics):
        x = start_x + (i * (box_w + gap))
        c.setFillColor(colors.white)
        c.setStrokeColor(colors.lightgrey)
        c.roundRect(x, y_pos-60, box_w, box_h, 8, fill=1, stroke=1)
        c.setFillColor(brand_red)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(x + box_w/2, y_pos-35, value)
        c.setFillColor(colors.grey)
        c.setFont("Helvetica", 10)
        c.drawCentredString(x + box_w/2, y_pos-50, label)

    # --- CHARTS SECTION (Added Back) ---
    y_pos -= 80
    c.setFillColor(brand_dark)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(30, y_pos, "2. DATA VISUALIZATION")
    
    if not df.empty:
        try:
            # Pie Chart (Categories)
            fig1, ax1 = plt.subplots(figsize=(4, 3))
            cat_counts = df['Category'].value_counts()
            ax1.pie(cat_counts, labels=cat_counts.index, autopct='%1.0f%%', startangle=90, colors=['#8B0000', '#2F4F4F', '#A9A9A9'])
            ax1.set_title("Categories", fontsize=10)
            
            img1 = io.BytesIO()
            plt.savefig(img1, format='png', bbox_inches='tight', transparent=True)
            img1.seek(0)
            c.drawImage(ImageReader(img1), 30, y_pos-220, width=240, height=180)
            plt.close(fig1)

            # Bar Chart (Branches)
            fig2, ax2 = plt.subplots(figsize=(4, 3))
            branch_counts = df['Branch'].value_counts()
            branch_counts.plot(kind='bar', color='#8B0000', ax=ax2)
            ax2.set_title("Activity by Branch", fontsize=10)
            plt.xticks(rotation=45, ha='right', fontsize=8)
            
            img2 = io.BytesIO()
            plt.savefig(img2, format='png', bbox_inches='tight', transparent=True)
            img2.seek(0)
            c.drawImage(ImageReader(img2), 300, y_pos-220, width=240, height=180)
            plt.close(fig2)
            
        except Exception as e:
            c.drawString(30, y_pos-30, "Charts unavailable.")
    
    # --- TABLE SECTION ---
    y_pos -= 240
    c.setFillColor(brand_dark)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(30, y_pos, "3. DETAILED INVENTORY LIST")
    
    # Header
    y_curr = y_pos - 30
    col_widths = [80, 160, 80, 80, 140]
    headers = ["CATEGORY", "ITEM NAME", "BRANCH", "STAFF", "NOTE"]
    
    c.setFillColor(brand_red)
    c.rect(30, y_curr-5, sum(col_widths), 20, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    
    x_pos = 35
    for i, h in enumerate(headers):
        c.drawString(x_pos, y_curr+2, h)
        x_pos += col_widths[i]
        
    y_curr -= 20
    
    # Rows
    c.setFont("Helvetica", 9)
    row_count = 0
    
    if not df.empty:
        # SORTING: Sort by Item Name so same items appear together
        if 'Item' in df.columns:
            df = df.sort_values(by=['Item', 'Category'])
            
        for _, row in df.iterrows():
            if row_count % 2 == 0:
                c.setFillColor(light_grey)
                c.rect(30, y_curr-5, sum(col_widths), 15, fill=1, stroke=0)
            
            # HIGHLIGHT LOGIC: Red for "Maqan"
            is_missing = row.get('Category', '') == 'Maqan'
            c.setFillColor(brand_red if is_missing else colors.black)
            
            # Data
            vals = [
                str(row.get('Category', ''))[:15],
                str(row.get('Item', ''))[:28], # Item Name
                str(row.get('Branch', '')).replace("Branch", "Br."),
                str(row.get('Employee', ''))[:12],
                str(row.get('Note', ''))[:25]
            ]
            
            x_pos = 35
            for i, val in enumerate(vals):
                c.drawString(x_pos, y_curr, val)
                x_pos += col_widths[i]
            
            y_curr -= 18
            row_count += 1
            
            if y_curr < 50:
                c.showPage()
                y_curr = height - 50

    # Signature
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
    
    c.save()
    buffer.seek(0)
    return buffer

# --- 3. APP UI ---
st.markdown("<h1 style='text-align: center; color: #8B0000;'>🏢 Mareero General Trading LLC</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; color: gray;'>System Date: {get_local_time().strftime('%d %B %Y | %I:%M %p')}</p>", unsafe_allow_html=True)

# TABS
tab_staff, tab_manager = st.tabs(["📝 SHAQAALAHA (Staff)", "🔐 MAAMULKA (Manager)"])

# --- STAFF TAB ---
with tab_staff:
    st.info("Fadlan halkan ku diiwaangeli warbixintaada maalinlaha ah.")
    
    with st.form("log_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            branch_options = ["Head Q", "Branch 1", "Branch 3", "Branch 4", "Branch 5" , "Kaydka M.hassan"]
            branch = st.selectbox("📍 Xulo Laanta (Select Branch)", branch_options)
            employee = st.text_input("👤 Magacaaga (Your Name)")
        with col2:
            cat_map = {
                "alaabta Maqan (Missing)": "Maqan",
                "alaabta Suqqa leh (High Demand)": "Suuq leh",
                "bahiyaha Dadweynaha (New Request)": "Dadweynaha"
            }
            category_selection = st.selectbox("📂 Nooca Warbixinta (Type)", list(cat_map.keys()))
            item = st.text_input("📦 Magaca Alaabta (Item Name)")
        
        note = st.text_input("📝 Faahfaahin / Tirada (Note/Qty)")
        
        # Spacer
        st.write("")
        submit_btn = st.form_submit_button("🚀 GUDBI (SUBMIT)", use_container_width=True)
        
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
    # LOGIN
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
    
    # DASHBOARD
    if st.session_state.logged_in:
        c_head, c_logout = st.columns([4,1])
        with c_head:
            st.subheader("📊 Maamulka Dashboard")
        with c_logout:
            if st.button("🔓 Logout"):
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
            
            m1.metric("Total", count_total)
            m2.metric("Missing", count_missing, delta_color="inverse")
            m3.metric("Requests", count_new)
            m4.metric("Branches", df['Branch'].nunique() if 'Branch' in df.columns else 0)
            
            st.markdown("---")
            
            # REPORTS
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    label="📥 Download PDF Report (With Charts)",
                    data=generate_pdf(df),
                    file_name=f"Mareero_Report_{get_local_time().strftime('%Y-%m-%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            with c2:
                st.download_button(
                    label="📥 Download Excel Data",
                    data=generate_excel(df),
                    file_name=f"Mareero_Data_{get_local_time().strftime('%Y-%m-%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            st.markdown("---")

            # EDIT TABLE
            with st.expander("🛠️ Manage Data (Edit / Delete Rows)", expanded=False):
                df_with_delete = df.copy()
                df_with_delete.insert(0, "Select", False)

                edited_df = st.data_editor(
                    df_with_delete,
                    num_rows="fixed",
                    hide_index=True,
                    use_container_width=True,
                    key="data_editor",
                    column_config={"Select": st.column_config.CheckboxColumn("❌", width="small")}
                )
                
                col_save, col_del = st.columns([1,1])
                with col_save:
                    if st.button("💾 Save Changes", use_container_width=True):
                        try:
                            final_df = edited_df.drop(columns=["Select"])
                            conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=final_df)
                            st.cache_data.clear()
                            st.success("Updated!")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                with col_del:
                    if st.button("🗑️ Delete Selected", type="primary", use_container_width=True):
                        try:
                            rows_to_keep = edited_df[edited_df["Select"] == False]
                            final_df = rows_to_keep.drop(columns=["Select"])
                            conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=final_df)
                            st.cache_data.clear()
                            st.success("Deleted!")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
        else:
            st.info("No data found.")
