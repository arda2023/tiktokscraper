import customtkinter as ctk

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TikTok Scraper & Transcriber")
        self.geometry("600x400")
        
        self.label = ctk.CTkLabel(self, text="Welcome to TikTok Scraper")
        self.label.pack(pady=20)
