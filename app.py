import customtkinter as ctk
import tkinter as tk
import threading
import time
import uvicorn
from typing import Dict, Any

from gui_client import api_client
from local_llm_backend.main import app as fastapi_app

def run_backend():
    """Runs the FastAPI backend in a uvicorn server."""
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8000)

class MinerManagerWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Miner Configuration Manager")
        self.geometry("500x400")
        self.master_app = master
        self.config = self.master_app.config # Use config from master app
        self.miner_names = [m['name'] for m in self.config.get('miners', [])]
        self.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self, text="Select Miner:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.miner_selector = ctk.CTkOptionMenu(self, values=["Add New Miner"] + self.miner_names, command=self.on_miner_selected)
        self.miner_selector.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.entries = {}
        fields = ["name", "miner_path", "wallet", "pool", "coin", "worker", "device"]
        for i, field in enumerate(fields):
            ctk.CTkLabel(self, text=f"{field.replace('_', ' ').title()}:").grid(row=i+1, column=0, padx=10, pady=5, sticky="w")
            entry = ctk.CTkEntry(self)
            entry.grid(row=i+1, column=1, padx=10, pady=5, sticky="ew")
            self.entries[field] = entry
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=len(fields)+1, column=0, columnspan=2, padx=10, pady=10)
        self.save_button = ctk.CTkButton(button_frame, text="Save", command=self.save_miner)
        self.save_button.pack(side="left", padx=10)
        self.delete_button = ctk.CTkButton(button_frame, text="Delete", command=self.delete_miner, fg_color="#D32F2F", hover_color="#E57373")
        self.delete_button.pack(side="left", padx=10)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.on_miner_selected("Add New Miner")

    def on_miner_selected(self, selection):
        if selection == "Add New Miner":
            for entry in self.entries.values(): entry.delete(0, tk.END)
            self.delete_button.configure(state="disabled")
        else:
            miner_data = next((m for m in self.config.get('miners', []) if m['name'] == selection), None)
            if miner_data:
                for field, entry in self.entries.items():
                    entry.delete(0, tk.END)
                    entry.insert(0, str(miner_data.get(field, "")))
                self.delete_button.configure(state="normal")

    def save_miner(self):
        selected_name = self.miner_selector.get()
        new_data = {field: entry.get() for field, entry in self.entries.items()}
        if new_data.get('device'):
            try: new_data['device'] = int(new_data['device'])
            except (ValueError, TypeError): new_data['device'] = None
        else:
            new_data['device'] = None
        full_config = self.master_app.config.copy()
        if selected_name == "Add New Miner":
            full_config.get('miners', []).append(new_data)
        else:
            full_config['miners'] = [new_data if m['name'] == selected_name else m for m in full_config.get('miners', [])]
        updated_config = api_client.update_config(full_config)
        if updated_config:
            self.master_app.config = updated_config
            self.refresh_selectors()

    def delete_miner(self):
        selected_name = self.miner_selector.get()
        if selected_name != "Add New Miner":
            full_config = self.master_app.config.copy()
            full_config['miners'] = [m for m in full_config.get('miners', []) if m['name'] != selected_name]
            updated_config = api_client.update_config(full_config)
            if updated_config:
                self.master_app.config = updated_config
                self.refresh_selectors()

    def refresh_selectors(self):
        self.config = self.master_app.config
        self.miner_names = [m['name'] for m in self.config.get('miners', [])]
        self.miner_selector.configure(values=["Add New Miner"] + self.miner_names)
        self.miner_selector.set("Add New Miner")
        self.on_miner_selected("Add New Miner")

    def on_close(self):
        self.master_app.miner_manager_window = None
        self.master_app.refresh_miner_list()
        self.destroy()

class LocalLLMApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Local LLM Controller")
        self.geometry("1000x600")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.config: Dict[str, Any] = {}
        self.miner_widgets = {}
        self.miner_manager_window = None
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.tab_view.add("AI"); self.tab_view.add("Crypto"); self.tab_view.add("Dashboard")
        self.create_ai_tab(self.tab_view.tab("AI"))
        self.create_crypto_tab(self.tab_view.tab("Crypto"))
        self.create_dashboard_tab(self.tab_view.tab("Dashboard"))
        self.load_initial_data()

    def load_initial_data(self):
        self.config = api_client.get_config()
        if not self.config:
            print("Error: Could not load configuration from backend.")
            self.config = {"miners": [], "llm": {"provider": "unknown"}}
        self.refresh_miner_list()
        self.refresh_recipe_list()
        self.update_dashboard()
        self.update_crypto_tab()

    def create_ai_tab(self, tab):
        tab.grid_columnconfigure(0, weight=2)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(2, weight=1)
        left_frame = ctk.CTkFrame(tab)
        left_frame.grid(row=0, column=0, rowspan=3, padx=(10, 5), pady=10, sticky="nsew")
        left_frame.grid_rowconfigure(1, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)
        self.prompt_textbox = ctk.CTkTextbox(left_frame)
        self.prompt_textbox.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.prompt_textbox.insert("0.0", "Enter your prompt here...")
        run_button = ctk.CTkButton(left_frame, text="Run LLM", command=self.run_llm)
        run_button.grid(row=1, column=0, padx=10, pady=10, sticky="sw")
        self.output_textbox = ctk.CTkTextbox(left_frame, state="disabled")
        self.output_textbox.grid(row=2, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="nsew")
        recipe_frame = ctk.CTkFrame(tab)
        recipe_frame.grid(row=0, column=1, rowspan=3, padx=(5, 10), pady=10, sticky="nsew")
        recipe_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(recipe_frame, text="Recipes").grid(row=0, column=0, padx=10, pady=10)
        self.recipe_menu = ctk.CTkOptionMenu(recipe_frame, values=[], command=self.load_recipe)
        self.recipe_menu.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

    def run_llm(self):
        prompt = self.prompt_textbox.get("1.0", tk.END)
        self.output_textbox.configure(state="normal")
        self.output_textbox.delete("1.0", tk.END)
        self.output_textbox.insert("1.0", "Generating... Please wait.")
        self.output_textbox.configure(state="disabled")
        threading.Thread(target=self.execute_llm_call, args=(prompt,)).start()

    def execute_llm_call(self, prompt):
        if not self.config or 'llm' not in self.config:
            self.update_output_textbox("LLM configuration not loaded.")
            return
        llm_config = self.config['llm']
        model = llm_config.get('default_model', 'unknown')
        response = api_client.generate_llm(model=model, prompt=prompt)
        if response and response.get('choices'):
            content = response['choices'][0]['delta']['content']
            self.update_output_textbox(content)
        else:
            self.update_output_textbox("Error: Failed to get a valid response from the backend.")

    def update_output_textbox(self, text):
        self.output_textbox.configure(state="normal")
        self.output_textbox.delete("1.0", tk.END)
        self.output_textbox.insert("1.0", text)
        self.output_textbox.configure(state="disabled")

    def refresh_recipe_list(self):
        self.recipes = api_client.get_recipes()
        if self.recipes:
            recipe_names = [f"{cat}/{name}" for cat, names in self.recipes.items() for name in names]
            if not recipe_names: recipe_names = ["No Recipes Found"]
            self.recipe_menu.configure(values=recipe_names)
            self.recipe_menu.set(recipe_names[0])
        else:
            self.recipe_menu.configure(values=["No Recipes Found"])
            self.recipe_menu.set("No Recipes Found")

    def load_recipe(self, selection):
        if selection == "No Recipes Found" or '/' not in selection: return
        category, name = selection.split('/', 1)
        recipe_data = api_client.get_recipe(category, name)
        if recipe_data and 'prompt' in recipe_data:
            self.prompt_textbox.delete("1.0", tk.END)
            self.prompt_textbox.insert("1.0", recipe_data['prompt'])

    def create_crypto_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        controls_frame = ctk.CTkFrame(tab)
        controls_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        ctk.CTkButton(controls_frame, text="Start All", command=self.start_all_miners).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(controls_frame, text="Stop All", command=self.stop_all_miners).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(controls_frame, text="Manage Miners", command=self.open_miner_manager).pack(side="right", padx=10, pady=10)
        self.miners_frame = ctk.CTkScrollableFrame(tab, label_text="Miner Configurations")
        self.miners_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

    def refresh_miner_list(self):
        for widget in self.miners_frame.winfo_children(): widget.destroy()
        self.miner_widgets = {}
        miners = self.config.get('miners', [])
        for miner_config in miners:
            miner_name = miner_config['name']
            frame = ctk.CTkFrame(self.miners_frame); frame.pack(fill="x", padx=5, pady=5); frame.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(frame, text=miner_name).grid(row=0, column=0, padx=10, pady=5)
            status = ctk.CTkLabel(frame, text="Stopped", text_color="#E57373"); status.grid(row=0, column=1, padx=10, pady=5, sticky="e")
            start_btn = ctk.CTkButton(frame, text="Start", width=60, command=lambda n=miner_name: api_client.start_miner(n)); start_btn.grid(row=0, column=2, padx=5, pady=5)
            stop_btn = ctk.CTkButton(frame, text="Stop", width=60, command=lambda n=miner_name: api_client.stop_miner(n)); stop_btn.grid(row=0, column=3, padx=5, pady=5)
            self.miner_widgets[miner_name] = {'status': status, 'start_button': start_btn, 'stop_button': stop_btn}

    def update_crypto_tab(self):
        statuses = api_client.get_all_miner_status()
        if statuses:
            for name, widgets in self.miner_widgets.items():
                status = statuses.get(name, "NOT_FOUND")
                if status == "RUNNING":
                    widgets['status'].configure(text="Running", text_color="#81C784"); widgets['start_button'].configure(state="disabled"); widgets['stop_button'].configure(state="normal")
                else:
                    widgets['status'].configure(text="Stopped", text_color="#E57373"); widgets['start_button'].configure(state="normal"); widgets['stop_button'].configure(state="disabled")
        self.after(2000, self.update_crypto_tab)

    def start_all_miners(self):
        for miner_config in self.config.get('miners', []):
            api_client.start_miner(miner_config['name'])

    def stop_all_miners(self):
        api_client.stop_all_miners()

    def open_miner_manager(self):
        if self.miner_manager_window is None or not self.miner_manager_window.winfo_exists():
            self.miner_manager_window = MinerManagerWindow(self)
            self.miner_manager_window.transient(self)
        else:
            self.miner_manager_window.focus()

    def create_dashboard_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        cpu_frame = ctk.CTkFrame(tab); cpu_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew"); cpu_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(cpu_frame, text="CPU Usage").grid(row=0, column=0, padx=10, pady=5)
        self.cpu_progress = ctk.CTkProgressBar(cpu_frame); self.cpu_progress.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        self.cpu_label = ctk.CTkLabel(cpu_frame, text="0%"); self.cpu_label.grid(row=0, column=2, padx=10, pady=5)
        ram_frame = ctk.CTkFrame(tab); ram_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew"); ram_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(ram_frame, text="RAM Usage").grid(row=0, column=0, padx=10, pady=5)
        self.ram_progress = ctk.CTkProgressBar(ram_frame); self.ram_progress.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        self.ram_label = ctk.CTkLabel(ram_frame, text="0% (0.0/0.0 GB)"); self.ram_label.grid(row=0, column=2, padx=10, pady=5)
        self.gpu_frames = []

    def update_dashboard(self):
        stats = api_client.get_system_stats()
        if stats:
            if 'cpu' in stats and 'percent' in stats['cpu']:
                self.cpu_progress.set(stats['cpu']['percent'] / 100)
                self.cpu_label.configure(text=f"{stats['cpu']['percent']:.1f}%")
            if 'ram' in stats and all(k in stats['ram'] for k in ['percent', 'used', 'total']):
                ram_used_gb = stats['ram']['used'] / (1024**3); ram_total_gb = stats['ram']['total'] / (1024**3)
                self.ram_progress.set(stats['ram']['percent'] / 100)
                self.ram_label.configure(text=f"{stats['ram']['percent']:.1f}% ({ram_used_gb:.1f}/{ram_total_gb:.1f} GB)")
            if 'gpus' in stats and stats['gpus'] and not self.gpu_frames:
                for i, gpu_stat in enumerate(stats['gpus']):
                    gpu_frame = ctk.CTkFrame(self.tab_view.tab("Dashboard")); gpu_frame.grid(row=2+i, column=0, padx=10, pady=10, sticky="nsew"); gpu_frame.grid_columnconfigure(1, weight=1)
                    ctk.CTkLabel(gpu_frame, text=f"GPU {i}: {gpu_stat.get('name', 'N/A')}").grid(row=0, column=0, columnspan=3, padx=10, pady=5, sticky="w")
                    ctk.CTkLabel(gpu_frame, text="Usage").grid(row=1, column=0, padx=10, pady=2, sticky="w")
                    gpu_usage_progress = ctk.CTkProgressBar(gpu_frame); gpu_usage_progress.grid(row=1, column=1, padx=10, pady=2, sticky="ew")
                    gpu_usage_label = ctk.CTkLabel(gpu_frame, text="0%"); gpu_usage_label.grid(row=1, column=2, padx=10, pady=2, sticky="e")
                    ctk.CTkLabel(gpu_frame, text="Memory").grid(row=2, column=0, padx=10, pady=2, sticky="w")
                    gpu_mem_progress = ctk.CTkProgressBar(gpu_frame); gpu_mem_progress.grid(row=2, column=1, padx=10, pady=2, sticky="ew")
                    gpu_mem_label = ctk.CTkLabel(gpu_frame, text="0%"); gpu_mem_label.grid(row=2, column=2, padx=10, pady=2, sticky="e")
                    ctk.CTkLabel(gpu_frame, text="Temp").grid(row=3, column=0, padx=10, pady=2, sticky="w")
                    gpu_temp_label = ctk.CTkLabel(gpu_frame, text="0°C"); gpu_temp_label.grid(row=3, column=1, padx=10, pady=2, sticky="w")
                    self.gpu_frames.append({'frame': gpu_frame, 'usage_progress': gpu_usage_progress, 'usage_label': gpu_usage_label, 'mem_progress': gpu_mem_progress, 'mem_label': gpu_mem_label, 'temp_label': gpu_temp_label})
            if 'gpus' in stats:
                for i, gpu_stat in enumerate(stats['gpus']):
                    if i < len(self.gpu_frames):
                        frame_info = self.gpu_frames[i]
                        usage = gpu_stat.get('usage', 0); mem_usage = gpu_stat.get('memory_usage', 0); temp = gpu_stat.get('temperature', 0)
                        frame_info['usage_progress'].set(usage / 100); frame_info['usage_label'].configure(text=f"{usage}%")
                        frame_info['mem_progress'].set(mem_usage / 100); frame_info['mem_label'].configure(text=f"{mem_usage}%")
                        frame_info['temp_label'].configure(text=f"{temp}°C")
        self.after(2000, self.update_dashboard)

if __name__ == "__main__":
    # Start the backend in a daemon thread
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()
    # Give the server a moment to start before launching the GUI
    time.sleep(5)
    
    app = LocalLLMApp()
    app.mainloop()