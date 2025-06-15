import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import pandas as pd
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SKUMapper:
    """
    A class to manage SKU to MSKU mappings and process sales data.
    """
    def __init__(self):
        self.sku_to_msku_map = {}
        self.processed_data = None
        logging.info("SKUMapper initialized.")

    def load_mapping(self, file_path):
        """
        Loads SKU to MSKU mapping from a CSV file.
        The CSV is expected to have 'SKU' and 'MSKU' columns.
        """
        if not file_path:
            logging.warning("No mapping file path provided.")
            raise ValueError("No mapping file path provided.")
        try:
            # Assuming the mapping file has 'SKU' and 'MSKU' columns
            mapping_df = pd.read_csv(file_path)
            if 'SKU' not in mapping_df.columns or 'MSKU' not in mapping_df.columns:
                raise ValueError("Mapping file must contain 'SKU' and 'MSKU' columns.")
            self.sku_to_msku_map = mapping_df.set_index('SKU')['MSKU'].to_dict()
            logging.info(f"Loaded {len(self.sku_to_msku_map)} SKU to MSKU mappings from {file_path}")
            return True
        except FileNotFoundError:
            logging.error(f"Mapping file not found: {file_path}")
            raise FileNotFoundError(f"Mapping file not found: {file_path}")
        except Exception as e:
            logging.error(f"Error loading mapping file {file_path}: {e}")
            raise ValueError(f"Error loading mapping file: {e}")

    def identify_and_map_sku(self, sku_value):
        """
        Identifies and maps a single SKU to its corresponding MSKU.
        Handles case insensitivity and basic cleaning.
        """
        if pd.isna(sku_value):
            return None # Return None for NaN or empty SKUs

        # Convert to string and clean up whitespace, convert to uppercase for consistency
        clean_sku = str(sku_value).strip().upper()

        if clean_sku in self.sku_to_msku_map:
            return self.sku_to_msku_map[clean_sku]
        else:
            logging.warning(f"SKU '{sku_value}' (cleaned: '{clean_sku}') not found in mapping. Returning original SKU.")
            return sku_value # Return original SKU if no mapping found

    def handle_combo_products(self, df, sku_column='SKU', combo_prefix='COMBO_'):
        """
        Identifies and processes combo products.
        Assumes combo SKUs start with a specific prefix.
        For simplicity, this example just assigns a generic 'COMBO_MSKU' if detected.
        More complex logic (e.g., breaking down combo into individual SKUs) would go here.
        """
        if sku_column not in df.columns:
            logging.warning(f"SKU column '{sku_column}' not found for combo product handling.")
            return df

        def _process_combo(sku):
            if pd.isna(sku):
                return sku
            if str(sku).strip().upper().startswith(combo_prefix):
                logging.info(f"Identified combo product SKU: {sku}")
                return f"{combo_prefix}MSKU" # Or more complex logic
            return sku

        df[sku_column] = df[sku_column].apply(_process_combo)
        logging.info("Combo product handling applied.")
        return df

    def process_sales_data(self, df, sku_column='SKU', msku_column='MSKU'):
        """
        Processes the sales data DataFrame to add an MSKU column.
        """
        if self.sku_to_msku_map is None or not self.sku_to_msku_map:
            logging.error("SKU to MSKU mapping is not loaded. Cannot process data.")
            raise ValueError("SKU to MSKU mapping is not loaded.")

        if sku_column not in df.columns:
            logging.error(f"SKU column '{sku_column}' not found in the sales data.")
            raise ValueError(f"SKU column '{sku_column}' not found in the sales data.")

        # Apply the mapping
        df[msku_column] = df[sku_column].apply(self.identify_and_map_sku)

        # Handle combo products (optional, can be integrated or called separately)
        # For this example, we apply it after initial mapping on the 'SKU' column
        # and then re-map or ensure the MSKU is updated if the SKU was a combo.
        # A more robust solution might handle combo parsing before MSKU assignment.
        df = self.handle_combo_products(df, sku_column=sku_column)
        df[msku_column] = df[sku_column].apply(self.identify_and_map_sku) # Re-apply after combo handling if needed

        self.processed_data = df
        logging.info("Sales data processed successfully with MSKU mapping.")
        return df

