import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import yt_dlp
import os
import sys
import threading
import platform
import zipfile
import tarfile
import urllib.request
import shutil
import stat
import ssl

# --- CORREÇÃO NUCLEAR DO SSL (Mantida e Reforçada) ---
# Garante que o Python do Mac não bloqueie o download
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context
# -----------------------------------------------------

class UniversalDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Silverio Downloader")
        self.root.geometry("600x550")
        self.root.resizable(True, True)

        self.os_name = platform.system() 
        
        self.download_folder = tk.StringVar()
        self.url_var = tk.StringVar()
        self.status_var = tk.StringVar(value=f"Sistema: {self.os_name} | Inicializando...")
        self.progress_var = tk.DoubleVar()
        self.ffmpeg_installed = False # Flag para saber se temos poder total
        
        self.setup_paths()
        self.create_widgets()
        
        # Inicia verificação em background
        threading.Thread(target=self.check_and_install_ffmpeg, daemon=True).start()

    def setup_paths(self):
        user_home = os.path.expanduser("~")
        
        if self.os_name == "Windows":
            self.app_data_dir = os.path.join(os.environ.get('LOCALAPPDATA', user_home), "UniversalDownloader")
            self.ffmpeg_exe_name = "ffmpeg.exe"
        elif self.os_name == "Darwin": # Mac
            self.app_data_dir = os.path.join(user_home, "Library", "Application Support", "UniversalDownloader")
            self.ffmpeg_exe_name = "ffmpeg"
        else: # Linux
            self.app_data_dir = os.path.join(user_home, ".local", "share", "UniversalDownloader")
            self.ffmpeg_exe_name = "ffmpeg"

        self.ffmpeg_final_path = os.path.join(self.app_data_dir, self.ffmpeg_exe_name)

    def create_widgets(self):
        # Título
        tk.Label(self.root, text="YouTube Downloader Premium", font=("Segoe UI", 16, "bold")).pack(pady=10)
        
        # Status Label (Importante para feedback)
        self.lbl_status = tk.Label(self.root, textvariable=self.status_var, fg="#333", wraplength=550)
        self.lbl_status.pack(pady=5)

        # URL
        frame_url = tk.LabelFrame(self.root, text="URL do Vídeo", padx=10, pady=10)
        frame_url.pack(padx=20, pady=10, fill="x")
        self.url_entry = tk.Entry(frame_url, textvariable=self.url_var)
        self.url_entry.pack(fill="x")

        # Pasta
        frame_folder = tk.LabelFrame(self.root, text="Salvar em", padx=10, pady=10)
        frame_folder.pack(padx=20, pady=5, fill="x")
        
        self.entry_folder = tk.Entry(frame_folder, textvariable=self.download_folder, state='readonly')
        self.entry_folder.pack(side=tk.LEFT, fill="x", expand=True, padx=(0, 10))
        btn_folder = tk.Button(frame_folder, text="Escolher...", command=self.escolher_pasta)
        btn_folder.pack(side=tk.RIGHT)

        # Progresso
        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(padx=20, pady=20, fill="x")

        # Botão
        self.btn_download = tk.Button(self.root, text="Aguarde...", 
                                      command=self.iniciar_download_thread, 
                                      bg="#cccccc", state=tk.DISABLED, 
                                      font=("Segoe UI", 12, "bold"), height=2)
        self.btn_download.pack(padx=20, pady=10, fill="x")

    def check_and_install_ffmpeg(self):
        # Verifica se já temos o FFmpeg funcionando
        if os.path.exists(self.ffmpeg_final_path):
            self.ffmpeg_installed = True
            self.status_var.set("Modo 4K Ativado: FFmpeg detectado.")
            self.habilitar_botao(modo_maximo=True)
            return

        self.status_var.set("Configurando primeira execução (Baixando componentes de áudio)...")
        os.makedirs(self.app_data_dir, exist_ok=True)
        
        try:
            url = ""
            filename = ""
            
            # --- NOVOS LINKS (PERMALINKS) ---
            if self.os_name == "Windows":
                # Link oficial do BtbN (GitHub) que sempre aponta para o último zip
                url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
                filename = "ffmpeg.zip"
            elif self.os_name == "Darwin": # Mac
                # Link oficial do evermeet.cx que redireciona para o zip mais novo
                url = "https://evermeet.cx/ffmpeg/getrelease/zip"
                filename = "ffmpeg.zip"
            else: # Linux
                # Link oficial para build estática do Linux
                url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
                filename = "ffmpeg.tar.xz"

            download_path = os.path.join(self.app_data_dir, filename)

            # Configura Headers para evitar bloqueio 403/404
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            
            # Baixa
            with urllib.request.urlopen(req) as response, open(download_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            
            self.status_var.set("Extraindo FFmpeg...")

            # Extração
            if filename.endswith(".zip"):
                with zipfile.ZipFile(download_path, 'r') as z:
                    z.extractall(self.app_data_dir)
            elif filename.endswith(".tar.xz"):
                with tarfile.open(download_path, "r:xz") as t:
                    t.extractall(self.app_data_dir)

            # Busca Recursiva (Resolve o problema de pastas com nomes estranhos)
            found = False
            for root, dirs, files in os.walk(self.app_data_dir):
                if self.ffmpeg_exe_name in files:
                    source = os.path.join(root, self.ffmpeg_exe_name)
                    try:
                        shutil.move(source, self.ffmpeg_final_path)
                    except: pass
                    found = True
                    break
            
            if not found:
                raise Exception("Arquivo executável não encontrado após extração.")

            # Permissões
            if self.os_name != "Windows":
                st = os.stat(self.ffmpeg_final_path)
                os.chmod(self.ffmpeg_final_path, st.st_mode | stat.S_IEXEC)

            # Limpeza
            try: os.remove(download_path)
            except: pass

            self.ffmpeg_installed = True
            self.status_var.set("Instalação Completa! Modo 4K/Áudio habilitado.")
            self.habilitar_botao(modo_maximo=True)

        except Exception as e:
            # SE FALHAR, NÃO TRAVA MAIS O USUÁRIO
            print(f"Erro FFmpeg: {e}")
            self.ffmpeg_installed = False
            self.status_var.set(f"Aviso: FFmpeg não instalado ({str(e)}). Usando modo Compatibilidade (720p com Áudio).")
            self.habilitar_botao(modo_maximo=False)

    def habilitar_botao(self, modo_maximo=True):
        if modo_maximo:
            self.btn_download.config(state=tk.NORMAL, text="BAIXAR (Qualidade Máxima)", bg="#2ecc71", fg="white")
        else:
            self.btn_download.config(state=tk.NORMAL, text="BAIXAR (Modo Seguro/Áudio OK)", bg="#f1c40f", fg="black")

    def escolher_pasta(self):
        p = filedialog.askdirectory()
        if p: self.download_folder.set(p)

    def hook(self, d):
        if d['status'] == 'downloading':
            try:
                p = d.get('_percent_str', '0%').replace('%','')
                self.progress_var.set(float(p))
                self.root.update_idletasks()
            except: pass
        elif d['status'] == 'finished':
            self.status_var.set("Finalizando arquivo...")
            self.progress_var.set(100)

    def download_logic(self):
        url = self.url_var.get()
        folder = self.download_folder.get()
        
        if not url or not folder:
            messagebox.showwarning("Erro", "Preencha URL e Pasta!")
            self.habilitar_botao(self.ffmpeg_installed)
            return

        # LÓGICA INTELIGENTE DE SELEÇÃO DE FORMATO
        if self.ffmpeg_installed and os.path.exists(self.ffmpeg_final_path):
            # Tenta baixar o melhor vídeo e melhor áudio separados e junta
            formato = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            ffmpeg_loc = self.ffmpeg_final_path
            msg_sucesso = "Vídeo baixado em alta qualidade!"
        else:
            # FALLBACK DE SEGURANÇA:
            # Baixa o melhor formato ÚNICO disponível (geralmente 720p mp4).
            # Isso garante que VÍDEO e ÁUDIO venham juntos num arquivo só.
            formato = 'best' 
            ffmpeg_loc = None
            msg_sucesso = "Vídeo baixado! (Modo Compatibilidade)"

        ydl_opts = {
            'format': formato,
            'outtmpl': os.path.join(folder, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'ffmpeg_location': ffmpeg_loc,
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'progress_hooks': [self.hook],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            self.status_var.set("Pronto!")
            messagebox.showinfo("Sucesso", msg_sucesso)
            self.progress_var.set(0)
            self.url_var.set("")
        except Exception as e:
            messagebox.showerror("Erro Fatal", f"Ocorreu um erro:\n{e}")
            self.status_var.set("Erro no download.")
        finally:
            self.habilitar_botao(self.ffmpeg_installed)

    def iniciar_download_thread(self):
        self.btn_download.config(state=tk.DISABLED, text="Baixando...")
        threading.Thread(target=self.download_logic).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = UniversalDownloader(root)
    root.mainloop()