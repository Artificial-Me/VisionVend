import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import subprocess
import time
import json
from datetime import datetime
from dotenv import load_dotenv
from product_tracker import main as run_tracker
import supervision as sv
import torch
from trackers import SORTTracker, DeepSORTTracker
from urllib.request import urlretrieve
from huggingface_hub import login

class ProductTrackerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Product Tracker")
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar(value=os.path.join(os.path.dirname(__file__), "output"))
        self.metrics = {
            'processing_time': 0,
            'objects_tracked': 0,
            'fps': 0
        }
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(pady=10, padx=10, fill='both', expand=True)
        
        # Main tab
        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="Settings")
        
        # Metrics tab
        self.metrics_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.metrics_tab, text="Metrics")
        
        self.create_widgets()
        self.create_metrics_widgets()
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_widgets(self):
        # Input/Output section
        ttk.Label(self.main_tab, text="Input Video:").grid(row=0, column=0, sticky="e", pady=5)
        ttk.Entry(self.main_tab, textvariable=self.input_path, width=50).grid(row=0, column=1, pady=5)
        ttk.Button(self.main_tab, text="Browse", command=self.browse_input).grid(row=0, column=2, pady=5)

        ttk.Label(self.main_tab, text="Output Folder:").grid(row=1, column=0, sticky="e", pady=5)
        ttk.Entry(self.main_tab, textvariable=self.output_path, width=50).grid(row=1, column=1, pady=5)
        ttk.Button(self.main_tab, text="Browse", command=self.browse_output).grid(row=1, column=2, pady=5)

        # Tracker settings
        ttk.Label(self.main_tab, text="Tracker Type:").grid(row=2, column=0, sticky="e", pady=5)
        self.tracker_type = tk.StringVar(value="sort")
        ttk.Combobox(self.main_tab, textvariable=self.tracker_type, 
                    values=["sort", "deepsort"], state="readonly").grid(row=2, column=1, sticky="w", pady=5)

        # Tracking parameters
        ttk.Label(self.main_tab, text="Max Age:").grid(row=3, column=0, sticky="e", pady=5)
        self.max_age = tk.IntVar(value=1)
        ttk.Spinbox(self.main_tab, from_=1, to=30, textvariable=self.max_age).grid(row=3, column=1, sticky="w", pady=5)

        ttk.Label(self.main_tab, text="Min Hits:").grid(row=4, column=0, sticky="e", pady=5)
        self.min_hits = tk.IntVar(value=3)
        ttk.Spinbox(self.main_tab, from_=1, to=10, textvariable=self.min_hits).grid(row=4, column=1, sticky="w", pady=5)

        ttk.Label(self.main_tab, text="IOU Threshold:").grid(row=5, column=0, sticky="e", pady=5)
        self.iou_threshold = tk.DoubleVar(value=0.3)
        ttk.Spinbox(self.main_tab, from_=0.1, to=1.0, increment=0.1, 
                   textvariable=self.iou_threshold).grid(row=5, column=1, sticky="w", pady=5)

        # DeepSORT specific
        ttk.Label(self.main_tab, text="Appearance Threshold:").grid(row=6, column=0, sticky="e", pady=5)
        self.appearance_threshold = tk.DoubleVar(value=0.5)
        ttk.Spinbox(self.main_tab, from_=0.1, to=1.0, increment=0.1, 
                   textvariable=self.appearance_threshold).grid(row=6, column=1, sticky="w", pady=5)

        # Visualization options
        ttk.Label(self.main_tab, text="Visualization:").grid(row=7, column=0, sticky="e", pady=5)
        self.show_confidence = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.main_tab, text="Show Confidence", variable=self.show_confidence).grid(row=7, column=1, sticky="w", pady=5)
        
        self.show_class = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.main_tab, text="Show Class", variable=self.show_class).grid(row=8, column=1, sticky="w", pady=5)
        
        self.show_trajectories = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.main_tab, text="Show Trajectories", variable=self.show_trajectories).grid(row=9, column=1, sticky="w", pady=5)

        # Run button
        ttk.Button(self.main_tab, text="Run Tracker", command=self.run_tracker).grid(row=10, column=1, pady=10)

    def create_metrics_widgets(self):
        # Metrics display
        ttk.Label(self.metrics_tab, text="Performance Metrics", font=('Arial', 12)).grid(row=0, column=0, columnspan=2, pady=10)
        
        ttk.Label(self.metrics_tab, text="Processing Time:").grid(row=1, column=0, sticky="e", pady=5)
        self.time_label = ttk.Label(self.metrics_tab, text="0.00s")
        self.time_label.grid(row=1, column=1, sticky="w", pady=5)
        
        ttk.Label(self.metrics_tab, text="Objects Tracked:").grid(row=2, column=0, sticky="e", pady=5)
        self.objects_label = ttk.Label(self.metrics_tab, text="0")
        self.objects_label.grid(row=2, column=1, sticky="w", pady=5)
        
        ttk.Label(self.metrics_tab, text="Frames Per Second:").grid(row=3, column=0, sticky="e", pady=5)
        self.fps_label = ttk.Label(self.metrics_tab, text="0")
        self.fps_label.grid(row=3, column=1, sticky="w", pady=5)
        
        # Save metrics button
        ttk.Button(self.metrics_tab, text="Save Metrics", command=self.save_metrics).grid(row=4, column=0, columnspan=2, pady=10)

    def browse_input(self):
        file_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4;*.avi;*.mov")])
        if file_path:
            self.input_path.set(file_path)

    def browse_output(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_path.set(folder)

    def update_status(self, message):
        self.status_var.set(message)
        self.root.update_idletasks()
        
    def update_metrics(self, metrics):
        self.metrics = metrics
        self.time_label.config(text=f"{metrics['processing_time']:.2f}s")
        self.objects_label.config(text=str(metrics['objects_tracked']))
        self.fps_label.config(text=f"{metrics['fps']:.1f}")
        
    def save_metrics(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        if file_path:
            with open(file_path, 'w') as f:
                json.dump(self.metrics, f, indent=4)
            messagebox.showinfo("Success", f"Metrics saved to {file_path}")

    def run_tracker(self):
        self.update_status("Processing...")
        input_file = self.input_path.get()
        output_folder = self.output_path.get()
        
        if not input_file or not os.path.isfile(input_file):
            messagebox.showerror("Error", "Please select a valid video file.")
            return
            
        if not os.path.isdir(output_folder):
            os.makedirs(output_folder, exist_ok=True)
            
        # Get all parameters
        params = {
            'input_path': input_file,
            'output_dir': output_folder,
            'tracker_type': self.tracker_type.get(),
            'max_age': self.max_age.get(),
            'min_hits': self.min_hits.get(),
            'iou_threshold': self.iou_threshold.get(),
            'appearance_threshold': self.appearance_threshold.get(),
            'show_confidence': self.show_confidence.get(),
            'show_class': self.show_class.get(),
            'show_trajectories': self.show_trajectories.get()
        }
        
        # Disable button during processing
        self.run_button = self.main_tab.grid_slaves(row=10, column=1)[0]
        self.run_button.config(state=tk.DISABLED)
        
        def worker():
            start_time = time.time()
            try:
                # Run tracker and capture metrics
                result = run_tracker(**params)
                processing_time = time.time() - start_time
                
                # Calculate metrics (simplified example)
                metrics = {
                    'processing_time': processing_time,
                    'objects_tracked': result.get('objects_tracked', 0),
                    'fps': result.get('fps', 0),
                    'parameters': params,
                    'timestamp': datetime.now().isoformat()
                }
                
                self.root.after(0, lambda: self.update_metrics(metrics))
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
    root.geometry("600x500")
    app = ProductTrackerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