class WMSApp:
    """
    Graphical User Interface for the Warehouse Management System MVP.
    """
    def __init__(self, master):
        self.master = master
        master.title("WMS SKU Mapper MVP")
        master.geometry("800x600")
        master.configure(bg='#e0f2f7') # Light blue background

        self.sku_mapper = SKUMapper()
        self.sales_data_df = None
        self.processed_data_df = None

        # --- Styling ---
        button_style = {'bg': '#00796b', 'fg': 'white', 'font': ('Inter', 10, 'bold'), 'relief': 'raised', 'bd': 2, 'width': 20}
        label_style = {'bg': '#e0f2f7', 'fg': '#004d40', 'font': ('Inter', 10, 'bold')}
        frame_style = {'bg': '#e0f2f7', 'bd': 2, 'relief': 'groove'}

        # --- Frames ---
        self.top_frame = tk.Frame(master, **frame_style, padx=10, pady=10)
        self.top_frame.pack(pady=10, fill='x')

        self.middle_frame = tk.Frame(master, **frame_style, padx=10, pady=10)
        self.middle_frame.pack(pady=10, fill='both', expand=True)

        self.bottom_frame = tk.Frame(master, **frame_style, padx=10, pady=10)
        self.bottom_frame.pack(pady=10, fill='x')

        # --- Widgets in Top Frame ---
        tk.Label(self.top_frame, text="1. Load SKU to MSKU Mapping CSV:", **label_style).grid(row=0, column=0, sticky='w', pady=5)
        self.load_mapping_button = tk.Button(self.top_frame, text="Load Mapping File", command=self.load_mapping_file, **button_style)
        self.load_mapping_button.grid(row=0, column=1, padx=5, pady=5)
        self.mapping_status_label = tk.Label(self.top_frame, text="No mapping loaded", **label_style, fg='#d32f2f') # Red for error/status
        self.mapping_status_label.grid(row=0, column=2, sticky='w', padx=5)

        tk.Label(self.top_frame, text="2. Load Sales Data CSV:", **label_style).grid(row=1, column=0, sticky='w', pady=5)
        self.load_sales_button = tk.Button(self.top_frame, text="Load Sales Data", command=self.load_sales_file, **button_style)
        self.load_sales_button.grid(row=1, column=1, padx=5, pady=5)
        self.sales_status_label = tk.Label(self.top_frame, text="No sales data loaded", **label_style, fg='#d32f2f')
        self.sales_status_label.grid(row=1, column=2, sticky='w', padx=5)

        self.process_button = tk.Button(self.top_frame, text="3. Process Sales Data", command=self.process_data, **button_style)
        self.process_button.grid(row=2, column=1, padx=5, pady=10)
        self.process_button.config(state=tk.DISABLED) # Disabled until files are loaded

        # --- Widgets in Middle Frame (Log Area) ---
        tk.Label(self.middle_frame, text="Application Log:", **label_style).pack(anchor='w')
        self.log_text = scrolledtext.ScrolledText(self.middle_frame, wrap=tk.WORD, height=15, width=90, font=('Consolas', 9), bg='#f5f5f5', fg='#333333', bd=1, relief='sunken')
        self.log_text.pack(pady=5, fill='both', expand=True)
        self.log_text.config(state=tk.DISABLED) # Make it read-only

        # --- Widgets in Bottom Frame ---
        self.save_button = tk.Button(self.bottom_frame, text="4. Save Processed Data", command=self.save_processed_data, **button_style)
        self.save_button.pack(side='left', padx=5, pady=5)
        self.save_button.config(state=tk.DISABLED) # Disabled until data is processed

        self.exit_button = tk.Button(self.bottom_frame, text="Exit", command=master.quit, **button_style)
        self.exit_button.pack(side='right', padx=5, pady=5)

        self.log_message("Welcome to the WMS SKU Mapper MVP. Load mapping and sales data to begin.", level='info')

    def log_message(self, message, level='info'):
        """Appends a message to the GUI log area."""
        self.log_text.config(state=tk.NORMAL)
        if level == 'info':
            self.log_text.insert(tk.END, f"[INFO] {message}\n", 'info')
        elif level == 'warning':
            self.log_text.insert(tk.END, f"[WARNING] {message}\n", 'warning')
        elif level == 'error':
            self.log_text.insert(tk.END, f"[ERROR] {message}\n", 'error')
        self.log_text.tag_config('info', foreground='blue')
        self.log_text.tag_config('warning', foreground='orange')
        self.log_text.tag_config('error', foreground='red')
        self.log_text.see(tk.END) # Scroll to the end
        self.log_text.config(state=tk.DISABLED)

    def load_mapping_file(self):
        """Allows user to select and load the SKU to MSKU mapping file."""
        file_path = filedialog.askopenfilename(
            title="Select SKU to MSKU Mapping File",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx *.xls")]
        )
        if file_path:
            try:
                self.sku_mapper.load_mapping(file_path)
                self.mapping_status_label.config(text=f"Mapping loaded: {os.path.basename(file_path)}", fg='#2e7d32') # Green success
                self.log_message(f"Successfully loaded mapping from {os.path.basename(file_path)}")
                self._check_enable_process_button()
            except Exception as e:
                self.mapping_status_label.config(text="Error loading mapping!", fg='#d32f2f')
                self.log_message(f"Failed to load mapping: {e}", level='error')
                messagebox.showerror("Error", f"Failed to load mapping: {e}")
        else:
            self.log_message("Mapping file selection cancelled.", level='warning')

    def load_sales_file(self):
        """Allows user to select and load the sales data file."""
        file_path = filedialog.askopenfilename(
            title="Select Sales Data File",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx *.xls")]
        )
        if file_path:
            try:
                # Read the file based on its extension
                if file_path.endswith('.csv'):
                    self.sales_data_df = pd.read_csv(file_path)
                elif file_path.endswith('.xlsx') or file_path.endswith('.xls'):
                    self.sales_data_df = pd.read_excel(file_path)
                else:
                    raise ValueError("Unsupported file type. Please select a CSV or Excel file.")

                self.sales_status_label.config(text=f"Sales data loaded: {os.path.basename(file_path)}", fg='#2e7d32')
                self.log_message(f"Successfully loaded sales data from {os.path.basename(file_path)}. Rows: {len(self.sales_data_df)}")
                self._check_enable_process_button()
            except Exception as e:
                self.sales_status_label.config(text="Error loading sales data!", fg='#d32f2f')
                self.log_message(f"Failed to load sales data: {e}", level='error')
                messagebox.showerror("Error", f"Failed to load sales data: {e}")
        else:
            self.log_message("Sales data file selection cancelled.", level='warning')

    def _check_enable_process_button(self):
        """Enables the process button if both mapping and sales data are loaded."""
        if self.sku_mapper.sku_to_msku_map and self.sales_data_df is not None:
            self.process_button.config(state=tk.NORMAL)
            self.log_message("Ready to process data. Click 'Process Sales Data'.")
        else:
            self.process_button.config(state=tk.DISABLED)

    def process_data(self):
        """Processes the loaded sales data using the SKU mapper."""
        if self.sales_data_df is None:
            self.log_message("No sales data loaded to process.", level='warning')
            messagebox.showwarning("Warning", "Please load sales data first.")
            return
        if not self.sku_mapper.sku_to_msku_map:
            self.log_message("No SKU to MSKU mapping loaded.", level='warning')
            messagebox.showwarning("Warning", "Please load SKU to MSKU mapping file first.")
            return

        try:
            # Create a copy to avoid modifying the original loaded DataFrame directly
            df_to_process = self.sales_data_df.copy()
            self.processed_data_df = self.sku_mapper.process_sales_data(df_to_process)
            self.log_message("Sales data processing complete. 'MSKU' column added/updated.")
            self.save_button.config(state=tk.NORMAL) # Enable save button
            messagebox.showinfo("Success", "Sales data processed successfully! You can now save the results.")
        except ValueError as ve:
            self.log_message(f"Processing error: {ve}", level='error')
            messagebox.showerror("Error", f"Processing error: {ve}\nPlease ensure your sales data has a 'SKU' column.")
        except Exception as e:
            self.log_message(f"An unexpected error occurred during processing: {e}", level='error')
            messagebox.showerror("Error", f"An unexpected error occurred during processing: {e}")

    def save_processed_data(self):
        """Saves the processed data to a new CSV file."""
        if self.processed_data_df is None:
            self.log_message("No processed data to save.", level='warning')
            messagebox.showwarning("Warning", "No processed data available. Please process data first.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx")],
            title="Save Processed Sales Data As"
        )
        if file_path:
            try:
                if file_path.endswith('.csv'):
                    self.processed_data_df.to_csv(file_path, index=False)
                elif file_path.endswith('.xlsx'):
                    self.processed_data_df.to_excel(file_path, index=False)
                self.log_message(f"Processed data saved to {os.path.basename(file_path)}")
                messagebox.showinfo("Success", f"Processed data saved to:\n{file_path}")
            except Exception as e:
                self.log_message(f"Failed to save processed data: {e}", level='error')
                messagebox.showerror("Error", f"Failed to save processed data: {e}")
        else:
            self.log_message("Save operation cancelled.", level='warning')

if __name__ == "__main__":
    root = tk.Tk()
    app = WMSApp(root)
    root.mainloop()