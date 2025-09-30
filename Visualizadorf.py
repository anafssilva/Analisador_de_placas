import json
import os
import re
import shutil
import tkinter as tk
from tkinter import filedialog, font, messagebox

import pandas as pd
from PIL import Image, ImageTk

# --- CONFIGURAÇÕES GERAIS ---
NOME_DA_ABA = "Relatorio"
NOME_ARQUIVO_EXCEL = "Relatorio_Placas_Processadas.xlsx"
COLUNAS_RELATORIO = [
    "Câmera",
    "Data e Hora",
    "Placa Lida (JSON)",
    "Placa Verificada (Manual)",
    "Confiabilidade Total",
    "Acurácia",
    "Confiabilidade Letra a Letra",
    "H (Altura)",
    "Coordenada Sup. Dir.",
    "Arquivo JSON",
    "Arquivo JPG Encontrado",
]
TOLERANCIA_MINUTOS = 5
CONFERIDOS_FOLDER = "ARQUIVOS_CONFERIDOS"


def parse_jpg_filename(filename):
    """Extrai a placa e o objeto datetime do nome do JPG, se o padrão existir."""
    match = re.search(r"-([A-Z0-9]{7})-(\d{8}T\d{6})", filename)
    if match:
        plate = match.group(1)
        timestamp_str = match.group(2).replace("T", "")
        timestamp = pd.to_datetime(
            timestamp_str, format="%Y%m%d%H%M%S", errors="coerce"
        )
        if pd.notna(timestamp):
            return {"plate": plate, "timestamp": timestamp, "filename": filename}
    return None


