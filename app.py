# Salve como app.py
from flask import Flask, render_template, request, send_file
import sqlite3
from datetime import datetime
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import io
import os

app = Flask(__name__)

# Dicionário de traduções (PT e EN para simplicidade)
TRADUCOES = {
    "pt": {
        "titulo": "Calculadora de ITB",
        "nome_paciente": "Nome do Paciente",
        "registro": "Registro",
        "pressao_braco": "Pressão Braço (mmHg)",
        "pressao_tornozelo": "Pressão Tornozelo (mmHg)",
        "momento": "Momento",
        "salvar_calcular": "Salvar e Calcular",
        "limpar": "Limpar",
        "exportar_excel": "Exportar Excel",
        "exportar_pdf": "Exportar PDF",
        "lingua_label": "Idioma",
        "resultado": "Resultado aparecerá aqui.",
        "tabela_nome": "Nome",
        "tabela_registro": "Registro",
        "tabela_data": "Data",
        "tabela_itb": "ITB",
        "tabela_momento": "Momento",
        "erro_nome": "Nome do paciente é obrigatório.",
        "erro_valor": "Insira valores numéricos válidos.",
        "erro_zero": "A pressão do braço não pode ser zero.",
        "aviso_exportar": "Nenhum dado para exportar.",
        "sucesso_exportar": "Dados exportados com sucesso.",
        "antes": "Pré-tratamento",
        "depois": "Pós-tratamento",
        "politica_texto": "Este aplicativo coleta dados como nome do paciente, registro e pressões arteriais para cálculos de ITB, armazenados localmente. Usamos anúncios do Google AdMob, que podem coletar identificadores de dispositivo para personalização. Não compartilhamos dados com terceiros além do necessário para anúncios. Conforme a LGPD, você tem direito a acessar ou excluir seus dados. Contato: elvascular@icloud.com.",
        "consentimento": "Eu aceito os termos da Política de Privacidade e permito o uso de dados para anúncios personalizados."
    },
    "en": {
        "titulo": "ITB Calculator",
        "nome_paciente": "Patient Name",
        "registro": "Record",
        "pressao_braco": "Arm Pressure (mmHg)",
        "pressao_tornozelo": "Ankle Pressure (mmHg)",
        "momento": "Moment",
        "salvar_calcular": "Save and Calculate",
        "limpar": "Clear",
        "exportar_excel": "Export to Excel",
        "exportar_pdf": "Export to PDF",
        "lingua_label": "Language",
        "resultado": "Result will appear here.",
        "tabela_nome": "Name",
        "tabela_registro": "Record",
        "tabela_data": "Date",
        "tabela_itb": "ITB",
        "tabela_momento": "Moment",
        "erro_nome": "Patient name is required.",
        "erro_valor": "Please enter valid numeric values.",
        "erro_zero": "Arm pressure cannot be zero.",
        "aviso_exportar": "No data to export.",
        "sucesso_exportar": "Data exported successfully.",
        "antes": "Pre-treatment",
        "depois": "Post-treatment",
        "politica_texto": "This app collects data such as patient name, record, and arterial pressures for ITB calculations, stored locally. We use Google AdMob ads, which may collect device identifiers for personalization. Data is not shared with third parties beyond ad requirements. Per LGPD, you can access or delete your data. Contact: elvascular@icloud.com.",
        "consentimento": "I accept the Privacy Policy terms and allow data use for personalized ads."
    }
}

# Função para criar conexão com o banco
def get_db_connection():
    conn = sqlite3.connect("itb_pacientes.db")
    conn.row_factory = sqlite3.Row  # Permite acessar colunas por nome
    return conn

# Inicializar o banco (chamado apenas uma vez no início)
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pacientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            registro TEXT,
            data TEXT NOT NULL,
            pressao_braco REAL,
            pressao_tornozelo REAL,
            itb REAL,
            momento TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Chamar a inicialização apenas uma vez
init_db()

