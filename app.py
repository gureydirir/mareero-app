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

# --- 3. DATABASE CONNECTION ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    SHEET_URL = st.secrets["gcp_sheet_url"] 
except Exception as e:
    st.error(f"⚠️ Connection Error: {e}")
    st.stop()

# --- 4. EXCEL ENGINE (AUTO-SPLIT BY BRANCH) ---
def clean_sheet_name(name):
    """Sanitize string to be a valid Excel sheet name"""
    if not name: return "Unknown"
    # Remove invalid characters [] : * ? / \
    clean = re.sub(r'[\[\]:*?/\\]', '', str(name))
    # Max length 31 characters
    return clean[:31]

def generate_excel(df):
    output = io.BytesIO()
    
    # Get unique branches for splitting
    if not df.empty and 'Branch' in df.columns:
        branches = df['Branch'].unique()
    else:
        branches = ["Data"]

    if HAS_XLSXWRITER:
        # --- ADVANCED MODE (Split Tabs + Formatting) ---
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            workbook = writer.book
            
            # --- FORMATS ---
            header_fmt = workbook.add_format({
                'bold': True, 'font_color': 'white', 'bg_color': '#1E3A8A',
                'border': 1, 'align': 'center', 'valign': 'vcenter'
            })
            duplicate_fmt = workbook.add_format({
                'font_color': '#9C0006', 'bg_color': '#FFC7CE'
            })
            cat_missing_fmt = workbook.add_format({
                'bg_color': '#FFE6E6', 'border': 1
            })
            cat_request_fmt = workbook.add_format({
                'bg_color': '#E6F3FF', 'border': 1
            })

            # --- LOOP THROUGH BRANCHES ---
            for branch in branches:
                # 1. Filter Data
                if 'Branch' in df.columns:
                    sub_df = df[df['Branch'] == branch]
                else:
                    sub_df = df
                
                if sub_df.empty: continue

                # 2. Create Sheet Name
                sheet_name = clean_sheet_name(branch)
                sheet = workbook.add_worksheet(sheet_name)
                
                # 3. Write Data
                sub_df.to_excel(writer, sheet_name=sheet_name, startrow=1, header=False, index=False)
                
                # 4. Create Table
                (max_row, max_col) = sub_df.shape
                column_settings = [{'header': column} for column in sub_df.columns]
                
                sheet.add_table(0, 0, max_row, max_col - 1, {
                    'columns': column_settings,
                    'style': 'TableStyleMedium9',
                    'name': f"Table_{random.randint(1000,9999)}" # Unique table name
                })
                
                # 5. Apply Formatting logic (Same as before, just inside the loop)
                cols = sub_df.columns.tolist()
                
                # Duplicates Highlight
                if 'Item' in cols:
                    item_idx = cols.index('Item')
                    letter = chr(65 + item_idx)
                    rng = f"{letter}2:{letter}{max_row+1}"
                    sheet.conditional_format(rng, {'type': 'duplicate', 'format': duplicate_fmt})

                # Category Colors
                if 'Category' in cols:
                    cat_idx = cols.index('Category')
                    letter = chr(65 + cat_idx)
                    rng = f"{letter}2:{letter}{max_row+1}"
                    sheet.conditional_format(rng, {'type': 'text', 'criteria': 'containing', 'value': "go'an", 'format': cat_missing_fmt})
                    sheet.conditional_format(rng, {'type': 'text', 'criteria': 'containing', 'value': "Dadweynaha", 'format': cat_request_fmt})

                # Auto-fit Widths
                for i, col in enumerate(sub_df.columns):
                    max_len = max(sub_df[col].astype(str).map(len).max(), len(str(col))) + 4
                    sheet.set_column(i, i, max_len)

    else:
        # --- BASIC FALLBACK (Split Tabs only, no colors) ---
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for branch in branches:
                if 'Branch' in df.columns:
                    sub_df = df[df['Branch'] == branch]
                else:
                    sub_df = df
                
                if not sub_df.empty:
                    sheet_name = clean_sheet_name(branch)
                    sub_df.to_excel(writer, index=False, sheet_name=sheet_name)

    output.seek(0)
    return output

