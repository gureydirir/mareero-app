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
import pytz # NEW: For Real Time
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
import io
import random

# --- 1. SETUP TIMEZONE (Somalia) ---
def get_local_time():
    tz = pytz.timezone('Africa/Mogadishu') 
    return datetime.now(tz)

# --- 2. CSS: PROFESSIONAL DESIGN ---
st.markdown("""
<style>
    /* Main Background & Fonts */
    .block-container { padding-top: 1.5rem; padding-bottom: 5rem; }
    
    /* Hide Default Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* CARD DESIGN FOR METRICS */
    div[data-testid="stMetric"] {
        background-color: #ffffff; /* White Card */
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        color: black;
    }
    
    /* TABS DESIGN */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f8f9fa;
        border-radius: 5px;
        font-weight: 600;
        color: #555;
    }
    .stTabs [aria-selected="true"] {
        background-color: #8B0000 !important; /* Mareero Red */
        color: white !important;
    }

    /* INPUT FIELDS */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        border-radius: 5px;
    }

    /* BUTTONS */
    div[data-testid="stButton"] button {
        border-radius: 5px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. DATABASE ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    SHEET_URL = st.secrets["gcp_sheet_url"] 
except Exception as e:
    st.error(f"⚠️ Connection Error: {e}")
    st.stop()

# --- 4. ENGINES ---

def generate_excel(df):
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Warbixin')
            # Auto-Adjust Column Widths
            worksheet = writer.sheets['Warbixin']
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(str(col))) + 2
                col_letter = chr(65 + i)
                worksheet.column_dimensions[col_letter].width = max_len
    except Exception as e:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
    output.seek(0)
    return output

def generate_pdf(df):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # COLORS
    primary_color = colors.HexColor("#8B0000") # Dark Red
    text_color = colors.HexColor("#2C3E50")    # Dark Blue/Grey
    light_grey = colors.HexColor("#F0F0F0")
    
    # --- HEADER ---
    c.setFillColor(primary_color)
    c.rect(0, height-110, width, 110, fill=1, stroke=0)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(40, height-50, "MAREERO SYSTEM")
    c.setFont("Helvetica", 12)
    c.drawString(40, height-70, "General Trading & Spare Parts LLC")
    
    # Real Time & ID
    current_time = get_local_time()
    report_id = f"REF-{current_time.strftime('%Y%m%d')}-{random.randint(100,999)}"
    
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(width-40, height-40, "OPERATION REPORT")
    c.setFont("Helvetica", 10)
    c.drawRightString(width-40, height-55, f"Date: {current_time.strftime('%d %B %Y')}")
    c.drawRightString(width-40, height-70, f"Time: {current_time.strftime('%I:%M %p')}")
    c.drawRightString(width-40, height-85, f"ID: {report_id}")

    # --- SECTION 1: SUMMARY ---
    y_summary = height - 150
    c.setFillColor(text_color)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y_summary, "1. KOOBITAAN (SUMMARY):")
    
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.grey)
    c.drawString(40, y_summary-20, "Warbixinta guud ee maanta, alaabta maqan, iyo dalabyada cusub.")
    
    # Metrics
    total = len(df)
    missing = len(df[df['Category'] == 'Maqan']) if not df.empty else 0
    new_req = len(df[df['Category'] == 'Dadweynaha']) if not df.empty else 0
    
    # Draw Stylish Boxes
    box_w, box_h = 160, 50
    gap = 15
    start_x = 40
    
    metrics = [("Wadarta (Total)", str(total)), ("Maqan (Missing)", str(missing)), ("Dalab (Requests)", str(new_req))]
    
    for i, (label, value) in enumerate(metrics):
        x = start_x + (i * (box_w + gap))
        c.setStrokeColor(colors.lightgrey)
        c.roundRect(x, y_summary-80, box_w, box_h, 5, fill=0, stroke=1)
        
        c.setFillColor(primary_color)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(x + box_w/2, y_summary-55, value)
        
        c.setFillColor(text_color)
        c.setFont("Helvetica", 10)
        c.drawCentredString(x + box_w/2, y_summary-70, label)

    # --- SECTION 2: CHARTS ---
    y_chart = height - 320
    c.setFillColor(text_color)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y_chart, "2. SHAXDA XOGTA (CHARTS):")
    
    if not df.empty:
        try:
            plt.rcdefaults() # Reset style for PDF
            
            # Chart 1: Pie
            fig1, ax1 = plt.subplots(figsize=(4, 3))
            category_counts = df['Category'].value_counts()
            if not category_counts.empty:
                ax1.pie(category_counts, labels=category_counts.index, autopct='%1.0f%%', colors=['#8B0000', '#2F4F4F', '#A9A9A9'])
                ax1.set_title("Qeybaha", fontsize=10)
                
                img1 = io.BytesIO()
                plt.savefig(img1, format='png', bbox_inches='tight')
                plt.close(fig1)
                img1.seek(0)
                c.drawImage(ImageReader(img1), 40, y_chart-200, width=220, height=165)
            
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
                c.drawImage(ImageReader(img2), 300, y_chart-200, width=220, height=165)
        except Exception:
            c.drawString(40, y_chart-60, "Error generating charts.")

    # --- SECTION 3: CRITICAL LIST ---
    y_list = y_chart - 240
    c.setFillColor(text_color)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y_list, "3. ALAABTA MUHIIMKA AH (DETAILS):")
    
    # Header
    y_curr = y_list - 40
    col_widths = [80, 160, 80, 80, 115] 
    headers = ["CATEGORY", "ITEM NAME", "BRANCH", "STAFF", "NOTE"]
    
    c.setFillColor(primary_color)
    c.rect(40, y_curr-6, sum(col_widths), 22, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    
    x_pos = 45
    for i, h in enumerate(headers):
        c.drawString(x_pos, y_curr+2, h)
        x_pos += col_widths[i]
        
    y_curr -= 22
    c.setFont("Helvetica", 9)
    row_count = 0
    
    if not df.empty:
        # Sort by Item
        if 'Item' in df.columns:
            df = df.sort_values(by=['Item'])
            
        for _, row in df.iterrows():
            if row_count % 2 == 0:
                c.setFillColor(light_grey)
                c.rect(40, y_curr-6, sum(col_widths), 18, fill=1, stroke=0)
            
            # Professional Color Coding for PDF Text
            cat = str(row.get('Category', ''))
            if cat == 'Maqan':
                c.setFillColor(colors.red)
            elif cat == 'Dadweynaha':
                c.setFillColor(colors.blue)
            else:
                c.setFillColor(colors.black)
            
            vals = [
                cat[:12],
                str(row.get('Item', ''))[:25],
                str(row.get('Branch', '')).replace("Branch", "Br."),
                str(row.get('Employee', ''))[:14],
                str(row.get('Note', ''))[:20]
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

    c.save()
    buffer.seek(0)
    return buffer

# --- 5. THE APP UI ---
st.markdown("<h1 style='text-align: center; color: #8B0000;'>🏢 Mareero General Trading LLC</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; color: gray;'>Date: {get_local_time().strftime('%d %B %Y')}</p>", unsafe_allow_html=True)

# TABS
tab_staff, tab_manager = st.tabs(["📝 Qeybta Shaqaalaha (Staff)", "🔐 Maamulka (Manager)"])

# --- STAFF TAB ---
with tab_staff:
    st.info("Fadlan halkan ku diiwaangeli warbixintaada maalinlaha ah.")
    
    with st.form("log_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            branch_options = ["Head Q", "Branch 1", "Branch 3", "Branch 4", "Branch 5" , "Kaydka M.hassan"]
            branch = st.selectbox("📍 Branch", branch_options)
            employee = st.text_input("👤 Magacaaga (Your Name)")
        with c2:
            cat_map = {
                "alaabta Maqan (Missing)": "Maqan",
                "alaabta Suqqa leh (High Demand)": "Suuq leh",
                "bahiyaha Dadweynaha (New Request)": "Dadweynaha"
            }
            category_selection = st.selectbox("📂 Nooca Warbixinta (Report Type)", list(cat_map.keys()))
            item = st.text_input("📦 Magaca Alaabta (Item Name)")
        
        note = st.text_input("📝 Faahfaahin / Tirada (Note/Qty)")
        
        st.write("")
        if st.form_submit_button("🚀 Gudbi (Submit)", use_container_width=True):
            if employee and item:
                try:
                    data = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=0)
                    if data is None: data = pd.DataFrame()
                    data = data.dropna(how="all")
                    
                    real_category = cat_map[category_selection]
                    # Use Real Time
                    real_time_str = get_local_time().strftime("%Y-%m-%d %H:%M")
                    
                    new_row = pd.DataFrame([{
                        "Date": real_time_str,
                        "Branch": branch,
                        "Employee": employee,
                        "Category": real_category,
                        "Item": item,
                        "Note": note
                    }])
                    
                    updated = pd.concat([data, new_row], ignore_index=True)
                    conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=updated)
                    st.cache_data.clear()
                    st.success(f"✅ Waa la gudbiyay! ({real_time_str})")
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("⚠️ Fadlan buuxi Magacaaga iyo Alaabta.")

# --- MANAGER TAB ---
with tab_manager:
    
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        c_pass, c_btn = st.columns([5, 1], vertical_alignment="bottom")
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
        
        # Load Data
        try:
            df = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=0)
            if df is None: df = pd.DataFrame()
            df = df.dropna(how="all")
        except:
            df = pd.DataFrame()

        if not df.empty:
            # METRICS CARD STYLE
            st.markdown("---")
            count_total = len(df)
            count_missing = len(df[df['Category'] == 'Maqan']) if 'Category' in df.columns else 0
            count_new = len(df[df['Category'] == 'Dadweynaha']) if 'Category' in df.columns else 0
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Wadarta (Total)", count_total)
            m2.metric("Maqan (Missing)", count_missing, delta_color="inverse")
            m3.metric("Dalab (New Req)", count_new)
            st.markdown("---")
            
            # DOWNLOADS
            st.subheader("📄 Warbixinada (Reports)")
            col_pdf, col_xls = st.columns(2)
            
            with col_pdf:
                st.download_button(
                    label="📥 Download PDF Report", 
                    data=generate_pdf(df),
                    file_name=f"Mareero_Report_{get_local_time().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            with col_xls:
                st.download_button(
                    label="📥 Download Excel Data",
                    data=generate_excel(df),
                    file_name=f"Mareero_Data_{get_local_time().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            st.divider()

            # --- EDIT/DELETE TABLE (WITH SAFETY CONFIRMATION) ---
            st.subheader("🛠️ Wax ka bedel / Tirtir (Edit/Delete)")
            
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
            
            if "confirm_delete" not in st.session_state:
                st.session_state.confirm_delete = False
            
            c_save, c_del = st.columns([1, 1])

            with c_save:
                if st.button("💾 Kaydi Isbedelka (Save)", use_container_width=True):
                    try:
                        final_df = edited_df.drop(columns=["Select"])
                        conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=final_df)
                        st.cache_data.clear()
                        st.success("✅ Saved!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

            with c_del:
                if st.button("🗑️ Tirtir (Delete)", type="primary", use_container_width=True):
                    if edited_df["Select"].any():
                        st.session_state.confirm_delete = True
                    else:
                        st.warning("⚠️ Select rows first")

            # CONFIRMATION BOX (Professional Safety)
            if st.session_state.confirm_delete:
                st.warning("⚠️ Ma hubtaa inaad tirtirto? (Are you sure?)")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("✅ Haa (Yes)", type="primary", use_container_width=True):
                        try:
                            rows_to_keep = edited_df[edited_df["Select"] == False]
                            final_df = rows_to_keep.drop(columns=["Select"])
                            conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=final_df)
                            st.cache_data.clear()
                            st.session_state.confirm_delete = False
                            st.success("✅ Deleted!")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                with col_no:
                    if st.button("❌ Maya (Cancel)", use_container_width=True):
                        st.session_state.confirm_delete = False
                        st.rerun()

        else:
            st.warning("⚠️ Xog ma jiro (No Data Found)")