@app.route('/', methods=['GET', 'POST'])
def index():
    lingua = request.args.get('lingua', 'pt')
    trad = TRADUCOES[lingua]
    resultado = ""
    historico = []

    # Criar conexão SQLite dentro da rota
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        registro = request.form.get('registro', '').strip()
        pressao_braco = request.form.get('pressao_braco', '')
        pressao_tornozelo = request.form.get('pressao_tornozelo', '')
        momento = request.form.get('momento', trad["antes"])

        if not nome:
            resultado = trad["erro_nome"]
        else:
            try:
                pressao_braco = float(pressao_braco)
                pressao_tornozelo = float(pressao_tornozelo)
                if pressao_braco == 0:
                    resultado = trad["erro_zero"]
                else:
                    itb = pressao_tornozelo / pressao_braco
                    if itb > 1.3:
                        interpretacao = "ITB > 1.3: Possible arterial stiffness."
                    elif 0.9 <= itb <= 1.3:
                        interpretacao = "ITB 0.9 - 1.3: Normal."
                    elif 0.5 <= itb < 0.9:
                        interpretacao = "ITB 0.5 - 0.9: Mild to moderate PAD."
                    elif 0.4 <= itb < 0.5:
                        interpretacao = "ITB 0.4 - 0.5: Severe PAD."
                    else:
                        interpretacao = "ITB < 0.4: Critical ischemia."
                    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute('INSERT INTO pacientes (nome, registro, data, pressao_braco, pressao_tornozelo, itb, momento) VALUES (?, ?, ?, ?, ?, ?, ?)',
                                   (nome, registro, data_atual, pressao_braco, pressao_tornozelo, itb, momento))
                    conn.commit()
                    resultado = f"ITB: {itb:.2f} - {interpretacao} - {trad['sucesso_exportar']}"
            except ValueError:
                resultado = trad["erro_valor"]

    cursor.execute("SELECT nome, registro, data, itb, momento FROM pacientes ORDER BY data DESC")
    historico = cursor.fetchall()
    conn.close()

    return render_template('index.html', trad=trad, resultado=resultado, historico=historico, lingua=lingua)

@app.route('/exportar_excel')
def exportar_excel():
    lingua = request.args.get('lingua', 'pt')
    trad = TRADUCOES[lingua]
    nome = request.args.get('nome', '')

    # Criar conexão SQLite dentro da rota
    conn = get_db_connection()
    cursor = conn.cursor()

    if nome:
        cursor.execute("SELECT * FROM pacientes WHERE nome = ? ORDER BY data", (nome,))
    else:
        cursor.execute("SELECT * FROM pacientes")
    
    dados = cursor.fetchall()
    conn.close()

    if not dados:
        return trad["aviso_exportar"]

    colunas = ["ID", trad["tabela_nome"], trad["tabela_registro"], trad["tabela_data"],
               trad["pressao_braco"], trad["pressao_tornozelo"], trad["tabela_itb"], trad["tabela_momento"]]
    df = pd.DataFrame(dados, columns=colunas)
    
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, download_name="itb_export.xlsx", as_attachment=True)

@app.route('/exportar_pdf')
def exportar_pdf():
    lingua = request.args.get('lingua', 'pt')
    trad = TRADUCOES[lingua]
    nome = request.args.get('nome', '')

    # Criar conexão SQLite dentro da rota
    conn = get_db_connection()
    cursor = conn.cursor()

    if nome:
        cursor.execute("SELECT * FROM pacientes WHERE nome = ? ORDER BY data", (nome,))
    else:
        cursor.execute("SELECT * FROM pacientes")
    
    dados = cursor.fetchall()
    conn.close()

    if not dados:
        return trad["aviso_exportar"]

    output = io.BytesIO()
    pdf = SimpleDocTemplate(output, pagesize=letter)
    elementos = []
    styles = getSampleStyleSheet()
    elementos.append(Paragraph(trad["relatorio_titulo"] + (f" - {nome}" if nome else ""), styles["Title"]))
    elementos.append(Spacer(1, 12))

    colunas = ["ID", trad["tabela_nome"], trad["tabela_registro"], trad["tabela_data"],
               trad["pressao_braco"], trad["pressao_tornozelo"], trad["tabela_itb"], trad["tabela_momento"]]
    tabela_dados = [colunas] + [list(row) for row in dados]
    tabela = Table(tabela_dados)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
    ]))
    elementos.append(tabela)
    pdf.build(elementos)
    output.seek(0)
    return send_file(output, download_name="itb_export.pdf", as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)