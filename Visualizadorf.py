from Config.config import *
from tkinter import messagebox
import json
import os
import re
import pandas as pd


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



