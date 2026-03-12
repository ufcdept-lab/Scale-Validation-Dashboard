import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import statistics
import math
import io
import os
from datetime import datetime

# ==================== CONFIG ====================
st.set_page_config(page_title="Scale Validation Dashboard", page_icon="⚖️", layout="wide")

# ==================== SESSION STATE ====================
if 'weights' not in st.session_state:
    st.session_state.weights = []

def reset_data():
    st.session_state.weights = []

# --- ฟังก์ชันจัดการการคีย์ข้อมูล (แก้ไขให้รองรับค่าว่าง) ---
def add_manual_weight():
    val = st.session_state.weight_input
    # ตรวจสอบว่ามีค่าและมากกว่า 0 ถึงจะบันทึก
    if val is not None and val > 0:
        st.session_state.weights.append(val)
        # เคลียร์ค่าให้กลับเป็นช่องว่าง (None) เพื่อรอรับชิ้นต่อไป
        st.session_state.weight_input = None

def delete_item(index):
    st.session_state.weights.pop(index)

def save_to_history(part_no, sample_size, apw, std, cv, max_error, status, raw_weights):
    history_file = "validation_history.csv"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    raw_str = ", ".join([f"{w:.2f}" for w in raw_weights])
    
    data = {
        "Timestamp": [timestamp],
        "Part Number": [part_no],
        "Sample Size": [sample_size],
        "APW (g)": [round(apw, 4)],
        "STD": [round(std, 4)],
        "%CV": [round(cv, 2)],
        "Max Error (pcs)": [round(max_error, 2)],
        "Status": [status],
        "Raw Data": [raw_str]
    }
    df = pd.DataFrame(data)
    
    if os.path.isfile(history_file):
        df.to_csv(history_file, mode='a', header=False, index=False, encoding='utf-8-sig')
    else:
        df.to_csv(history_file, mode='w', header=True, index=False, encoding='utf-8-sig')

# ==================== SIDEBAR ====================
with st.sidebar:
    st.title("📋 Project Config")
    part_no = st.text_input("Part Number:", value="A123456")
    
    col1, col2 = st.columns(2)
    with col1: target_qty = st.number_input("Sample Size:", min_value=1, value=30)
    with col2: full_snp = st.number_input("Full SNP:", min_value=1, value=30)
    
    st.divider()
    
    st.subheader("⚖️ Weight Input (g)")
    # --- แก้ไขช่องรับน้ำหนัก: ค่าเริ่มต้น=None (ว่าง), ทศนิยม=2 ตำแหน่ง ---
    st.number_input(
        "Enter Weight:", 
        min_value=0.0, 
        step=0.01, 
        format="%.2f", 
        value=None, 
        key="weight_input", 
        on_change=add_manual_weight
    )
    
    st.markdown("**📝 Data List (รายการที่ชั่งแล้ว)**")
    list_container = st.container(height=300) 
    with list_container:
        if len(st.session_state.weights) == 0:
            st.caption("ยังไม่มีข้อมูล...")
        else:
            for i, w in enumerate(st.session_state.weights):
                c1, c2 = st.columns([3, 1])
                # --- แก้ไขการแสดงผล List ให้เป็นทศนิยม 2 ตำแหน่ง ---
                c1.markdown(f"**#{i+1:02d}:** `{w:.2f} g`")
                c2.button("❌", key=f"del_{i}_{w}_{datetime.now().microsecond}", on_click=delete_item, args=(i,))

    st.divider()
    
    st.subheader("📁 Excel / CSV Upload")
    uploaded_file = st.file_uploader("Choose a file", type=['xlsx', 'xls', 'csv'], label_visibility="collapsed")
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file, header=None)
            else:
                df = pd.read_excel(uploaded_file, header=None)
            
            new_weights = []
            for col in df.columns:
                numeric_col = pd.to_numeric(df[col], errors='coerce').dropna()
                if not numeric_col.empty:
                    new_weights.extend(numeric_col.tolist())
                    break
            
            if new_weights:
                if st.button(f"Import {len(new_weights)} Records", type="primary"):
                    st.session_state.weights.extend(new_weights)
                    st.success(f"Imported {len(new_weights)} records!")
            else:
                st.error("No numeric data found.")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    st.divider()
    if st.button("🔄 Reset All Data", type="secondary", use_container_width=True):
        reset_data()
        st.rerun()

