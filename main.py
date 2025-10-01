from Config.config import *
from Visualizadorf import gerar_relatorio_inicial
from Classes.ValidarPlacas import ValidadorPlacasGUI
import tkinter as tk
from tkinter import filedialog, messagebox
import os


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
