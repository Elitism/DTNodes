import tkinter as tk
from tkinter import ttk
import psutil
import random
import os
import time
import logging
from threading import Thread
import queue
import uuid

# Color scheme: Dark futuristic with neon accents
DRIVE_COLOR = "#00FF9F"
DISK_COLOR = "#1E90FF"
CPU_PARENT_COLOR = "#FF3D00"
CPU_CORE_COLOR = "#FF7F50"
CPU_THREAD_COLOR = "#FFDAB9"
GPU_PARENT_COLOR = "#FF4500"
GPU_COLOR = "#00CED1"
NETWORK_PARENT_COLOR = "#9932CC"
NETWORK_COLOR = "#DA70D6"
FILESYSTEM_PARENT_COLOR = "#32CD32"
FILESYSTEM_COLOR = "#98FB98"
LINE_COLOR = "#2F4F4F"
ARC_COLOR = "#00FF7F"
CPU_ARC_COLOR = "#FF4500"
SEND_ARC_COLOR = "#1E90FF"
RECEIVE_ARC_COLOR = "#9400D3"
READ_ARC_COLOR = "#FFD700"
WRITE_ARC_COLOR = "#FF6347"
BACKGROUND_COLOR = "#0A0F1A"
PARENT_FONT = ("Orbitron", 16, "bold")
CPU_CHILD_FONT = ("Fira Code", 8, "normal")
CHILD_FONT = ("Roboto Mono", 12, "normal")
CPU_CORE_FONT = ("Roboto Mono", 9, "bold")
CPU_THREAD_FONT = ("Roboto Mono", 8, "normal")
ARC_WIDTH = 5

try:
    import pynvml
    pynvml.nvmlInit()
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    logging.warning("pynvml not available, GPU monitoring disabled")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Particle:
    def __init__(self, text, color, font, parent=None, data_key=None, is_gpu=False, is_network=False, is_filesystem=False, is_cpu=False, app=None, particle_type=None):
        self.app = app
        self.text = text
        self.color = color
        self.font = font
        self.parent = parent
        self.data_key = data_key
        self.is_gpu = is_gpu
        self.is_network = is_network
        self.is_filesystem = is_filesystem
        self.is_cpu = is_cpu
        self.particle_type = particle_type
        self.x = random.randint(0, 1920)
        self.y = random.randint(0, 1080)
        self.target_x = self.x
        self.target_y = self.y
        self.line_id = None
        self.text_id = None
        self.arc_id = None
        self.max_value = 1.0
        self.display_value = 0.0
        self.jitter_offset_x = 0.0
        self.jitter_offset_y = 0.0
        self.target_offset_x = 0.0
        self.target_offset_y = 0.0
        self.prev_value = 0.0
        self.update_counter = 0
        self.depth = 0
        if parent:
            self.depth = parent.depth + 1
        effective_depth = min(self.depth, len(self.app.arc_radii) - 1)
        self.arc_radius = self.app.arc_radii[effective_depth]
        self.jitter_strength = self.app.jitter_strengths[effective_depth]

