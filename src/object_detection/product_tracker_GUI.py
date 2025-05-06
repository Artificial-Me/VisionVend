import tkinter as tk
from tkinter import filedialog, messagebox
import os
import subprocess
from dotenv import load_dotenv
from product_tracker import main as run_tracker
import supervision as sv
from transformers import RTDetrV2ForObjectDetection, RTDetrImageProcessor
import torch
from trackers import SORTTracker
from urllib.request import urlretrieve
from huggingface_hub import login


class ProductTrackerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Product Tracker")
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar(value=os.path.join(os.path.dirname(__file__), "output"))
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=3, column=0, columnspan=3, sticky=tk.EW, pady=(10,0))
        
        self.create_widgets()

    def create_widgets(self):
        tk.Label(self.root, text="Select .mp4 file:").grid(row=0, column=0, sticky="e")
        tk.Entry(self.root, textvariable=self.input_path, width=50).grid(row=0, column=1)
        tk.Button(self.root, text="Browse", command=self.browse_input).grid(row=0, column=2)

        tk.Label(self.root, text="Select output folder:").grid(row=1, column=0, sticky="e")
        tk.Entry(self.root, textvariable=self.output_path, width=50).grid(row=1, column=1)
        tk.Button(self.root, text="Browse", command=self.browse_output).grid(row=1, column=2)

        tk.Button(self.root, text="Run Tracker", command=self.run_tracker).grid(row=2, column=1, pady=10)

    def browse_input(self):
        file_path = filedialog.askopenfilename(filetypes=[("MP4 files", "*.mp4")])
        if file_path:
            self.input_path.set(file_path)

    def browse_output(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_path.set(folder)

    def update_status(self, message):
        self.status_var.set(message)
        self.root.update_idletasks()

    def run_tracker(self):
        self.update_status("Processing...")
        input_file = self.input_path.get()
        output_folder = self.output_path.get()
        if not input_file or not os.path.isfile(input_file):
            messagebox.showerror("Error", "Please select a valid .mp4 file.")
            return
        if not os.path.isdir(output_folder):
            os.makedirs(output_folder, exist_ok=True)
            
        # Disable button during processing
        self.run_button = self.root.grid_slaves(row=2, column=1)[0]
        self.run_button.config(state=tk.DISABLED)
        
        def worker():
            try:
                run_tracker(input_file, output_folder)
                self.root.after(0, lambda: messagebox.showinfo("Success", "Tracking completed!"))
                self.root.after(0, lambda: self.update_status("Done"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Tracking failed: {e}"))
                self.root.after(0, lambda: self.update_status("Error occurred"))
            finally:
                self.root.after(0, lambda: self.run_button.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.update_status("Ready"))
        
        import threading
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()

def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    root = tk.Tk()
    app = ProductTrackerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