def gerar_relatorio_inicial(pasta_selecionada):
    """Fase 1: Gera a planilha Excel com lógica de busca de JPG aprimorada."""
    print("FASE 1: Gerando novo relatório inicial.")
    caminho_saida_excel = os.path.join(pasta_selecionada, NOME_ARQUIVO_EXCEL)

    todos_jpgs = [
        f
        for f in os.listdir(pasta_selecionada)
        if f.lower().endswith((".jpg", ".jpeg"))
    ]
    jpgs_parseados = [
        parsed for f in todos_jpgs if (parsed := parse_jpg_filename(f)) is not None
    ]

    dados_compilados = []
    arquivos_json_na_pasta = [
        f for f in os.listdir(pasta_selecionada) if f.lower().endswith("_json.txt")
    ]

    if not arquivos_json_na_pasta:
        messagebox.showerror("Erro", "Nenhum arquivo '_json.txt' encontrado na pasta.")
        return None

    count_ideal = 0
    count_fallback = 0

    for nome_arquivo_json in arquivos_json_na_pasta:
        try:
            with open(
                os.path.join(pasta_selecionada, nome_arquivo_json),
                "r",
                encoding="utf-8",
            ) as f:
                data = json.load(f)

            placa_lida = data.get("plate", data.get("placa", "N/A")).strip()
            data_evento = pd.to_datetime(
                data.get("start", ""), format="%Y%m%dT%H%M%S", errors="coerce"
            )

            imagem_encontrada = "Nenhuma"

            if pd.notna(data_evento) and len(placa_lida) == 7:
                inicio_janela = data_evento - pd.Timedelta(minutes=TOLERANCIA_MINUTOS)
                fim_janela = data_evento + pd.Timedelta(minutes=TOLERANCIA_MINUTOS)
                for jpg_info in jpgs_parseados:
                    if (
                        jpg_info["plate"] == placa_lida
                        and inicio_janela <= jpg_info["timestamp"] <= fim_janela
                    ):
                        imagem_encontrada = jpg_info["filename"]
                        count_ideal += 1
                        break

            if imagem_encontrada == "Nenhuma":
                base_name = nome_arquivo_json.replace("_json.txt", "").lower()
                for jpg_file in todos_jpgs:
                    if jpg_file.lower().startswith(base_name):
                        imagem_encontrada = jpg_file
                        count_fallback += 1
                        break

            dados_compilados.append(
                {
                    "Câmera": data.get("Lane", "N/A"),
                    "Data e Hora": (
                        data_evento.strftime("%d/%m/%Y %H:%M:%S")
                        if pd.notna(data_evento)
                        else ""
                    ),
                    "Placa Lida (JSON)": placa_lida,
                    "Placa Verificada (Manual)": "",
                    "Acurácia": "",
                    "Confiabilidade Total": (
                        f"{data.get('hiConf', 0.0):.2f}%"
                        if isinstance(data.get("hiConf"), float)
                        else data.get("hiConf", 0.0)
                    ),
                    "Confiabilidade Letra a Letra": str(data.get("carConf", "N/A")),
                    "H (Altura)": data.get("height", "N/A"),
                    "Coordenada Sup. Dir.": (
                        f"({p[2]}, {p[1]})"
                        if len(p := data.get("platePos", [])) == 4
                        else "N/A"
                    ),
                    "Arquivo JSON": nome_arquivo_json,
                    "Arquivo JPG Encontrado": imagem_encontrada,
                }
            )
        except Exception as e:
            print(f"⚠️ AVISO: Ignorando arquivo '{nome_arquivo_json}' por erro: {e}")

    print("-" * 30)
    print("Resumo da busca por JPGs:")
    print(f"Correspondências pela busca ideal (Placa+Data): {count_ideal}")
    print(f"Correspondências pela busca alternativa (Nome): {count_fallback}")
    print(
        f"Total de JSONs sem JPG correspondente: {len(arquivos_json_na_pasta) - (count_ideal + count_fallback)}"
    )
    print("-" * 30)

    if not dados_compilados:
        messagebox.showerror(
            "Erro", "Nenhum dado foi compilado. Verifique os arquivos JSON."
        )
        return None

    df = pd.DataFrame(dados_compilados)
    df_final = df.reindex(columns=COLUNAS_RELATORIO).copy()
    df_final["Arquivo JPG Encontrado (Link)"] = [
        f'=HYPERLINK("{f}", "Abrir JPG")' if f != "Nenhuma" else "Nenhuma"
        for f in df["Arquivo JPG Encontrado"]
    ]
    df_final["Arquivo JSON (Link)"] = [
        f'=HYPERLINK("{f}", "Abrir JSON")' for f in df["Arquivo JSON"]
    ]

    try:
        df_final.to_excel(
            caminho_saida_excel, index=False, sheet_name=NOME_DA_ABA, engine="openpyxl"
        )
        print(f"✅ SUCESSO! Novo relatório salvo em: {caminho_saida_excel}")
        return caminho_saida_excel
    except Exception as e:
        messagebox.showerror(
            "Erro ao Salvar",
            f"Não foi possível salvar o Excel. Verifique se o arquivo não está aberto.\nDetalhe: {e}",
        )
        return None


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


def main():
    root = tk.Tk()
    root.withdraw()

    pasta_trabalho = filedialog.askdirectory(
        title="Selecione a pasta com os arquivos de placas"
    )
    if not pasta_trabalho:
        print("Nenhuma pasta selecionada. Encerrando.")
        return

    # --- LÓGICA PARA CONTINUAR OU COMEÇAR DE NOVO ---
    caminho_excel_existente = os.path.join(pasta_trabalho, NOME_ARQUIVO_EXCEL)
    caminho_excel_para_validar = ""

    if os.path.exists(caminho_excel_existente):
        continuar = messagebox.askyesno(
            "Relatório Encontrado",
            "Um relatório existente foi encontrado nesta pasta.\n\nDeseja continuar a validação anterior?",
        )
        if continuar:
            print("Continuando validação a partir de relatório existente.")
            caminho_excel_para_validar = caminho_excel_existente
        else:
            caminho_excel_para_validar = gerar_relatorio_inicial(pasta_trabalho)
    else:
        caminho_excel_para_validar = gerar_relatorio_inicial(pasta_trabalho)

    # --- INICIAR A GUI ---
    if caminho_excel_para_validar:
        print("Iniciando a interface de validação...")
        gui_root = tk.Toplevel()
        app = ValidadorPlacasGUI(gui_root, caminho_excel_para_validar, pasta_trabalho)
        gui_root.mainloop()
    else:
        print("Processo encerrado pois nenhum relatório foi gerado ou selecionado.")


if __name__ == "__main__":
    main()
