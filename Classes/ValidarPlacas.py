from Config.config import *
from tkinter import font, messagebox
from PIL import Image, ImageTk
import pandas as pd
import shutil
import tkinter as tk
import os


class ValidadorPlacasGUI:
    def __init__(self, root, caminho_excel, pasta_base):
        self.root = root
        self.caminho_excel = caminho_excel
        self.pasta_base = pasta_base
        self.df = None
        self.indices_para_validar = []
        self.index_atual = -1
        self.linha_idx = -1
        self.item_com_imagem_encontrado = False

        self.root.title("Validação de Placas v2.4")
        self.root.geometry("850x750")
        self.root.configure(bg="#2c2c2c")

        self.pasta_conferidos = os.path.join(self.pasta_base, CONFERIDOS_FOLDER)
        os.makedirs(self.pasta_conferidos, exist_ok=True)

        # --- Widgets ---
        self.contador_label = tk.Label(
            root, text="", bg="#2c2c2c", fg="#00ff7f", font=("Segoe UI", 14)
        )
        self.contador_label.pack(pady=(10, 0))
        self.img_label = tk.Label(root, bg="#2c2c2c", fg="white", font=("Segoe UI", 12))
        self.img_label.pack(pady=10, fill="both", expand=True)
        char_frame = tk.Frame(root, bg="#2c2c2c")
        char_frame.pack(pady=10)
        self.labels_originais = self._criar_labels_placa(char_frame, "Lida (JSON):", 0)
        self.labels_editados = self._criar_labels_placa(char_frame, "Verificada:", 1)
        self.placa_var = tk.StringVar()
        self.placa_var.trace_add("write", self.atualizar_display_caracteres)
        self.entry_placa = tk.Entry(
            root,
            textvariable=self.placa_var,
            font=("Courier New", 24, "bold"),
            width=15,
            justify="center",
            bg="#404040",
            fg="white",
            insertbackground="white",
        )
        self.entry_placa.pack(pady=20)
        btn_frame = tk.Frame(root, bg="#2c2c2c")
        btn_frame.pack(pady=20, fill="x", expand=True)
        self.btn_salvar = tk.Button(
            btn_frame,
            text="✅ Salvar e Próximo",
            command=self.processar_e_avancar,
            bg="#28a745",
            fg="white",
            font=("Segoe UI", 14, "bold"),
            width=25,
            relief="flat",
        )
        self.btn_salvar.pack(pady=5)

        self.root.protocol("WM_DELETE_WINDOW", self.ao_fechar)

        # --- Início do fluxo da GUI ---
        if self.carregar_dados_excel():
            self.proximo_item()
        else:
            self.root.destroy()

        if not self.item_com_imagem_encontrado and self.indices_para_validar:
            messagebox.showinfo(
                "Concluído",
                "Todos os itens pendentes foram processados ou não tinham imagens para validar.",
            )
            self.ao_fechar()

    def _criar_labels_placa(self, parent, texto_label, row_num):
        tk.Label(
            parent, text=texto_label, bg="#2c2c2c", fg="gray", font=("Segoe UI", 10)
        ).grid(row=row_num, column=0, padx=10, sticky="e")
        labels = []
        char_font = font.Font(family="Courier New", size=24, weight="bold")
        for i in range(7):
            lbl = tk.Label(
                parent,
                text="",
                width=2,
                font=char_font,
                bg="#333333",
                fg="white",
                bd=1,
                relief="solid",
            )
            lbl.grid(row=row_num, column=i + 1, padx=3, pady=3)
            labels.append(lbl)
        return labels

    def carregar_dados_excel(self):
        try:
            self.df = pd.read_excel(self.caminho_excel, sheet_name=NOME_DA_ABA)
            nao_validadas = self.df["Placa Verificada (Manual)"].isna() | (
                self.df["Placa Verificada (Manual)"].astype(str).str.strip() == ""
            )
            self.indices_para_validar = self.df[nao_validadas].index.tolist()

            print(
                f"FASE 2: Encontradas {len(self.indices_para_validar)} placas pendentes de validação."
            )
            if not self.indices_para_validar:
                messagebox.showinfo(
                    "Tudo Certo!",
                    "Não foram encontradas placas pendentes de validação na planilha.",
                )
                return False
            self.index_atual = -1
            return True
        except Exception as e:
            messagebox.showerror(
                "Erro ao Ler Excel",
                f"Não foi possível carregar o arquivo '{self.caminho_excel}'.\nErro: {e}",
            )
            return False

    def proximo_item(self):
        self.index_atual += 1
        if self.index_atual >= len(self.indices_para_validar):
            self.item_com_imagem_encontrado = True
            messagebox.showinfo("Fim", "Parabéns! Todos os itens foram validados.")
            self.ao_fechar()
            return

        self.linha_idx = self.indices_para_validar[self.index_atual]
        self.linha_atual = self.df.loc[self.linha_idx]

        nome_imagem = self.linha_atual.get("Arquivo JPG Encontrado")
        if pd.isna(nome_imagem):
            nome_imagem = "Nenhuma"

        caminho_imagem = (
            os.path.join(self.pasta_base, nome_imagem)
            if nome_imagem != "Nenhuma"
            else ""
        )

        if not caminho_imagem or not os.path.exists(caminho_imagem):
            print(
                f"INFO: Pulando automaticamente item (JSON: {self.linha_atual.get('Arquivo JSON')}) por falta de JPG."
            )
            self.registrar_falha_e_avancar()
            return

        self.item_com_imagem_encontrado = True
        placa_lida = str(self.linha_atual.get("Placa Lida (JSON)", ""))
        self.placa_original = placa_lida
        self.placa_var.set(placa_lida)

        self.atualizar_contador()
        self.carregar_imagem(caminho_imagem)
        self.atualizar_display_caracteres()

    def carregar_imagem(self, caminho_imagem):
        try:
            img = Image.open(caminho_imagem)
            img.thumbnail((800, 500), Image.Resampling.LANCZOS)
            self.tk_image = ImageTk.PhotoImage(img)
            self.img_label.config(image=self.tk_image, text="")
            self.entry_placa.config(state="normal")
            self.entry_placa.focus_set()
        except Exception as e:
            self.img_label.config(image="", text=f"Erro ao carregar imagem: {e}")
            self.entry_placa.config(state="disabled")

    def registrar_falha_e_avancar(self):
        self.atualizar_linha_df("JPG NAO ENCONTRADO", "N/A")
        self.mover_arquivos_processados()
        self.proximo_item()

    def processar_e_avancar(self):
        placa_verificada = self.placa_var.get().strip().upper()
        if len(placa_verificada) != 7:
            messagebox.showwarning(
                "Atenção", "A placa verificada deve ter 7 caracteres."
            )
            return
        acuracia = self.calcular_semelhanca(self.placa_original, placa_verificada)
        self.atualizar_linha_df(placa_verificada, f"{acuracia:.2f}%")
        self.mover_arquivos_processados()
        self.proximo_item()

    def atualizar_display_caracteres(self, *args):
        original = self.placa_original.upper().ljust(7)
        editada = self.placa_var.get().upper().ljust(7)
        for i in range(7):
            self.labels_originais[i].config(text=original[i])
            self.labels_editados[i].config(text=editada[i])
            if original[i] != " " and original[i] == editada[i]:
                self.labels_editados[i].config(bg="#006400")
            else:
                self.labels_editados[i].config(bg="#8B0000")

    def atualizar_contador(self):
        total_a_validar = len(self.indices_para_validar)
        validados_ate_agora = self.index_atual
        self.contador_label.config(
            text=f"Validando: {validados_ate_agora + 1} de {total_a_validar} pendentes"
        )

    def atualizar_linha_df(self, placa_verificada, acuracia_str):
        self.df.loc[self.linha_idx, "Placa Verificada (Manual)"] = placa_verificada
        self.df.loc[self.linha_idx, "Acurácia"] = acuracia_str

    def calcular_semelhanca(self, original, verificada):
        corretos = sum(
            1 for c1, c2 in zip(original.upper(), verificada.upper()) if c1 == c2
        )
        return (corretos / 7.0) * 100

    def mover_arquivos_processados(self):
        try:
            nome_json = self.linha_atual.get("Arquivo JSON")
            nome_jpg = self.linha_atual.get("Arquivo JPG Encontrado")
            if pd.isna(nome_jpg):
                nome_jpg = None

            if nome_json and os.path.exists(
                caminho := os.path.join(self.pasta_base, nome_json)
            ):
                shutil.move(
                    caminho,
                    os.path.join(self.pasta_conferidos, os.path.basename(nome_json)),
                )
            if nome_jpg and os.path.exists(
                caminho := os.path.join(self.pasta_base, nome_jpg)
            ):
                shutil.move(
                    caminho,
                    os.path.join(self.pasta_conferidos, os.path.basename(nome_jpg)),
                )
        except Exception as e:
            print(
                f"⚠️ AVISO: Não foi possível mover os arquivos da linha {self.linha_idx}. Erro: {e}"
            )

    def salvar_planilha(self):
        if self.df is None:
            return
        print("Salvando progresso na planilha...")
        try:
            self.df.to_excel(
                self.caminho_excel,
                index=False,
                sheet_name=NOME_DA_ABA,
                engine="openpyxl",
            )
            print("✅ Progresso salvo com sucesso!")
        except Exception as e:
            messagebox.showerror(
                "Erro ao Salvar",
                f"Não foi possível salvar as alterações no Excel.\nErro: {e}",
            )

    def ao_fechar(self):
        if self.df is not None:
            if messagebox.askyesno(
                "Sair", "Deseja salvar as alterações e fechar o validador?"
            ):
                self.salvar_planilha()
        self.root.destroy()