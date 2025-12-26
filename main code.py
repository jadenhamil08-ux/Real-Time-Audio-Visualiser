import customtkinter as ctk
from tkinter import filedialog
import librosa
import numpy as np
import pygame
import os

pygame.init()
pygame.mixer.init()
pygame.mixer.music.set_volume(0.5)

ctk.set_appearance_mode("black")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Audio Visualiser")
        self.geometry("600x600")
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True)
        self.frames = {}
        self.current_filepath = None
        self.current_filename = None

        for index in (MainPage, PlayerPage):
            frame = index(self.container,self)
            self.frames[index] = frame
            frame.place(relwidth=1, relheight=1)
        self.show_frame(MainPage)

    def show_frame(self, page):
        self.frames[page].tkraise()

    def set_current_song(self, filepath, filename):
        self.current_filepath = filepath
        self.current_filename = filename

class MainPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        title = ctk.CTkLabel(self, text="Audio Visualiser",font=ctk.CTkFont(size=120,weight="bold"))
        title.pack(pady=80)

        label = ctk.CTkLabel(self, text="For MP3 Files",font=ctk.CTkFont(size=60))
        label.pack(pady=(0,5))

        button = button = ctk.CTkButton(self, text="Select MP3",command=lambda: self.open_file(),width=300,height=75,font=ctk.CTkFont(size=40,weight="bold"))
        button.pack(pady=100)

        exit_button = ctk.CTkButton(self, text="Exit",command=lambda: app.destroy(),width=300,height=75,font=ctk.CTkFont(size=40,weight="bold"))
        exit_button.pack(pady=20)

    def open_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("MP3 Files","*.mp3")])

        if not filepath:
            return

        filename = os.path.basename(filepath)
        pygame.mixer.music.load(filepath)
        player_page = self.controller.frames[PlayerPage]
        player_page.load_song(filepath,filename)
        self.controller.show_frame(PlayerPage)

def set_volume(value):
    pygame.mixer.music.set_volume(float(value))

def exit_program():
    app.destroy()

class PlayerPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.themes = {
            "Purple": ("#c77dff", "#7b2cbf"),
            "Blue": ("#4cc9f0", "#4361ee"),
            "Green": ("#80ffdb", "#2ec4b6"),
            "Red": ("#ff5c8a", "#c9184a")
        }
        self.current_theme = "Purple"
        self.neon_core, self.neon_glow = self.themes[self.current_theme]
        self.bass_energy = 0.0

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.title = ctk.CTkLabel(self, text="Now Playing:",font=ctk.CTkFont(size=40, weight="bold"))
        self.title.grid(row=0, column=0, pady=(10, 0))

        self.song_label = ctk.CTkLabel(self, text="",font=ctk.CTkFont(size=22, weight="bold"))
        self.song_label.grid(row=1, column=0, pady=(0, 10))

        self.canvas = ctk.CTkCanvas(self, bg="#111111", highlightthickness=0)
        self.canvas.grid(row=2, column=0,sticky="nsew",padx=10,pady=(10, 0))

        self.time_label = ctk.CTkLabel(self, text="00:00 / 00:00",font=ctk.CTkFont(size=18))
        self.time_label.grid(row=3, column=0, pady=5)

        self.progress_bg = ctk.CTkCanvas(self, height=14,bg="#2a2a2a", highlightthickness=0)
        self.progress_bg.grid(row=4, column=0,sticky="ew",padx=20,pady=5)
        self.progress_bg.bind("<Button-1>", self.seek_audio)

        self.volume_slider = ctk.CTkSlider(self, from_=0, to=1, number_of_steps=100, command=set_volume)
        self.volume_slider.set(0.5)
        self.volume_slider.grid(row=5, column=0,sticky="ew",padx=80,pady=8)

        self.bottom_frame = ctk.CTkFrame(self, fg_color="transparent", height=140)
        self.bottom_frame.grid(row=6, column=0, pady=10)

        controls_frame = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        controls_frame.grid(row=0, column=0)

        self.skip_back_button = ctk.CTkButton(controls_frame, text="-5s", width=80,command=lambda: self.skip_seconds(-5))
        self.skip_back_button.grid(row=0, column=0, padx=5)

        self.restart_button = ctk.CTkButton(controls_frame, text="Restart", width=80,command=self.restart_song)
        self.restart_button.grid(row=0, column=1, padx=5)

        self.skip_forward_button = ctk.CTkButton(controls_frame, text="+5s", width=80,command=lambda: self.skip_seconds(5))
        self.skip_forward_button.grid(row=0, column=2, padx=5)

        self.mode_button = ctk.CTkButton(controls_frame, text="Switch Visual", width=180,command=self.toggle_mode)
        self.mode_button.grid(row=0, column=3, padx=10)

        self.theme_menu = ctk.CTkOptionMenu(controls_frame,values=list(self.themes.keys()),command=self.change_theme,width=120)
        self.theme_menu.set("Purple")
        self.theme_menu.grid(row=0, column=5, padx=10)

        self.play_button = ctk.CTkButton(controls_frame, text="Play", width=120,command=self.toggle_play)
        self.play_button.grid(row=0, column=4, padx=10)

        self.back_button = ctk.CTkButton(self.bottom_frame,text="Back",width=120,command=self.on_back)
        self.back_button.grid(row=1, column=0, pady=10)

        self.bind("<Configure>",self.resize_layout)

        self.start_time = None
        self.pause_offset = 0.0

        self.progress_fg = None
        self.visualiser_mode = "bars"
        self.audio_data = None
        self.sample_rate = None
        self.position = None
        self.chunk_size = 4096
        self.num_bars = 128
        self.prev_fft = np.zeros(self.num_bars)
        self.is_playing = False
        self.total_samples = 0

    def resize_layout(self,event=None):
        width = self.winfo_width()
        height = self.winfo_height()

        vis_height = int(height * 0.75)
        vis_width = int(width * 0.95)

        self.canvas.configure(width=vis_width, height=vis_height)
        self.progress_bg.configure(width=vis_width)
        self.volume_slider.configure(width=int(vis_width * 0.5))

    def change_theme(self, theme_name):
        self.current_theme = theme_name
        self.neon_core, self.neon_glow = self.themes[theme_name]

    def draw_bar_visualiser(self, fft):
        self.canvas.delete("all")

        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        bar_width = width / self.num_bars
        gap = bar_width * 0.45
        pulse = 1.0 + self.bass_energy * 0.25
        max_height = height * 0.9

        for i, value in enumerate(fft):
            # perceptual scaling
            value = np.sqrt(value)
            value = np.power(value, 0.8)

            x0 = i * bar_width + gap / 2
            x1 = x0 + bar_width - gap

            y1 = height
            y0 = y1 - (value * pulse * max_height)

            glow = int(2 + self.bass_energy * 1.5)

            self.canvas.create_rectangle(x0 - glow, y0 - glow,x1 + glow, y1,fill=self.neon_glow,outline="")
            self.canvas.create_rectangle(x0, y0,x1, y1,fill=self.neon_core,outline="")

    def draw_circle_visualiser(self, fft):
        self.canvas.delete("all")

        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        cx = width / 2
        cy = height / 2

        base_radius = 160
        pulse_radius = base_radius * (1 + self.bass_energy * 0.25)
        max_bar_length = 220

        angle_step = 2 * np.pi / self.num_bars

        for i, value in enumerate(fft):
            angle = i * angle_step

            inner_x = cx + pulse_radius * np.cos(angle)
            inner_y = cy + pulse_radius * np.sin(angle)

            bar_len = value * max_bar_length * (1 + self.bass_energy * 0.4)
            outer_x = cx + (pulse_radius + bar_len) * np.cos(angle)
            outer_y = cy + (pulse_radius + bar_len) * np.sin(angle)

            glow_width = int(2 + self.bass_energy * 3)

            # Glow
            self.canvas.create_line(inner_x, inner_y,outer_x, outer_y,fill=self.neon_glow,width=glow_width + 4)

            # Core neon line
            self.canvas.create_line(inner_x, inner_y,outer_x, outer_y,fill=self.neon_core,width=glow_width)

    def load_song(self,filepath,filename):
        self.song_label.configure(text=filename)
        y,sr = librosa.load(filepath, mono=True)
        self.audio_data = y
        self.sample_rate = sr
        self.total_samples = len(y)
        self.position = 0
        self.prev_fft = np.zeros(self.num_bars)
        self.is_playing = False
        self.update_progress_bar()

    def seek_audio(self, event):
        if self.audio_data is None:
            return

        progress = event.x / self.progress_bg.winfo_width()
        progress = max(0.0, min(1.0, progress))

        self.pause_offset = progress * (self.total_samples / self.sample_rate)
        self.start_time = pygame.time.get_ticks() / 1000 - self.pause_offset

        pygame.mixer.music.play(start=self.pause_offset)
        self.prev_fft = np.zeros(self.num_bars)
        self.is_playing = True
        self.play_button.configure(text="Pause")
        self.update_bars()

    def toggle_mode(self):
        if self.visualiser_mode == "bars":
            self.visualiser_mode = "circle"
            self.mode_button.configure(text="Switch to Bars")
        else:
            self.visualiser_mode = "bars"
            self.mode_button.configure(text="Switch to Circle")

    def toggle_play(self):
        if self.audio_data is None:
            return

        if not self.is_playing:
            if self.start_time is None:
                pygame.mixer.music.play(start=self.pause_offset)
                self.start_time = pygame.time.get_ticks() / 1000 - self.pause_offset
            else:
                pygame.mixer.music.unpause()
                self.start_time = pygame.time.get_ticks() / 1000 - self.pause_offset

            self.is_playing = True
            self.play_button.configure(text="Pause")
            self.update_bars()

        else:
            pygame.mixer.music.pause()
            self.pause_offset = (pygame.time.get_ticks() / 1000) - self.start_time
            self.is_playing = False
            self.play_button.configure(text="Play")

    def stop_visualiser(self):
        pygame.mixer.music.stop()
        self.is_playing = False
        self.position = 0
        self.prev_fft = np.zeros(self.num_bars)
        self.canvas.delete("all")
        self.update_progress_bar()
        self.play_button.configure(text="Play")

    def on_back(self):
        pygame.mixer.music.stop()
        self.is_playing = False
        self.position = 0
        self.pause_offset = 0.0
        self.start_time = None
        self.prev_fft = np.zeros(self.num_bars)
        self.canvas.delete("all")
        self.play_button.configure(text="Play")
        self.controller.show_frame(MainPage)

    def skip_seconds(self,sec):
        if self.audio_data is None:
            return

        new_pos = self.position + int(sec * self.sample_rate)
        new_pos = max(0, min(self.total_samples - 1, new_pos))

        self.position = new_pos
        self.start_time = pygame.time.get_ticks() / 1000 - (new_pos / self.sample_rate)
        pygame.mixer.music.play(start=new_pos / self.sample_rate)
        self.prev_fft = np.zeros(self.num_bars)

    def restart_song(self):
        if self.audio_data is None:
            return

        self.pause_offset = 0.0
        self.start_time = pygame.time.get_ticks() / 1000
        pygame.mixer.music.play(start=0)

        self.prev_fft = np.zeros(self.num_bars)
        self.is_playing = True
        self.play_button.configure(text="Pause")
        self.update_bars()

    def update_progress_bar(self):
        self.progress_bg.delete("all")
        width = self.progress_bg.winfo_width()
        self.progress_bg.create_rectangle(0, 0, width, 14, fill="#444444", outline="")

        if self.total_samples == 0:
            return

        progress = self.position/self.total_samples
        progress_width = self.progress_bg.winfo_width() * max(0.0,min(1.0,progress))
        self.progress_bg.create_rectangle(0,0,progress_width,40,fill="white",outline="black")

    def update_bars(self):
        if not self.is_playing or self.audio_data is None:
            return

        current_time = pygame.time.get_ticks() / 1000
        elapsed = current_time - self.start_time
        self.position = int(elapsed * self.sample_rate)

        if self.position + self.chunk_size >= self.total_samples:
            self.is_playing = False
            self.play_button.configure(text="Play")
            return

        chunk = self.audio_data[self.position:self.position + self.chunk_size]

        fft = np.abs(np.fft.rfft(chunk))
        fft = fft[:self.num_bars]

        fft /= np.max(fft) + 1e-6

        bass_range = int(self.num_bars * 0.2)
        mid_range = int(self.num_bars * 0.6)

        fft[:bass_range] *= 1.5
        fft[bass_range:mid_range] *= 1.0
        fft[mid_range:] *= 1.2
        fft = np.clip(fft, 0.0, 1.0)

        smoothing = 0.85  # higher = smoother
        fft = smoothing * self.prev_fft + (1 - smoothing) * fft
        self.prev_fft = fft

        # gentle perceptual curve
        fft = np.power(fft, 0.75)

        bass_energy = np.mean(fft[:int(self.num_bars * 0.15)])
        self.bass_energy = bass_energy

        if self.visualiser_mode == "bars":
            self.draw_bar_visualiser(fft)
        else:
            self.draw_circle_visualiser(fft)

        current_sec = elapsed
        total_sec = self.total_samples / self.sample_rate

        def fmt(t):
            return f"{int(t // 60):02d}:{int(t % 60):02d}"

        self.time_label.configure(text=f"{fmt(current_sec)} / {fmt(total_sec)}")
        self.update_progress_bar()

        self.after(16, self.update_bars)


app = App()
app.mainloop()