class SettingsPanel(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.title("Settings")
        self.geometry("1920x1080")
        self.configure(bg=BACKGROUND_COLOR)

        style = ttk.Style(self)
        style.configure("TScale", background=BACKGROUND_COLOR, foreground="white", troughcolor=LINE_COLOR)
        style.configure("TLabel", background=BACKGROUND_COLOR, foreground="white", font=("Roboto Mono", 10))

        self.create_slider("CPU Y Position", "parent_y_positions", 0, 1080, key='cpu')
        self.create_slider("Drives Y Position", "parent_y_positions", 0, 1080, key='drives')
        self.create_slider("GPU Y Position", "parent_y_positions", 0, 1080, key='gpu')
        self.create_slider("Network Y Position", "parent_y_positions", 0, 1080, key='network')
        self.create_slider("FileSystem Y Position", "parent_y_positions", 0, 1080, key='filesystem')
        
        self.create_slider("Spacing", "spacing", 0, 200)
        self.create_slider("CPU Spacing", "parent_child_spacings", 0, 300, key='cpu')
        self.create_slider("Drives Spacing", "parent_child_spacings", 0, 300, key='drives')
        self.create_slider("GPU Spacing", "parent_child_spacings", 0, 300, key='gpu')
        self.create_slider("Network Spacing", "parent_child_spacings", 0, 300, key='network')
        self.create_slider("FileSystem Spacing", "parent_child_spacings", 0, 300, key='filesystem')
        self.create_slider("Vertical Spacing", "vertical_spacing", 0, 300)
        self.create_slider("Sub-Child Hori Spacing", "sub_child_spacing_hori", 0, 150)
        self.create_slider("Sub-Child Vert Spacing", "sub_child_spacing_verti", 0, 150)
        self.create_slider("Grandchild Hori Spacing", "sub_grandchild_spacing_hori", 0, 150)
        self.create_slider("Grandchild Vert Spacing", "sub_grandchild_spacing_verti", 0, 150)
        self.create_slider("Parent Jitter", "jitter_strengths", 0, 50, index=0)
        self.create_slider("Child Jitter", "jitter_strengths", 0, 50, index=1)
        self.create_slider("Grandchild Jitter", "jitter_strengths", 0, 50, index=2)

    def create_slider(self, text, var_name, from_, to, index=None, key=None):
        frame = tk.Frame(self, bg=BACKGROUND_COLOR)
        label = ttk.Label(frame, text=text, style="TLabel", width=22)
        label.pack(side=tk.LEFT, padx=8, pady=6)
        
        var = getattr(self.master, var_name)
        if key is not None:
            initial_value = var.get(key, 150)
        elif index is not None:
            initial_value = var[index]
        else:
            initial_value = var
        
        value_label = ttk.Label(frame, text=str(int(initial_value)), style="TLabel", width=5)
        value_label.pack(side=tk.RIGHT, padx=8)
        
        def update_value_label(val, name=var_name, idx=index, k=key, v_label=value_label):
            value = int(float(val))
            v_label.configure(text=str(value))
            if k is not None:
                getattr(self.master, name)[k] = value
            elif idx is not None:
                getattr(self.master, name)[idx] = value
            else:
                setattr(self.master, name, value)
            self.master.apply_settings()

        slider = ttk.Scale(frame, from_=from_, to=to, orient=tk.HORIZONTAL, value=initial_value,
                          command=update_value_label, style="TScale")
        slider.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=8)
        frame.pack(fill=tk.X, padx=8, pady=4)