# ==================== MAIN UI (TABS) ====================
st.title("Scale Counting Validation Dashboard v9.3")

tab1, tab2 = st.tabs(["📊 Dashboard & Analysis", "📁 History Logs (ประวัติการตรวจสอบ)"])

# -------------------- TAB 1: DASHBOARD --------------------
with tab1:
    weights = st.session_state.weights
    n = len(weights)

    if n == 0:
        st.info("WAITING FOR DATA: Please enter weights manually or upload a file from the sidebar.")
    else:
        mean_val = statistics.mean(weights) if n > 0 else 0
        sd_val = statistics.stdev(weights) if n > 1 else 0
        cv_val = (sd_val / mean_val) * 100 if mean_val != 0 else 0
        min_val = min(weights) if n > 0 else 0
        max_val = max(weights) if n > 0 else 0
        error_pieces = (3 * math.sqrt(full_snp) * sd_val) / mean_val if mean_val != 0 else 0
        status_result = "PASSED" if error_pieces <= 0.5 else "FAILED"

        if n >= 2:
            if status_result == "PASSED":
                st.success("✅ **STATUS: PASSED** (No Risk of Miscount)")
            else:
                st.error("❌ **STATUS: FAILED** (High Risk of Miscount!)")
        else:
            st.warning("⚠️ Need at least 2 samples to calculate risk.")

        col1, col2, col3, col4 = st.columns(4)
        status_text = "(COMPLETED)" if n >= target_qty else ""
        col1.metric("Count / Target", f"{n} pcs", delta=status_text, delta_color="normal")
        col2.metric("Average (APW)", f"{mean_val:.4f} g")
        col3.metric("%CV (Precision)", f"{cv_val:.2f} %", delta="< 1.0% is good", delta_color="off")
        col4.metric("Max Error @ Full SNP", f"± {error_pieces:.2f} pcs", 
                    delta=status_result, delta_color="inverse" if error_pieces > 0.5 else "normal")

        # --- CHARTS ---
        if n > 1:
            st.divider()
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 6), dpi=100)
            fig.patch.set_facecolor('#0e1117') 
            for ax in [ax1, ax2, ax3, ax4]:
                ax.set_facecolor('#0e1117')
                ax.tick_params(colors='#aaaaaa')
                for spine in ax.spines.values(): spine.set_color('#555555')

            x_seq = list(range(1, n+1))

            ax1.hist(weights, bins=max(5, int(n**0.5)), density=True, color='#3498db', edgecolor='white', alpha=0.7)
            if sd_val > 0:
                x_curve = np.linspace(min_val-sd_val, max_val+sd_val, 100)
                y_curve = (1/(sd_val * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x_curve - mean_val)/sd_val)**2)
                ax1.plot(x_curve, y_curve, color='#e74c3c', linewidth=2)
            ax1.set_title("1. Distribution (Bell Curve)", color='white')

            ax2.plot(x_seq, weights, marker='o', color='#2ecc71', linewidth=1.5, markersize=4)
            ax2.axhline(y=mean_val, color='#e74c3c', linestyle='--', alpha=0.7)
            ax2.set_title("2. Run Chart (Trend)", color='white')

            ax3.scatter(x_seq, weights, color='#f1c40f', edgecolor='white', s=40)
            if sd_val > 0:
                r_matrix = np.corrcoef(x_seq, weights)
                r_val = r_matrix[0, 1] if not np.isnan(r_matrix[0, 1]) else 0
                z = np.polyfit(x_seq, weights, 1)
                p = np.poly1d(z)
                ax3.plot(x_seq, p(x_seq), color='#9b59b6', linestyle=':', linewidth=2)
                ax3.text(0.05, 0.90, f"r = {r_val:.3f}", transform=ax3.transAxes, color='#f1c40f', weight='bold')
            ax3.set_title("3. Scatter Plot (Correlation)", color='white')

            bp = ax4.boxplot(weights, vert=False, patch_artist=True)
            for patch in bp['boxes']: patch.set_facecolor('#9b59b6')
            for median in bp['medians']: median.set(color='red', linewidth=2)
            for flier in bp['fliers']: 
                flier.set(marker='o', markerfacecolor='#ff3333', markeredgecolor='white', markersize=8, alpha=1.0)
            
            outlier_data = bp['fliers'][0].get_xdata()
            for x_val in np.unique(outlier_data):
                indices = [i+1 for i, w in enumerate(weights) if w == x_val]
                label = ",".join([f"#{i}" for i in indices])
                ax4.annotate(label, xy=(x_val, 1), xytext=(0, 12), textcoords='offset points', ha='center', va='bottom', color='#ff3333', weight='bold')
            ax4.set_title("4. Box Plot (Outliers Detection)", color='white')
            ax4.set_yticks([])

            fig.tight_layout(pad=2.0)
            st.pyplot(fig) 

        st.divider()
        
        # --- BOTTOM ACTION BAR ---
        col_b1, col_b2, col_b3, col_b4 = st.columns(4)
        col_b1.metric("⬇️ MIN Weight", f"{min_val:.4f} g")
        col_b2.metric("⬆️ MAX Weight", f"{max_val:.4f} g")
        col_b3.metric("📊 STD", f"{sd_val:.4f}")

        if n > 1:
            with col_b4:
                if st.button("💾 Save Record to History", type="primary", use_container_width=True):
                    save_to_history(part_no, n, mean_val, sd_val, cv_val, error_pieces, status_result, weights)
                    st.success(f"บันทึกประวัติ Part: {part_no} เรียบร้อยแล้ว! (ดูได้ที่แท็บ History Logs)")

                buffer = io.BytesIO()
                with PdfPages(buffer) as pdf:
                    pdf_fig = plt.figure(figsize=(8.27, 11.69), facecolor='white') 
                    
                    pdf_fig.text(0.5, 0.94, "ZERO DEFECT: SCALE VALIDATION REPORT", fontsize=18, weight='bold', ha='center', color='black')
                    pdf_fig.text(0.1, 0.89, f"Part Number: {part_no}", fontsize=12, color='black')
                    pdf_fig.text(0.1, 0.86, f"Sample Size: {n} pcs", fontsize=12, color='black')
                    pdf_fig.text(0.55, 0.89, f"Full SNP Target: {full_snp} pcs/pack", fontsize=12, weight='bold', color='black')
                    
                    status_pdf = "PASSED" if error_pieces <= 0.5 else "FAILED (Miscount Risk)"
                    pdf_fig.text(0.1, 0.80, "Analysis Result:", fontsize=14, weight='bold', color='black')
                    pdf_fig.text(0.15, 0.77, f"- Average (APW) : {mean_val:.4f} g", fontsize=12, color='black')
                    pdf_fig.text(0.15, 0.74, f"- STD           : {sd_val:.4f}", fontsize=12, color='black')
                    pdf_fig.text(0.15, 0.71, f"- Min / Max     : {min_val:.4f} g / {max_val:.4f} g", fontsize=12, color='black')
                    pdf_fig.text(0.15, 0.68, f"- Max Error     : +/- {error_pieces:.2f} pieces", fontsize=12, weight='bold', color='red' if error_pieces > 0.5 else 'green')
                    pdf_fig.text(0.15, 0.63, f"Conclusion: {status_pdf}", fontsize=16, weight='bold', color='red' if error_pieces > 0.5 else 'green')

                    ax1_p = pdf_fig.add_axes([0.1, 0.38, 0.35, 0.15]) 
                    ax2_p = pdf_fig.add_axes([0.55, 0.38, 0.35, 0.15])
                    ax3_p = pdf_fig.add_axes([0.1, 0.15, 0.35, 0.15])
                    ax4_p = pdf_fig.add_axes([0.55, 0.15, 0.35, 0.15])

                    for ax in [ax1_p, ax2_p, ax3_p, ax4_p]:
                        ax.set_facecolor('white')
                        ax.tick_params(colors='black')
                        for spine in ax.spines.values(): spine.set_color('black')

                    ax1_p.hist(weights, bins=max(5, int(n**0.5)), density=True, color='#3498db', edgecolor='black', alpha=0.6)
                    if sd_val > 0: ax1_p.plot(x_curve, y_curve, color='red', linewidth=2)
                    ax1_p.set_title("1. Distribution", color='black', fontsize=9)
                    
                    ax2_p.plot(x_seq, weights, marker='o', color='#2ecc71', markersize=3)
                    ax2_p.axhline(y=mean_val, color='red', linestyle='--')
                    ax2_p.set_title("2. Run Chart", color='black', fontsize=9)

                    ax3_p.scatter(x_seq, weights, color='#f1c40f', edgecolor='black', s=20)
                    if sd_val > 0:
                        ax3_p.text(0.05, 0.90, f"r = {r_val:.3f}", transform=ax3_p.transAxes, color='black', weight='bold', fontsize=8)
                        ax3_p.plot(x_seq, p(x_seq), color='purple', linestyle=':')
                    ax3_p.set_title("3. Scatter Plot", color='black', fontsize=9)

                    bp_p = ax4_p.boxplot(weights, vert=False, patch_artist=True)
                    for patch in bp_p['boxes']: patch.set_facecolor('#9b59b6')
                    for median in bp_p['medians']: median.set(color='red', linewidth=2)
                    for flier in bp_p['fliers']: flier.set(marker='o', markerfacecolor='red', markeredgecolor='black', markersize=6)
                    
                    outlier_data_p = bp_p['fliers'][0].get_xdata()
                    for x_val in np.unique(outlier_data_p):
                        indices = [i+1 for i, w in enumerate(weights) if w == x_val]
                        label = ",".join([f"#{i}" for i in indices])
                        ax4_p.annotate(label, xy=(x_val, 1), xytext=(0, 8), textcoords='offset points', ha='center', va='bottom', color='red', fontsize=7, weight='bold')
                    ax4_p.set_title("4. Box Plot (Outliers)", color='black', fontsize=9)
                    ax4_p.set_yticks([])

                    pdf.savefig(pdf_fig)
                    plt.close(pdf_fig)

                    MAX_ROWS_PER_COL = 40
                    MAX_COLS_PER_PAGE = 4 
                    MAX_ITEMS_PER_PAGE = MAX_ROWS_PER_COL * MAX_COLS_PER_PAGE
                    pages_needed = math.ceil(n / MAX_ITEMS_PER_PAGE)
                    
                    for page_num in range(pages_needed):
                        data_fig = plt.figure(figsize=(8.27, 11.69), facecolor='white')
                        data_fig.text(0.5, 0.92, f"RAW DATA RECORD (Page {page_num+1}/{pages_needed})", fontsize=16, weight='bold', ha='center', color='black')
                        data_fig.text(0.1, 0.86, f"Part Number: {part_no}", fontsize=11, color='black')
                        
                        y_pos = 0.83
                        col_x = [0.10, 0.32, 0.54, 0.76] 
                        current_col = 0
                        start_idx = page_num * MAX_ITEMS_PER_PAGE
                        end_idx = min(start_idx + MAX_ITEMS_PER_PAGE, n)
                        
                        for i in range(start_idx, end_idx):
                            w = weights[i]
                            # PDF แสดงทศนิยม 2 ตำแหน่ง
                            data_fig.text(col_x[current_col], y_pos, f"#{i+1:03d}: {w:.2f}g", fontsize=10, fontfamily='monospace', color='black')
                            y_pos -= 0.018 
                            if y_pos < 0.08: 
                                y_pos = 0.83 
                                current_col += 1 
                                
                        pdf.savefig(data_fig)
                        plt.close(data_fig)

                st.download_button(
                    label="📥 Download PDF Report",
                    data=buffer.getvalue(),
                    file_name=f"Validation_{part_no}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

# -------------------- TAB 2: HISTORY LOGS --------------------
with tab2:
    st.header("🗄️ Validation History Database")
    history_file = "validation_history.csv"
    
    if os.path.isfile(history_file) and os.path.getsize(history_file) > 0:
        df_history = pd.read_csv(history_file)
        
        if df_history.empty:
            st.info("ยังไม่มีประวัติการตรวจสอบครับ (ข้อมูลว่างเปล่า)")
        else:
            search_part = st.text_input("🔍 Search by Part Number:")
            if search_part:
                df_display = df_history[df_history['Part Number'].astype(str).str.contains(search_part, case=False)]
            else:
                df_display = df_history
                
            st.write(f"พบข้อมูลทั้งหมด {len(df_display)} รายการ")
            
            def color_status(val):
                color = '#28a745' if val == 'PASSED' else '#dc3545'
                return f'color: {color}; font-weight: bold'
                
            st.dataframe(
                df_display.style.map(color_status, subset=['Status']), 
                use_container_width=True, 
                hide_index=True
            )
            
            csv = df_history.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 Download History to CSV",
                data=csv,
                file_name="Master_Validation_History.csv",
                mime="text/csv",
            )

            st.divider()
            with st.expander("🗑️ Data Management (จัดการลบข้อมูล)"):
                st.warning("⚠️ ระวัง: ข้อมูลที่ถูกลบจะไม่สามารถกู้คืนได้")
                
                col_del1, col_del2 = st.columns(2)
                
                with col_del1:
                    st.markdown("**ลบทีละรายการ (Delete Specific Record)**")
                    record_options = ["-- เลือกรายการที่ต้องการลบ --"] + (df_history['Timestamp'].astype(str) + " | Part: " + df_history['Part Number'].astype(str)).tolist()
                    selected_record = st.selectbox("เลือกรายการ:", record_options, label_visibility="collapsed")
                    
                    if st.button("🗑️ ลบรายการที่เลือก", type="primary"):
                        if selected_record != "-- เลือกรายการที่ต้องการลบ --":
                            target_timestamp = selected_record.split(" | ")[0]
                            df_history = df_history[df_history['Timestamp'] != target_timestamp]
                            df_history.to_csv(history_file, index=False, encoding='utf-8-sig')
                            st.success(f"✅ ลบข้อมูลเวลา {target_timestamp} สำเร็จ!")
                            st.rerun()
                            
                with col_del2:
                    st.markdown("**ลบข้อมูลทั้งหมด (Clear All History)**")
                    st.write("ปุ่มนี้จะทำการล้างประวัติทั้งหมดในระบบทันที")
                    if st.button("🚨 ล้างประวัติทั้งหมด (Clear All)", type="primary"):
                        os.remove(history_file)
                        st.success("✅ ล้างประวัติทั้งหมดเรียบร้อยแล้ว!")
                        st.rerun()

    else:

        st.info("ยังไม่มีประวัติการตรวจสอบครับ ลองกลับไปที่หน้า Dashboard แล้วกดปุ่ม 'Save Record to History' เพื่อเริ่มเก็บข้อมูลได้เลยครับ!")