# --- 5. PDF ENGINE ---
def generate_pdf(df):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Colors
    header_bg = colors.HexColor("#1E3A8A") # Navy Blue
    line_color = colors.HexColor("#dcdcdc") # Grey Grid
    
    # --- HEADER ---
    c.setFillColor(header_bg)
    c.rect(0, height-100, width, 100, fill=1, stroke=0)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(40, height-50, "MAREERO SYSTEM")
    c.setFont("Helvetica", 12)
    c.drawString(40, height-70, " Mareero General Trading  LLC")
    
    # Time
    current_time = get_local_time()
    c.drawRightString(width-40, height-50, "OPERATIONAL REPORT")
    c.setFont("Helvetica", 10)
    c.drawRightString(width-40, height-65, f"Date: {current_time.strftime('%d %B %Y')}")
    c.drawRightString(width-40, height-80, f"Time: {current_time.strftime('%I:%M %p')}")

    # --- SUMMARY ---
    y_pos = height - 140
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y_pos, "1. KOOBITAAN (SUMMARY)")
    
    total = len(df)
    missing = len(df[df['Category'] == 'Alaabta go\'an']) if not df.empty else 0
    requests = len(df[df['Category'] == 'bahiyaha Dadweynaha']) if not df.empty else 0
    
    # Boxes
    box_w, box_h = 160, 50
    start_x = 40
    metrics = [("Total Reports", str(total)), ("Alaabta go'an", str(missing)), ("Requests", str(requests))]
    
    for i, (label, value) in enumerate(metrics):
        x = start_x + (i * 175)
        c.setStrokeColor(colors.lightgrey)
        c.roundRect(x, y_pos-60, box_w, box_h, 6, fill=0, stroke=1)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(x + box_w/2, y_pos-35, value)
        c.setFillColor(colors.grey)
        c.setFont("Helvetica", 10)
        c.drawCentredString(x + box_w/2, y_pos-50, label)

    # --- CHARTS ---
    y_pos -= 80
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y_pos, "2. SHAXDA XOGTA (CHARTS)")
    
    if not df.empty:
        try:
            plt.rcdefaults()
            # Pie
            fig1, ax1 = plt.subplots(figsize=(4, 3))
            cat_counts = df['Category'].value_counts()
            ax1.pie(cat_counts, labels=cat_counts.index, autopct='%1.0f%%', colors=['#ef4444', '#f59e0b', '#3b82f6'])
            img1 = io.BytesIO()
            plt.savefig(img1, format='png', bbox_inches='tight')
            img1.seek(0)
            c.drawImage(ImageReader(img1), 40, y_pos-220, width=220, height=165)
            plt.close(fig1)

            # Bar
            fig2, ax2 = plt.subplots(figsize=(4, 3))
            branch_counts = df['Branch'].value_counts()
            branch_counts.plot(kind='bar', color='#1E3A8A', ax=ax2)
            plt.xticks(rotation=45, ha='right', fontsize=8)
            img2 = io.BytesIO()
            plt.savefig(img2, format='png', bbox_inches='tight')
            img2.seek(0)
            c.drawImage(ImageReader(img2), 300, y_pos-220, width=240, height=180)
            plt.close(fig2)
        except:
            pass

    # --- TABLE ---
    y_pos -= 240
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y_pos, "3. LIISKA FAAHFAAHSAN (DETAILS)")
    
    y_curr = y_pos - 30
    col_widths = [80, 135, 105, 85, 110] 
    headers = ["TYPE", "ITEM NAME", "BRANCH", "STAFF", "NOTES"]
    
    def draw_header(y):
        c.setFillColor(header_bg)
        c.rect(40, y-6, sum(col_widths), 22, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9)
        xp = 45
        for i, h in enumerate(headers):
            c.drawString(xp, y+2, h)
            xp += col_widths[i]

    draw_header(y_curr)
    y_curr -= 22
    c.setFont("Helvetica", 9)
    
    if not df.empty:
        if 'Category' in df.columns:
            df = df.sort_values(by=['Category'])

        row_count = 0
        for _, row in df.iterrows():
            if row_count % 2 == 0:
                c.setFillColor(colors.HexColor("#f1f5f9"))
                c.rect(40, y_curr-6, sum(col_widths), 18, fill=1, stroke=0)
            
            cat = str(row.get('Category', ''))
            if "go'an" in cat or "Maqan" in cat: c.setFillColor(colors.red)
            elif 'Dadweynaha' in cat: c.setFillColor(colors.blue)
            else: c.setFillColor(colors.black)
            
            vals = [
                cat[:15],
                str(row.get('Item', ''))[:25],
                str(row.get('Branch', ''))[:18], 
                str(row.get('Employee', ''))[:14],
                str(row.get('Note', ''))[:20]
            ]
            
            x_pos = 45
            c.setLineWidth(0.5)
            c.setStrokeColor(line_color)
            
            for i, val in enumerate(vals):
                c.drawString(x_pos, y_curr, val)
                c.line(x_pos + col_widths[i] - 5, y_curr-5, x_pos + col_widths[i] - 5, y_curr+12)
                x_pos += col_widths[i]
            
            c.line(40, y_curr-6, 40+sum(col_widths), y_curr-6)
            
            y_curr -= 18
            row_count += 1
            
            if y_curr < 60:
                c.showPage()
                y_curr = height - 50
                draw_header(y_curr)
                y_curr -= 22
                c.setFont("Helvetica", 9)

    # --- SIGNATURE ---
    if y_curr < 80:
        c.showPage()
        y_curr = height - 100
        
    y_sig = 50
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    
    c.line(40, y_sig, 200, y_sig)
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    c.drawString(40, y_sig-15, "Manager Signature")
    
    c.line(350, y_sig, 510, y_sig)
    c.drawString(350, y_sig-15, "Date & Stamp")

    c.save()
    buffer.seek(0)
    return buffer