class DesktopWidget(tk.Tk):
    def __init__(self):
        super().__init__()

        self.spacing = 70
        self.parent_child_spacings = {
            'cpu': 320,
            'drives': 0,
            'gpu': 0,
            'network': 0,
            'filesystem': 0
        }
        self.parent_y_positions = {
            'cpu': 50,
            'drives': 160,
            'gpu': 240,
            'network': 320,
            'filesystem': 400
        }
        self.vertical_spacing = 60
        self.sub_child_spacing_hori = 40
        self.sub_child_spacing_verti = 40
        self.sub_grandchild_spacing_hori = 45
        self.sub_grandchild_spacing_verti = 45
        self.arc_radii = [28, 20, 14]
        self.jitter_strengths = [0, 0, 12]

        self.width = self.winfo_screenwidth()
        self.height = self.winfo_screenheight()
        self.geometry(f"{self.width}x{self.height}+0+0")
        self.overrideredirect(True)
        self.attributes("-transparentcolor", BACKGROUND_COLOR)
        self.configure(bg=BACKGROUND_COLOR)
        self.topmost = True
        self.attributes("-topmost", self.topmost)

        self.canvas = tk.Canvas(self, width=self.width, height=self.height,
                                bg=BACKGROUND_COLOR, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.particles = []
        self.last_disk_io = psutil.disk_io_counters()
        self.last_disk_time = time.time()
        self.last_net_io = psutil.net_io_counters()
        self.last_net_time = time.time()
        self.data_queue = queue.Queue()
        self.running = True
        self.settings_panel = None
        
        self.create_particles()
        self.assign_grid_targets()

        self.drag_data = {"x": 0, "y": 0, "dragging": False}
        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.do_drag)
        self.canvas.bind("<ButtonRelease-1>", self.stop_drag)
        self.canvas.bind("<Double-Button-1>", self.minimize_widget)
        self.bind("<Control-t>", self.toggle_topmost)
        self.bind("<Control-s>", self.toggle_settings_panel)
        self.bind("<Escape>", self.on_closing)
        
        self.data_thread = Thread(target=self.collect_data, daemon=True)
        self.data_thread.start()
        
        self.after(16, self.update_loop)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.rise_factor = 0.08
        self.fall_factor = 0.03
        self.jitter_lerp_factor = 0.15
        self.frame_count = 0

    def collect_data(self):
        while self.running:
            try:
                data = {}
                data['cpu'] = {
                    'total': psutil.cpu_percent(percpu=False),
                    'per_cpu': psutil.cpu_percent(percpu=True)
                }

                for partition in psutil.disk_partitions():
                    if 'cdrom' not in partition.opts and partition.fstype and 'ro' not in partition.opts:
                        try:
                            usage = psutil.disk_usage(partition.mountpoint)
                            data[partition.mountpoint] = {
                                'percent': usage.percent,
                                'name': os.path.basename(partition.device),
                                'drive_name': partition.mountpoint  # Store mountpoint as drive name
                            }
                        except Exception:
                            continue
                
                if GPU_AVAILABLE:
                    try:
                        for i in range(pynvml.nvmlDeviceGetCount()):
                            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                            data[f"gpu{i}"] = {
                                'percent': utilization.gpu,
                                'memory': utilization.memory
                            }
                    except Exception as e:
                        logging.error(f"GPU data collection failed: {e}")
                
                current_net_io = psutil.net_io_counters()
                current_time_net = time.time()
                time_delta_net = current_time_net - self.last_net_time
                
                if time_delta_net > 0:
                    sent_mbps = ((current_net_io.bytes_sent - self.last_net_io.bytes_sent) * 8 / 1_000_000) / time_delta_net
                    received_mbps = ((current_net_io.bytes_recv - self.last_net_io.bytes_recv) * 8 / 1_000_000) / time_delta_net
                    data['network'] = {
                        'sent': sent_mbps,
                        'received': received_mbps
                    }
                    self.last_net_io = current_net_io
                    self.last_net_time = current_time_net

                current_disk_io = psutil.disk_io_counters()
                current_time_disk = time.time()
                time_delta_disk = current_time_disk - self.last_disk_time

                if time_delta_disk > 0:
                    read_mbps = (current_disk_io.read_bytes - self.last_disk_io.read_bytes) / (1024 * 1024) / time_delta_disk
                    write_mbps = (current_disk_io.write_bytes - self.last_disk_io.write_bytes) / (1024 * 1024) / time_delta_disk
                    data['filesystem'] = {
                        'read': read_mbps,
                        'write': write_mbps
                    }
                    self.last_disk_io = current_disk_io
                    self.last_disk_time = current_time_disk

                if not self.data_queue.full():
                    self.data_queue.put(data)
                    
            except Exception as e:
                logging.error(f"Data collection error: {e}")
            
            time.sleep(0.5)

    def minimize_widget(self, event=None):
        if self.state() == 'normal':
            self.iconify()
        else:
            self.deiconify()

    def start_drag(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        self.drag_data["dragging"] = False

    def do_drag(self, event):
        if not self.drag_data["dragging"]:
            dx = abs(event.x - self.drag_data["x"])
            dy = abs(event.y - self.drag_data["y"])
            if dx > 5 or dy > 5:
                self.drag_data["dragging"] = True
        
        if self.drag_data["dragging"]:
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]
            x = self.winfo_x() + dx
            y = self.winfo_y() + dy
            self.geometry(f"+{x}+{y}")

    def stop_drag(self, event):
        self.drag_data["x"] = 0
        self.drag_data["y"] = 0
        self.drag_data["dragging"] = False

    def toggle_topmost(self, event=None):
        self.topmost = not self.topmost
        self.attributes("-topmost", self.topmost)
        logging.info(f"Topmost set to {self.topmost}")

    def toggle_settings_panel(self, event=None):
        if self.settings_panel is None or not self.settings_panel.winfo_exists():
            self.settings_panel = SettingsPanel(self)
        else:
            self.settings_panel.lift()

    def apply_settings(self):
        for p in self.particles:
            effective_depth = min(p.depth, len(self.arc_radii) - 1)
            p.arc_radius = self.arc_radii[effective_depth]
            p.jitter_strength = self.jitter_strengths[effective_depth]
        self.assign_grid_targets()

    def create_particles(self):
        parent_x_pos = 180 
        physical_cores = psutil.cpu_count(logical=False)
        logical_cores = psutil.cpu_count(logical=True)
        threads_per_core = logical_cores // physical_cores

        parent_cpu = Particle("CPU", CPU_PARENT_COLOR, PARENT_FONT, is_cpu=True, data_key='cpu_total', app=self, particle_type='cpu')
        parent_cpu.x, parent_cpu.y = parent_x_pos, self.parent_y_positions['cpu']
        parent_cpu.target_x, parent_cpu.target_y = parent_cpu.x, parent_cpu.y
        self.particles.append(parent_cpu)

        for i in range(physical_cores):
            core_p = Particle(f"Core {i}", CPU_CORE_COLOR, CPU_CHILD_FONT, parent=parent_cpu, is_cpu=True, app=self)
            self.particles.append(core_p)
            for j in range(threads_per_core):
                thread_index = i * threads_per_core + j
                thread_p = Particle(f"Thread {thread_index}", CPU_THREAD_COLOR, CPU_THREAD_FONT, parent=core_p, is_cpu=True, data_key=thread_index, app=self)
                self.particles.append(thread_p)
        
        parent_drive = Particle("Drives", DRIVE_COLOR, PARENT_FONT, app=self, particle_type='drives')
        parent_drive.x, parent_drive.y = parent_x_pos, self.parent_y_positions['drives']
        parent_drive.target_x, parent_drive.target_y = parent_drive.x, parent_drive.y
        self.particles.append(parent_drive)

        for partition in psutil.disk_partitions():
            if 'cdrom' in partition.opts or not partition.fstype or 'ro' in partition.opts:
                continue
            p = Particle(f"{partition.mountpoint} ({os.path.basename(partition.device)})", DISK_COLOR, CHILD_FONT,
                         parent=parent_drive, data_key=partition.mountpoint, app=self)
            self.particles.append(p)

        if GPU_AVAILABLE:
            parent_gpu = Particle("GPU", GPU_PARENT_COLOR, PARENT_FONT, app=self, particle_type='gpu')
            parent_gpu.x, parent_gpu.y = parent_x_pos, self.parent_y_positions['gpu']
            parent_gpu.target_x, parent_gpu.target_y = parent_gpu.x, parent_gpu.y
            self.particles.append(parent_gpu)
            try:
                for i in range(pynvml.nvmlDeviceGetCount()):
                    p = Particle(f"GPU{i}", GPU_COLOR, CHILD_FONT,
                                 parent=parent_gpu, data_key=f"gpu{i}", is_gpu=True, app=self)
                    self.particles.append(p)
            except Exception as e:
                logging.error(f"Failed to initialize GPU particles: {e}")

        parent_network = Particle("Network", NETWORK_PARENT_COLOR, PARENT_FONT, app=self, particle_type='network')
        parent_network.x, parent_network.y = parent_x_pos, self.parent_y_positions['network']
        parent_network.target_x, parent_network.target_y = parent_network.x, parent_network.y
        self.particles.append(parent_network)

        p_sent = Particle("Sent 0 Mb/s", NETWORK_COLOR, CHILD_FONT,
                          parent=parent_network, data_key="sent", is_network=True, app=self)
        p_received = Particle("Received 0 Mb/s", NETWORK_COLOR, CHILD_FONT,
                              parent=parent_network, data_key="received", is_network=True, app=self)
        self.particles.extend([p_sent, p_received])
        
        parent_filesystem = Particle("FileSystem", FILESYSTEM_PARENT_COLOR, PARENT_FONT, app=self, particle_type='filesystem')
        parent_filesystem.x, parent_filesystem.y = parent_x_pos, self.parent_y_positions['filesystem']
        parent_filesystem.target_x, parent_filesystem.target_y = parent_filesystem.x, parent_filesystem.y
        self.particles.append(parent_filesystem)

        p_read = Particle("Read 0 MB/s", FILESYSTEM_COLOR, CHILD_FONT,
                          parent=parent_filesystem, data_key="read", is_filesystem=True, app=self)
        p_write = Particle("Write 0 MB/s", FILESYSTEM_COLOR, CHILD_FONT,
                           parent=parent_filesystem, data_key="write", is_filesystem=True, app=self)
        self.particles.extend([p_read, p_write])

    def assign_grid_targets(self):
        for parent in [p for p in self.particles if not p.parent]:
            parent.target_y = self.parent_y_positions.get(parent.particle_type, parent.y)
            parent.y = parent.target_y
            children = [c for c in self.particles if c.parent == parent]
            if not children:
                continue
            
            cols = min(len(children), 8 if parent.particle_type == 'cpu' else 4)
            rows = (len(children) + cols - 1) // cols
            
            cell_width = self.spacing + (55 if parent.particle_type == 'cpu' else 55)
            cell_height = self.vertical_spacing // 2
            
            grid_width = (cols - 1) * cell_width
            parent_spacing = self.parent_child_spacings.get(parent.particle_type, 150)
            x_start = parent.x + parent_spacing - grid_width / 2
            y_start = parent.y + (self.vertical_spacing / 1.6 if parent.particle_type == 'cpu' else self.vertical_spacing / 1.8)
            
            for idx, child in enumerate(children):
                row = idx // cols
                col = idx % cols
                
                child.target_x = x_start + col * cell_width
                child.target_y = y_start + row * cell_height
                
                child.target_x = max(50, min(child.target_x, self.width - 100))
                child.target_y = max(50, min(child.target_y, self.height - 50))
                
                self.assign_grid_targets_for_particle(child)

    def assign_grid_targets_for_particle(self, parent):
        children = [c for c in self.particles if c.parent == parent]
        if not children:
            return

        cols = len(children)
        cell_width = self.sub_child_spacing_hori
        x_start = parent.target_x - ((cols - 1) * cell_width) / 2
        y_start = parent.target_y + self.sub_child_spacing_verti

        for idx, child in enumerate(children):
            child.target_x = x_start + idx * cell_width
            child.target_y = y_start

    def update_loop(self):
        if not self.running:
            return
        
        self.frame_count += 1
        
        try:
            while not self.data_queue.empty():
                data = self.data_queue.get_nowait()
                self.update_particles_with_data(data)
        except queue.Empty:
            pass
        
        self.animate_particles()
        
        if self.frame_count % 2 == 0:
            self.redraw()
        
        self.after(16, self.update_loop)

    def update_particles_with_data(self, data):
        for p in self.particles:
            if not p.parent and p.data_key != 'cpu_total':
                continue

            current_value = 0
            
            if p.is_cpu and isinstance(p.data_key, int):
                if 'cpu' in data and len(data['cpu']['per_cpu']) > p.data_key:
                    current_value = data['cpu']['per_cpu'][p.data_key]
                    p.text = f"T{p.data_key} {current_value:.0f}%"
            elif p.is_cpu and p.data_key == 'cpu_total':
                if 'cpu' in data:
                    current_value = data['cpu']['total']
                    p.text = f"CPU {current_value:.0f}%"
            elif p.data_key and not p.is_gpu and not p.is_network and not p.is_filesystem and not p.is_cpu:
                if p.data_key in data:
                    current_value = data[p.data_key]['percent']
                    # Include drive name in the text
                    p.text = f"{data[p.data_key]['drive_name']} {current_value:.0f}%"
            elif p.is_gpu and p.data_key in data:
                current_value = data[p.data_key]['percent']
                p.text = f"GPU{p.data_key[-1]} {current_value}%"
            elif p.is_network and 'network' in data:
                if p.data_key == "sent":
                    current_value = data['network']['sent']
                    p.text = f"Sent {current_value:.2f} Mb/s"
                elif p.data_key == "received":
                    current_value = data['network']['received']
                    p.text = f"Received {current_value:.2f} Mb/s"
                
                if current_value > 0: p.max_value = max(p.max_value, current_value)
                if current_value > p.display_value: p.display_value += (current_value - p.display_value) * self.rise_factor
                else: p.display_value -= (p.display_value - current_value) * self.fall_factor
            elif p.is_filesystem and 'filesystem' in data:
                if p.data_key == "read":
                    current_value = data['filesystem']['read']
                    p.text = f"Read {current_value:.2f} MB/s"
                elif p.data_key == "write":
                    current_value = data['filesystem']['write']
                    p.text = f"Write {current_value:.2f} MB/s"

                if current_value > 0: p.max_value = max(p.max_value, current_value)
                if current_value > p.display_value: p.display_value += (current_value - p.display_value) * self.rise_factor
                else: p.display_value -= (p.display_value - current_value) * self.fall_factor

            if abs(current_value - p.prev_value) > 0.01:
                p.target_offset_x = random.uniform(-p.jitter_strength, p.jitter_strength)
                p.target_offset_y = random.uniform(-p.jitter_strength, p.jitter_strength)

            p.prev_value = current_value

        for p in self.particles:
            if p.is_cpu and p.text.startswith("Core"):
                children = [c for c in self.particles if c.parent == p]
                if children:
                    avg_usage = sum(c.prev_value for c in children) / len(children)
                    p.prev_value = avg_usage
                    p.text = f"Core {p.text.split(' ')[1]} {avg_usage:.0f}%"

    def animate_particles(self):
        for p in self.particles:
            if not p.parent:
                p.x += (p.target_x - p.x) * 0.12
                p.y += (p.target_y - p.y) * 0.12
                continue

            p.jitter_offset_x += (p.target_offset_x - p.jitter_offset_x) * self.jitter_lerp_factor
            p.jitter_offset_y += (p.target_offset_y - p.jitter_offset_y) * self.jitter_lerp_factor

            p.target_offset_x *= 0.90
            p.target_offset_y *= 0.90

            target_x = p.target_x + p.jitter_offset_x
            target_y = p.target_y + p.jitter_offset_y
            
            p.x += (target_x - p.x) * 0.12
            p.y += (target_y - p.y) * 0.12

            p.x = max(10, min(p.x, self.width - 10))
            p.y = max(10, min(p.y, self.height - 10))

    def redraw(self):
        for p in self.particles:
            if p.parent:
                if not p.line_id:
                    p.line_id = self.canvas.create_line(p.x, p.y, p.parent.x, p.parent.y,
                                                        fill=LINE_COLOR, width=3)
                else:
                    self.canvas.coords(p.line_id, p.x, p.y, p.parent.x, p.parent.y)
                self.canvas.tag_lower(p.line_id)

            if (p.data_key or p.is_cpu) and (p.parent or p.data_key == 'cpu_total'):
                try:
                    usage = 0
                    arc_color = ARC_COLOR
                    
                    if p.is_cpu:
                        usage = p.prev_value / 100.0
                        arc_color = CPU_ARC_COLOR
                    elif p.is_gpu:
                        usage = p.prev_value / 100.0
                    elif p.is_network:
                        usage = min(p.display_value / p.max_value, 1.0) if p.max_value > 0 else 0
                        arc_color = SEND_ARC_COLOR if p.data_key == "sent" else RECEIVE_ARC_COLOR
                    elif p.is_filesystem:
                        usage = min(p.display_value / p.max_value, 1.0) if p.max_value > 0 else 0
                        arc_color = READ_ARC_COLOR if p.data_key == "read" else WRITE_ARC_COLOR
                    else:
                        usage = p.prev_value / 100.0

                    if usage > 0.01:
                        x0, y0 = p.x - p.arc_radius, p.y - p.arc_radius
                        x1, y1 = p.x + p.arc_radius, p.y + p.arc_radius

                        if not p.arc_id:
                            p.arc_id = self.canvas.create_arc(
                                x0, y0, x1, y1,
                                start=90, extent=-usage * 360,
                                style=tk.ARC, outline=arc_color,
                                width=ARC_WIDTH
                            )
                        else:
                            self.canvas.coords(p.arc_id, x0, y0, x1, y1)
                            self.canvas.itemconfig(p.arc_id, extent=-usage * 360, outline=arc_color)
                        self.canvas.tag_lower(p.arc_id)
                    elif p.arc_id:
                        self.canvas.delete(p.arc_id)
                        p.arc_id = None
                        
                except Exception as e:
                    logging.error(f"Arc draw failed for {p.data_key}: {e}")

            if not p.text_id:
                p.text_id = self.canvas.create_text(
                    p.x, p.y, text=p.text, fill=p.color,
                    font=p.font, anchor=tk.CENTER
                )
            else:
                self.canvas.coords(p.text_id, p.x, p.y)
                self.canvas.itemconfig(p.text_id, text=p.text)
            
            if p.text_id:
                self.canvas.tag_raise(p.text_id)

    def on_closing(self, event=None):
        logging.info("Shutting down desktop widget...")
        self.running = False
        
        if GPU_AVAILABLE:
            try:
                pynvml.nvmlShutdown()
                logging.info("pynvml shutdown successfully")
            except Exception as e:
                logging.error(f"pynvml shutdown failed: {e}")
        
        if hasattr(self, 'data_thread') and self.data_thread.is_alive():
            self.data_thread.join(timeout=1.0)
        
        self.destroy()

if __name__ == "__main__":
    try:
        app = DesktopWidget()
        app.mainloop()
    except KeyboardInterrupt:
        logging.info("Application interrupted by user")
    except Exception as e:
        logging.error(f"Application error: {e}")
        raise