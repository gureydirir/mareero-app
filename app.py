import streamlit as st

# ---------------------------------------------------------
# PAGE CONFIGURATION (MUST BE THE FIRST STREAMLIT COMMAND)
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
import pytz # For Somalia Time
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

# --- 2. CSS: ORIGINAL WHITE & RED THEME ---
st.markdown("""
<style>
    /* Hide Streamlit Logos & Menus */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    div[data-testid="stStatusWidget"] {visibility: hidden;}
    
    /* Adjust top padding for mobile */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 5rem;
    }
    
    /* Make the Buttons Red and Round-ish */
    div[data-testid="stButton"] button {
        border-radius: 5px;
        font-weight: bold;
    }
    
    /* Tabs Selection Color (Red) */
    .stTabs [aria-selected="true"] {
        background-color: #8B0000 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. SETUP DATABASE ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    SHEET_URL = st.secrets["gcp_sheet_url"] 
except Exception as e:
    st.error(f"⚠️ Connection Error: {e}")
    st.stop()

# --- 4. EXCEL ENGINE ---
def clean_text(text):
    if pd.isna(text) or str(text).lower() == 'nan':
        return "-"
    return str(text)

def generate_excel(df):
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Warbixin')
            
            # Auto-Adjust Column Widths
            worksheet = writer.sheets['Warbixin']
            for i, col in enumerate(df.columns):
                max_len = max(
                    df[col].astype(str).map(len).max(),
                    len(str(col))
                ) + 2
                col_letter = chr(65 + i)
                worksheet.column_dimensions[col_letter].width = max_len
    except Exception as e:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
            
    output.seek(0)
    return output

# --- 5. PDF ENGINE (PERFECT ALIGNMENT & COLORS) ---
def generate_pdf(df):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # --- COLORS & STYLES ---
    primary_color = colors.HexColor("#8B0000") # Dark Red
    text_color = colors.HexColor("#2C3E50")    # Dark Blue/Grey
    
    # --- HEADER ---
    c.setFillColor(primary_color)
    c.rect(0, height-110, width, 110, fill=1, stroke=0)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(40, height-60, "MAREERO SYSTEM")
    c.setFont("Helvetica", 12)
    c.drawString(40, height-80, "General Trading & Spare Parts LLC")

    # Real Time Date
    current_time = get_local_time()
    c.drawRightString(width-40, height-50, "OPERATIONAL REPORT")
    c.setFont("Helvetica", 10)
    c.drawRightString(width-40, height-65, f"Date: {current_time.strftime('%d %B %Y')}")
    c.drawRightString(width-40, height-80, f"Time: {current_time.strftime('%I:%M %p')}")

    # --- SECTION 1: SUMMARY ---
    c.setFillColor(text_color)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height-150, "1. KOOBITAAN (SUMMARY):")
    
    # Calc Metrics
    total = len(df)
    missing = len(df[df['Category'] == 'Maqan']) if not df.empty else 0
    new_req = len(df[df['Category'] == 'Dadweynaha']) if not df.empty else 0
    
    # Draw Summary Boxes
    box_y = height - 220
    c.setStrokeColor(colors.lightgrey)
    
    # Box 1
    c.roundRect(40, box_y, 160, 50, 5, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(120, box_y+20, str(total))
    c.setFont("Helvetica", 10)
    c.drawCentredString(120, box_y+5, "Total Reports")
    
    # Box 2
    c.roundRect(210, box_y, 160, 50, 5, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(290, box_y+20, str(missing))
    c.setFont("Helvetica", 10)
    c.drawCentredString(290, box_y+5, "Alaabta Maqan")
    
    # Box 3
    c.roundRect(380, box_y, 160, 50, 5, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(460, box_y+20, str(new_req))
    c.setFont("Helvetica", 10)
    c.drawCentredString(460, box_y+5, "Requests (Dalab)")

    # --- SECTION 2: CHARTS ---
    y_chart = height - 260
    c.setFillColor(text_color)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y_chart, "2. SHAXDA XOGTA (CHARTS):")
    
    if not df.empty:
        try:
            plt.rcdefaults() # Ensure white background for PDF
            
            # Chart 1: Pie
            fig1, ax1 = plt.subplots(figsize=(4, 3))
            category_counts = df['Category'].value_counts()
            if not category_counts.empty:
                # Custom colors: Red for Maqan, Blue for Dadweynaha, Grey for others
                custom_colors = ['#d32f2f', '#1976d2', '#9e9e9e', '#ffa726'] 
                ax1.pie(category_counts, labels=category_counts.index, autopct='%1.0f%%', colors=custom_colors)
                
                img1 = io.BytesIO()
                plt.savefig(img1, format='png', bbox_inches='tight')
                plt.close(fig1)
                img1.seek(0)
                c.drawImage(ImageReader(img1), 40, y_chart-220, width=240, height=180)
            
            # Chart 2: Bar
            fig2, ax2 = plt.subplots(figsize=(4, 3))
            branch_counts = df['Branch'].value_counts()
            if not branch_counts.empty:
                branch_counts.plot(kind='bar', color='#0f172a', ax=ax2)
                plt.xticks(rotation=45, ha='right', fontsize=8)
                
                img2 = io.BytesIO()
                plt.savefig(img2, format='png', bbox_inches='tight')
                plt.close(fig2)
                img2.seek(0)
                c.drawImage(ImageReader(img2), 300, y_chart-220, width=240, height=180)
        except Exception:
            pass

    # --- SECTION 3: LIST ---
    y_list = y_chart - 250
    c.setFillColor(text_color)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y_list, "3. LIISKA FAAHFAAHSAN (DETAILS):")

    # Table Header
    y_row = y_list - 30
    # Fixed Column Widths (Total ~515)
    col_widths = [80, 150, 80, 80, 125] 
    headers = ["TYPE", "ITEM NAME", "BRANCH", "STAFF", "NOTES"]
    
    c.setFillColor(primary_color)
    c.rect(40, y_row-5, sum(col_widths), 20, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    
    x_pos = 45
    for i, h in enumerate(headers):
        c.drawString(x_pos, y_row, h)
        x_pos += col_widths[i]
    
    y_row -= 20
    c.setFont("Helvetica", 9)
    
    if not df.empty:
        # Sort: Show Maqan first
        if 'Category' in df.columns:
            df = df.sort_values(by=['Category'])

        row_count = 0
        for _, row in df.iterrows():
            if row_count % 2 == 0:
                c.setFillColor(colors.HexColor("#f5f5f5")) # Light grey stripe
                c.rect(40, y_row-5, sum(col_widths), 15, fill=1, stroke=0)
            
            # Text Color Logic
            cat_val = str(row.get('Category', ''))
            
            if cat_val == 'Maqan':
                c.setFillColor(colors.red)
            elif cat_val == 'Dadweynaha':
                c.setFillColor(colors.blue)
            else:
                c.setFillColor(colors.black)
            
            # Clean and truncate text
            vals = [
                cat_val[:15],
                str(row.get('Item', ''))[:25],
                str(row.get('Branch', '')).replace("Branch", "Br."),
                str(row.get('Employee', ''))[:14],
                str(row.get('Note', ''))[:22]
            ]
            
            x_pos = 45
            for i, val in enumerate(vals):
                c.drawString(x_pos, y_row, val)
                x_pos += col_widths[i]
            
            y_row -= 18
            row_count += 1
            
            if y_row < 50: 
                c.showPage()
                y_row = height - 50

    c.save()
    buffer.seek(0)
    return buffer

# --- 6. THE APP UI ---
st.title("🏢 Mareero General Trading LLC")

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
        
        if st.form_submit_button("🚀 Gudbi (Submit)", use_container_width=True):
            if employee and item:
                try:
                    data = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=0)
                    if data is None: data = pd.DataFrame()
                    data = data.dropna(how="all")
                    
                    real_category = cat_map[category_selection]
                    # REAL TIME
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
                    st.success(f"✅ Waa la gudbiyay! ({current_local_time})")
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("⚠️ Fadlan buuxi Magacaaga iyo Alaabta.")

# --- MANAGER TAB ---
with tab_manager:
    
    # --- 1. LOGIN ROW WITH ENTER BUTTON ---
    c_pass, c_btn = st.columns([5, 1], vertical_alignment="bottom")
    
    with c_pass:
        password = st.text_input("Geli Furaha (Password)", type="password", placeholder="Enter Password...", label_visibility="collapsed")
    with c_btn:
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
                count_total = len(df)
                count_missing = len(df[df['Category'] == 'Maqan']) if 'Category' in df.columns else 0
                count_new = len(df[df['Category'] == 'Dadweynaha']) if 'Category' in df.columns else 0
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Wadarta (Total)", count_total)
                m2.metric("Maqan (Missing)", count_missing)
                m3.metric("Dalab (New Req)", count_new)
                
                st.divider()
                
                # DOWNLOAD BUTTONS
                st.subheader("📄 Warbixinada (Reports)")
                col_pdf, col_xls = st.columns(2)
                
                with col_pdf:
                    st.download_button(
                        label="📥 Download PDF Report",
                        data=generate_pdf(df),
                        file_name=f"Mareero_Report_{get_local_time().strftime('%Y-%m-%d')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                with col_xls:
                    st.download_button(
                        label="📥 Download Excel Data",
                        data=generate_excel(df),
                        file_name=f"Mareero_Data_{get_local_time().strftime('%Y-%m-%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

                st.divider()

                # --- 2. EDIT/DELETE TABLE ---
                st.subheader("🛠️ Wax ka bedel / Tirtir (Edit/Delete)")
                
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
                
                # Init Confirmation State
                if "confirm_delete" not in st.session_state:
                    st.session_state.confirm_delete = False
                
                st.write("") 
                
                c_save, c_mid, c_del = st.columns([3, 2, 1])

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
                    if st.button("🗑️", type="primary", help="Delete Selected Rows"):
                         if edited_df["Select"].any():
                             st.session_state.confirm_delete = True
                         else:
                             st.warning("⚠️ Select first")
                
                # CONFIRMATION BOX (Professional Safety)
                if st.session_state.confirm_delete:
                    st.warning("⚠️ Ma hubtaa inaad tirtirto? (Are you sure?)")
                    cy, cn = st.columns(2)
                    with cy:
                        if st.button("✅ Haa (Yes)", type="primary", use_container_width=True):
                            try:
                                rows_to_keep = edited_df[edited_df["Select"] == False]
                                final_df = rows_to_keep.drop(columns=["Select"])
                                conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=final_df)
                                st.cache_data.clear()
                                st.session_state.confirm_delete = False
                                st.success("Deleted!")
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))
                    with cn:
                        if st.button("❌ Maya (Cancel)", use_container_width=True):
                            st.session_state.confirm_delete = False
                            st.rerun()

            else:
                st.warning("⚠️ Xog ma jiro (No Data Found)")
                
        else:
            st.error("Furaha waa khalad (Wrong Password)")