# --- 6. APP UI ---
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🏢 Mareero General Trading LLC</h1>", unsafe_allow_html=True)

tab_staff, tab_manager = st.tabs(["📝 Qeybta Shaqaalaha (Staff)", "🔐 Maamulka (Manager)"])

# --- STAFF TAB ---
with tab_staff:
    st.info("Fadlan halkan ku diiwaangeli warbixintaada maalinlaha ah.")
    
    with st.form("log_form", clear_on_submit=True):
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
        
        note = st.text_input("📝 Faahfaahin / Tirada (Note/Qty)")
        
        if st.form_submit_button("🚀 Gudbi (Submit)", use_container_width=True):
            if employee and item:
                try:
                    data = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=5)
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
            df = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=5)
            if df is None: df = pd.DataFrame()
            df = df.dropna(how="all")
            if not df.empty and 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        except:
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
            
            # --- SEARCH & FILTER ---
            st.subheader("🔍 Search & Filter")
            col_search, col_filter = st.columns(2)
            
            with col_search:
                search_term = st.text_input("🔍 Raadi (Search Item/Branch/Staff)...", placeholder="Type to search...")
                
            with col_filter:
                date_filter = st.selectbox("📅 Waqtiga (Time Filter)", ["All Time", "Today (Maanta)", "This Week (Isbuucan)"])
            
            filtered_df = df.copy()
            now = get_local_time()
            
            if date_filter == "Today (Maanta)":
                filtered_df = filtered_df[filtered_df['Date'].dt.date == now.date()]
            elif date_filter == "This Week (Isbuucan)":
                start_week = now - pd.Timedelta(days=7)
                filtered_df = filtered_df[filtered_df['Date'] >= start_week]
                
            if search_term:
                filtered_df = filtered_df[filtered_df.astype(str).apply(lambda x: x.str.contains(search_term, case=False).any(), axis=1)]

            

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
            # --- SMOOTH BATCH DELETE SECTION ---
            with st.expander("🛠️ Wax ka bedel / Tirtir (Edit/Delete)", expanded=True):
                if not filtered_df.empty:
                    # Prepare Data
                    df_with_delete = filtered_df.copy()
                    df_with_delete.insert(0, "Select", False)

                    # 🔴 START FORM: This prevents the app from loading on every click
                    with st.form("delete_form"):
                        st.write("Select rows to edit or delete below:")
                        
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
                        
                        c1, c2 = st.columns([1,1])
                        with c1:
                            # Button 1: Save Changes (Edits)
                            save_btn = st.form_submit_button("💾 Kaydi Isbedelka (Save)")
                        with c2:
                            # Button 2: Trigger Delete Logic
                            delete_btn = st.form_submit_button("🗑️ Diyaari Tirtiridda (Prepare Delete)")
                    # 🔴 END FORM

                    # --- LOGIC HANDLER (Runs only after button click) ---
                    
                    # 1. Handle Save
                    if save_btn:
                        try:
                            final_df = edited_df.drop(columns=["Select"])
                            conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=final_df)
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
                                    conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=final_df)
                                    
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


