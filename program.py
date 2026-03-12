import customtkinter as ctk
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_pdf import PdfPages
from tkinter import messagebox, filedialog
import statistics
import math

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ProValidationApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Scale Counting Validation v7.6 - Smart Outlier Tagging")
        self.geometry("1400x950") 
        self.weights = []

        self.grid_columnconfigure(0, weight=1) 
        self.grid_columnconfigure(1, weight=3) 
        self.grid_rowconfigure(0, weight=1)

        # ==================== LEFT PANEL (INPUTS) ====================
        self.left_panel = ctk.CTkFrame(self, corner_radius=15, fg_color="#212121")
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        self.left_panel.grid_rowconfigure(6, weight=1) 

        ctk.CTkLabel(self.left_panel, text="📋 Project Config", font=("Helvetica", 22, "bold"), text_color="#4da6ff").grid(row=0, column=0, pady=(20, 10))

        self.config_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.config_frame.grid(row=1, column=0, sticky="ew", padx=15)

        self.part_entry = self.create_input(self.config_frame, "Part Number:", "")
        self.qty_entry = self.create_input(self.config_frame, "Sample Size (Target):", "30")
        self.snp_entry = self.create_input(self.config_frame, "Full SNP (pcs/pack):", "100") 
        
        ctk.CTkFrame(self.left_panel, height=2, fg_color="#333333").grid(row=2, column=0, sticky="ew", padx=20, pady=10)

        ctk.CTkLabel(self.left_panel, text="⚖️ Weight Input (g)", font=("Helvetica", 16, "bold")).grid(row=3, column=0, pady=(5,0))
        self.weight_entry = ctk.CTkEntry(self.left_panel, height=45, font=("Helvetica", 22, "bold"), justify="center", placeholder_text="0.000")
        self.weight_entry.grid(row=4, column=0, sticky="ew", padx=20, pady=10)
        self.weight_entry.bind("<Return>", lambda e: self.add_weight())

        self.input_btn_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.input_btn_frame.grid(row=5, column=0, sticky="ew", padx=20, pady=5)
        self.input_btn_frame.grid_columnconfigure((0, 1), weight=1)

        self.btn_add = ctk.CTkButton(self.input_btn_frame, text="Enter Data", height=40, font=("Helvetica", 14, "bold"), command=self.add_weight, fg_color="#28a745", hover_color="#218838")
        self.btn_add.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        self.btn_upload = ctk.CTkButton(self.input_btn_frame, text="📁 Excel Upload", height=40, font=("Helvetica", 14, "bold"), command=self.upload_excel, fg_color="#2980b9", hover_color="#3498db")
        self.btn_upload.grid(row=0, column=1, sticky="ew", padx=(5, 0))

        self.list_frame = ctk.CTkScrollableFrame(self.left_panel, fg_color="#1a1a1a")
        self.list_frame.grid(row=6, column=0, sticky="nsew", padx=15, pady=15)

        # ==================== RIGHT PANEL (DASHBOARD) ====================
        self.right_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 15), pady=15)
        self.right_panel.grid_rowconfigure(3, weight=1) 
        self.right_panel.grid_columnconfigure(0, weight=1)

        self.top_bar = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        
        self.btn_exit = ctk.CTkButton(self.top_bar, text="❌ Exit", command=self.quit, fg_color="#7f8c8d", hover_color="#95a5a6", font=("Helvetica", 14, "bold"), height=40, width=100)
        self.btn_exit.pack(side="right", padx=5)

        self.btn_pdf = ctk.CTkButton(self.top_bar, text="📄 Print Report", command=self.generate_pdf, fg_color="#d35400", hover_color="#e67e22", font=("Helvetica", 14, "bold"), height=40)
        self.btn_pdf.pack(side="right", padx=5)
        self.btn_reset = ctk.CTkButton(self.top_bar, text="🔄 Reset", command=self.reset_data, fg_color="#c0392b", hover_color="#e74c3c", font=("Helvetica", 14, "bold"), height=40)
        self.btn_reset.pack(side="right", padx=5)

        self.status_bar = ctk.CTkLabel(self.right_panel, text="WAITING FOR DATA", font=("Helvetica", 24, "bold"), text_color="white", fg_color="#555555", height=50, corner_radius=10)
        self.status_bar.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        self.stats_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.stats_frame.grid(row=2, column=0, sticky="ew")
        self.stats_frame.grid_columnconfigure((0,1,2,3), weight=1)

        self.card_count = self.create_stat_card(self.stats_frame, "Total Data Count", "0 pcs", 0)
        self.card_mean = self.create_stat_card(self.stats_frame, "Average (APW)", "0.000 g", 1)
        self.card_cv = self.create_stat_card(self.stats_frame, "%CV (Precision)", "0.00 %", 2)
        self.card_risk = self.create_stat_card(self.stats_frame, "Max Error @ Full SNP", "0.00 pcs", 3) 

        self.charts_frame = ctk.CTkFrame(self.right_panel, corner_radius=15, fg_color="#212121")
        self.charts_frame.grid(row=3, column=0, sticky="nsew", pady=10)
        
        self.fig, ((self.ax1, self.ax2), (self.ax3, self.ax4)) = plt.subplots(2, 2, figsize=(10, 5), dpi=100)
        self.fig.patch.set_facecolor('#212121')
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.charts_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        
        self.bottom_stats_frame = ctk.CTkFrame(self.right_panel, fg_color="#1a1a1a", corner_radius=10)
        self.bottom_stats_frame.grid(row=4, column=0, sticky="ew", pady=(10,0))
        self.bottom_stats_frame.grid_columnconfigure((0,1,2), weight=1)

        self.lbl_min = self.create_bottom_stat(self.bottom_stats_frame, "⬇️ MIN Weight", "0.0000 g", 0, "#3498db")
        self.lbl_max = self.create_bottom_stat(self.bottom_stats_frame, "⬆️ MAX Weight", "0.0000 g", 1, "#e67e22") 
        self.lbl_std = self.create_bottom_stat(self.bottom_stats_frame, "📊 STD (Standard Deviation)", "0.0000", 2, "#f1c40f")

        self.update_charts()

    def create_input(self, parent, label_text, default_val):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=5)
        ctk.CTkLabel(frame, text=label_text, font=("Helvetica", 13)).pack(anchor="w")
        entry = ctk.CTkEntry(frame, height=32)
        entry.pack(fill="x")
        if default_val: entry.insert(0, default_val)
        return entry

    def create_stat_card(self, parent, title, value, col):
        card = ctk.CTkFrame(parent, corner_radius=10, fg_color="#2b2b2b", height=90)
        card.grid(row=0, column=col, padx=5, sticky="nsew")
        card.grid_propagate(False)
        ctk.CTkLabel(card, text=title, font=("Helvetica", 14), text_color="#aaaaaa").pack(pady=(10, 5))
        val_label = ctk.CTkLabel(card, text=value, font=("Helvetica", 22, "bold"), text_color="#ffffff")
        val_label.pack()
        return val_label

    def create_bottom_stat(self, parent, title, value, col, color):
        frame = ctk.CTkFrame(parent, fg_color="transparent", height=60)
        frame.grid(row=0, column=col, pady=10, sticky="nsew")
        ctk.CTkLabel(frame, text=title, font=("Helvetica", 14), text_color="#aaaaaa").pack(side="top")
        val_label = ctk.CTkLabel(frame, text=value, font=("Helvetica", 20, "bold"), text_color=color)
        val_label.pack(side="top")
        return val_label

    def add_weight(self):
        try:
            val = float(self.weight_entry.get())
            self.weights.append(val)
            self.weight_entry.delete(0, 'end')
            self.update_dashboard()
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number.")

    def upload_excel(self):
        file_path = filedialog.askopenfilename(
            title="Select Excel/CSV File",
            filetypes=(("Excel files", "*.xlsx *.xls"), ("CSV files", "*.csv"), ("All files", "*.*"))
        )
        if not file_path: return

        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path, header=None)
            else:
                df = pd.read_excel(file_path, header=None)
            
            new_weights = []
            for col in df.columns:
                numeric_col = pd.to_numeric(df[col], errors='coerce').dropna()
                if not numeric_col.empty:
                    new_weights.extend(numeric_col.tolist())
                    break 
            
            if not new_weights:
                messagebox.showerror("Error", "No numeric data found in the file.")
                return
            
            self.weights.extend(new_weights)
            self.update_dashboard()
            messagebox.showinfo("Success", f"Imported {len(new_weights)} records successfully.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to read file:\n{str(e)}")

    def delete_item(self, index):
        if 0 <= index < len(self.weights):
            self.weights.pop(index)
            self.update_dashboard()

    def update_dashboard(self):
        for widget in self.list_frame.winfo_children(): widget.destroy()
            
        for i, w in enumerate(self.weights):
            row_frame = ctk.CTkFrame(self.list_frame, fg_color="#2b2b2b", corner_radius=5)
            row_frame.pack(fill="x", pady=2, padx=2)
            ctk.CTkLabel(row_frame, text=f"#{i+1:02d}", font=("Consolas", 14), width=40).pack(side="left", padx=5)
            ctk.CTkLabel(row_frame, text=f"{w:.4f} g", font=("Consolas", 14, "bold")).pack(side="left", padx=10)
            btn_del = ctk.CTkButton(row_frame, text="🗑️", width=30, height=24, fg_color="#dc3545", hover_color="#c82333", command=lambda idx=i: self.delete_item(idx))
            btn_del.pack(side="right", padx=5, pady=2)

        if len(self.weights) > 0:
            self.after(50, lambda: self.list_frame._parent_canvas.yview_moveto(1.0))

        n = len(self.weights)
        try:
            target = int(self.qty_entry.get())
            snp = int(self.snp_entry.get())
        except ValueError:
            target, snp = 0, 100

        if target > 0 and n >= target:
            self.card_count.configure(text=f"{n} pcs\n(COMPLETED)", text_color="#2ecc71")
        elif n > 0:
            self.card_count.configure(text=f"{n} pcs", text_color="#4da6ff")
        else:
            self.card_count.configure(text="0 pcs", text_color="#4da6ff")

        if n >= 2:
            mean_val = statistics.mean(self.weights)
            sd_val = statistics.stdev(self.weights)
            cv_val = (sd_val / mean_val) * 100 if mean_val != 0 else 0
            
            error_in_pieces = (3 * math.sqrt(snp) * sd_val) / mean_val if mean_val != 0 else 0

            self.card_mean.configure(text=f"{mean_val:.4f} g")
            self.card_cv.configure(text=f"{cv_val:.2f} %")
            self.lbl_min.configure(text=f"{min(self.weights):.4f} g")
            self.lbl_max.configure(text=f"{max(self.weights):.4f} g")
            self.lbl_std.configure(text=f"{sd_val:.4f}")

            if error_in_pieces <= 0.5:
                risk_color = "#28a745"
                self.status_bar.configure(text="STATUS: PASSED (No Risk of Miscount)", fg_color=risk_color)
            else:
                risk_color = "#e74c3c"
                self.status_bar.configure(text="STATUS: FAILED (High Risk of Miscount!)", fg_color=risk_color)

            self.card_risk.configure(text=f"± {error_in_pieces:.2f} pcs", text_color=risk_color)
        else:
            self.card_mean.configure(text="0.000 g")
            self.card_cv.configure(text="0.00 %")
            self.card_risk.configure(text="0.00 pcs", text_color="#aaaaaa")
            self.lbl_min.configure(text="0.0000 g")
            self.lbl_max.configure(text="0.0000 g")
            self.lbl_std.configure(text="0.0000")
            self.status_bar.configure(text="WAITING FOR DATA", fg_color="#555555")

        self.update_charts()

    def update_charts(self):
        for ax in [self.ax1, self.ax2, self.ax3, self.ax4]:
            ax.clear()
            ax.set_facecolor('#2b2b2b')
            ax.tick_params(colors='#aaaaaa', labelsize=8)
            for spine in ax.spines.values(): spine.set_color('#555555')

        if len(self.weights) > 1:
            mean_val = np.mean(self.weights)
            sd_val = statistics.stdev(self.weights) if len(self.weights) > 1 else 0
            x_seq = list(range(1, len(self.weights)+1))
            
            self.ax1.hist(self.weights, bins=max(5, int(len(self.weights)**0.5)), density=True, color='#3498db', edgecolor='#212121', alpha=0.6)
            if sd_val > 0:
                x_curve = np.linspace(min(self.weights)-sd_val, max(self.weights)+sd_val, 100)
                y_curve = (1/(sd_val * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x_curve - mean_val)/sd_val)**2)
                self.ax1.plot(x_curve, y_curve, color='#e74c3c', linewidth=2)
            self.ax1.set_title("1. Distribution / Bell Curve\n[Consistency Check]", color='white', fontname='Helvetica', fontsize=10)
            
            self.ax2.plot(x_seq, self.weights, marker='o', color='#2ecc71', linewidth=1.5, alpha=0.8, markersize=4)
            self.ax2.axhline(y=mean_val, color='#e74c3c', linestyle='--', alpha=0.7)
            self.ax2.set_title("2. Run Chart\n[Trend & Stability Check]", color='white', fontname='Helvetica', fontsize=10)

            self.ax3.scatter(x_seq, self.weights, color='#f1c40f', edgecolor='#212121', s=40, zorder=5)
            if len(self.weights) > 1 and sd_val > 0:
                r_matrix = np.corrcoef(x_seq, self.weights)
                r_val = r_matrix[0, 1] if not np.isnan(r_matrix[0, 1]) else 0
                z = np.polyfit(x_seq, self.weights, 1)
                p = np.poly1d(z)
                self.ax3.plot(x_seq, p(x_seq), color='#9b59b6', linestyle=':', linewidth=2)
                self.ax3.text(0.05, 0.90, f"Correlation (r) = {r_val:.3f}", transform=self.ax3.transAxes, color='#f1c40f', fontsize=10, weight='bold', bbox=dict(facecolor='#212121', alpha=0.8, edgecolor='none'))
            self.ax3.set_title("3. Scatter Plot & Correlation\n[Dispersion & Drift Check]", color='white', fontname='Helvetica', fontsize=10)

            bp = self.ax4.boxplot(self.weights, vert=False, patch_artist=True)
            for patch in bp['boxes']: patch.set_facecolor('#9b59b6')
            for median in bp['medians']: median.set(color='red', linewidth=2)
            for flier in bp['fliers']: 
                flier.set(marker='o', markerfacecolor='#ff3333', markeredgecolor='white', markersize=10, alpha=1.0)
            
            # --- NEW: ติดป้ายระบุชิ้นงานที่เป็น Outlier ---
            outlier_data = bp['fliers'][0].get_xdata()
            for x_val in np.unique(outlier_data):
                # หาว่าน้ำหนักที่เป็น Outlier นี้ ตรงกับชิ้นงานเบอร์อะไรบ้าง
                indices = [i+1 for i, w in enumerate(self.weights) if w == x_val]
                label = ",".join([f"#{i:02d}" for i in indices])
                
                # พิมพ์ป้ายแปะเหนือจุดแดง
                self.ax4.annotate(label, xy=(x_val, 1), xytext=(0, 12), textcoords='offset points',
                                  ha='center', va='bottom', color='#ff3333', fontsize=10, weight='bold',
                                  bbox=dict(boxstyle='round,pad=0.2', fc='#2b2b2b', ec='none', alpha=0.8))

            self.ax4.set_title("4. Box Plot\n[Outliers Detection]", color='white', fontname='Helvetica', fontsize=10)
            self.ax4.set_yticks([])

        self.fig.tight_layout(pad=2.0)
        self.canvas.draw()

    def generate_pdf(self):
        if len(self.weights) < 2: return
        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=f"Validation_{self.part_entry.get()}.pdf")
        if not file_path: return

        mean_val = statistics.mean(self.weights)
        sd_val = statistics.stdev(self.weights)
        snp = int(self.snp_entry.get()) if self.snp_entry.get().isdigit() else 100
        error_pieces = (3 * math.sqrt(snp) * sd_val) / mean_val if mean_val != 0 else 0
        status = "PASSED" if error_pieces <= 0.5 else "FAILED (Miscount Risk)"

        pdf_fig = plt.figure(figsize=(8.27, 11.69), facecolor='white')
        
        pdf_fig.text(0.5, 0.94, "ZERO DEFECT: SCALE VALIDATION REPORT", fontsize=18, weight='bold', ha='center')
        pdf_fig.text(0.1, 0.89, f"Part Number: {self.part_entry.get()}", fontsize=12)
        pdf_fig.text(0.1, 0.86, f"Sample Size: {len(self.weights)} pcs", fontsize=12)
        pdf_fig.text(0.55, 0.89, f"Full SNP Target: {snp} pcs/pack", fontsize=12, weight='bold')
        pdf_fig.add_artist(plt.Line2D((0.1, 0.92), (0.9, 0.92), color='black', linewidth=1.5))

        pdf_fig.text(0.1, 0.80, "Analysis Result:", fontsize=14, weight='bold')
        pdf_fig.text(0.15, 0.77, f"- Average Piece Weight (APW) : {mean_val:.4f} g", fontsize=12)
        pdf_fig.text(0.15, 0.74, f"- Standard Deviation (STD)   : {sd_val:.4f}", fontsize=12)
        pdf_fig.text(0.15, 0.71, f"- Min / Max Weight           : {min(self.weights):.4f} g / {max(self.weights):.4f} g", fontsize=12)
        pdf_fig.text(0.15, 0.68, f"- Max Cumulative Error @ SNP : +/- {error_pieces:.2f} pieces", fontsize=12, weight='bold', color='red' if error_pieces > 0.5 else 'green')
        pdf_fig.text(0.15, 0.63, f"Conclusion: {status}", fontsize=16, weight='bold', color='red' if error_pieces > 0.5 else 'green')

        ax1 = pdf_fig.add_axes([0.1, 0.38, 0.35, 0.15]) 
        ax2 = pdf_fig.add_axes([0.55, 0.38, 0.35, 0.15])
        ax3 = pdf_fig.add_axes([0.1, 0.15, 0.35, 0.15])
        ax4 = pdf_fig.add_axes([0.55, 0.15, 0.35, 0.15])

        ax1.hist(self.weights, bins=max(5, int(len(self.weights)**0.5)), density=True, color='#3498db', edgecolor='black', alpha=0.6)
        if sd_val > 0:
            x_curve = np.linspace(min(self.weights)-sd_val, max(self.weights)+sd_val, 100)
            y_curve = (1/(sd_val * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x_curve - mean_val)/sd_val)**2)
            ax1.plot(x_curve, y_curve, color='red', linewidth=2)
        ax1.set_title("1. Distribution (Bell Curve)\n[Consistency Check]", fontsize=9)
        
        ax2.plot(range(1, len(self.weights)+1), self.weights, marker='o', color='#2ecc71', markersize=3)
        ax2.axhline(y=mean_val, color='red', linestyle='--')
        ax2.set_title("2. Run Chart\n[Trend Check]", fontsize=9)

        ax3.scatter(range(1, len(self.weights)+1), self.weights, color='#f1c40f', edgecolor='black')
        if sd_val > 0:
            r_matrix = np.corrcoef(range(1, len(self.weights)+1), self.weights)
            r_val = r_matrix[0, 1] if not np.isnan(r_matrix[0, 1]) else 0
            ax3.text(0.05, 0.90, f"r = {r_val:.3f}", transform=ax3.transAxes, color='black', weight='bold')
            z = np.polyfit(range(1, len(self.weights)+1), self.weights, 1)
            p = np.poly1d(z)
            ax3.plot(range(1, len(self.weights)+1), p(range(1, len(self.weights)+1)), color='purple', linestyle=':')
        ax3.set_title("3. Scatter Plot\n[Dispersion & Drift Check]", fontsize=9)

        bp = ax4.boxplot(self.weights, vert=False, patch_artist=True)
        for patch in bp['boxes']: patch.set_facecolor('#9b59b6')
        for median in bp['medians']: median.set(color='red', linewidth=2)
        for flier in bp['fliers']: 
            flier.set(marker='o', markerfacecolor='red', markeredgecolor='black', markersize=8, alpha=1.0)
        
        # --- NEW: ระบุ Outlier ในไฟล์ PDF ด้วย ---
        outlier_data = bp['fliers'][0].get_xdata()
        for x_val in np.unique(outlier_data):
            indices = [i+1 for i, w in enumerate(self.weights) if w == x_val]
            label = ",".join([f"#{i:02d}" for i in indices])
            ax4.annotate(label, xy=(x_val, 1), xytext=(0, 10), textcoords='offset points',
                         ha='center', va='bottom', color='red', fontsize=8, weight='bold')

        ax4.set_title("4. Box Plot\n[Outliers Detection]", fontsize=9)
        ax4.set_yticks([])

        with PdfPages(file_path) as pdf:
            pdf.savefig(pdf_fig)
            plt.close(pdf_fig)
            
            MAX_ROWS_PER_COL = 30
            MAX_COLS_PER_PAGE = 3
            MAX_ITEMS_PER_PAGE = MAX_ROWS_PER_COL * MAX_COLS_PER_PAGE
            
            total_items = len(self.weights)
            pages_needed = math.ceil(total_items / MAX_ITEMS_PER_PAGE)
            
            for page_num in range(pages_needed):
                data_fig = plt.figure(figsize=(8.27, 11.69), facecolor='white')
                data_fig.text(0.5, 0.92, f"RAW DATA RECORD (Page {page_num+1}/{pages_needed})", fontsize=18, weight='bold', ha='center')
                data_fig.text(0.1, 0.86, f"Part Number: {self.part_entry.get()}", fontsize=12)
                data_fig.add_artist(plt.Line2D((0.1, 0.88), (0.84, 0.84), color='black'))
                
                y_pos = 0.80
                col_x = [0.15, 0.45, 0.75]
                current_col = 0
                
                start_idx = page_num * MAX_ITEMS_PER_PAGE
                end_idx = min(start_idx + MAX_ITEMS_PER_PAGE, total_items)
                
                for i in range(start_idx, end_idx):
                    w = self.weights[i]
                    data_fig.text(col_x[current_col], y_pos, f"Sample #{i+1:03d} :  {w:.4f} g", fontsize=12, fontfamily='monospace')
                    y_pos -= 0.023
                    
                    if y_pos < 0.1:
                        y_pos = 0.80
                        current_col += 1
                        
                pdf.savefig(data_fig)
                plt.close(data_fig)

        messagebox.showinfo("Success", "Report Generated Successfully!\nสร้างรายงาน PDF พร้อมข้อมูลดิบเรียบร้อยแล้ว")

    def reset_data(self):
        if messagebox.askyesno("Confirm", "Clear all data?"):
            self.weights = []
            self.update_dashboard()

if __name__ == "__main__":
    app = ProValidationApp()
    app.mainloop()