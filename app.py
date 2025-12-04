import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

# Configurazione Pagina
st.set_page_config(page_title="Spoglio Sceneggiatura", layout="wide")

st.title("🎬 Spoglio Sceneggiatura Automatico")
st.markdown("Carica il PDF. L'app estrarrà solo le Intestazioni di Scena ignorando dialoghi e azioni.")

# Upload File
uploaded_file = st.file_uploader("Carica la tua sceneggiatura (PDF)", type="pdf")

def parse_screenplay(file):
    data = []
    
    with pdfplumber.open(file) as pdf:
        for i, page in enumerate(pdf.pages):
            # extract_text con layout=True aiuta a sistemare le spaziature strane (E S T)
            text = page.extract_text(layout=True, x_tolerance=2, y_tolerance=3)
            
            if not text:
                continue

            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                
                # 1. FIX SPAZIATURA ESTREMA
                # Se la riga è "1 . E S T - I N T", la compattiamo
                # Rimuoviamo spazi tra lettere singole maiuscole (es. "E S T" -> "EST")
                # Questa regex cerca lettere maiuscole separate da 1 spazio e le unisce
                line_compact = re.sub(r'(?<=[A-Z0-9])\s(?=[A-Z0-9])', '', line)
                
                # Ripristiniamo lo spazio dopo il punto del numero scena (es "1.EST" -> "1. EST")
                line_compact = re.sub(r'(\d+)\.', r'\1. ', line_compact)

                # 2. RICONOSCIMENTO SCENA
                # Cerca un numero all'inizio, un punto, e parole chiave
                # Ora che la riga è compattata, le parole chiave sono leggibili
                regex_scene = r'^(\d+)\.\s+.*(EST|INT|EXT|I\/E|E\/I)'
                
                match = re.search(regex_scene, line_compact, re.IGNORECASE)
                
                if match:
                    # Abbiamo trovato una scena!
                    scene_num = match.group(1)
                    full_text = line_compact.replace(f"{scene_num}.", "").strip()
                    
                    # Analisi componenti (IE / GN / Ambiente)
                    ie = ""
                    gn = ""
                    
                    # Estrai I/E
                    match_ie = re.search(r'\b(EST-INT|INT-EST|EST/INT|INT/EST|I/E|E/I|EST|INT|EXT)\b', full_text, re.IGNORECASE)
                    if match_ie:
                        ie = match_ie.group(0).upper()
                        full_text = full_text.replace(ie, "").strip()
                    
                    # Estrai G/N (Cerca alla fine o in mezzo)
                    match_gn = re.search(r'\b(GIORNO|NOTTE|ALBA|TRAMONTO|SERA|POMERIGGIO)\b', full_text, re.IGNORECASE)
                    if match_gn:
                        gn = match_gn.group(0).upper()
                        full_text = full_text.replace(gn, "").strip()
                    
                    # Pulizia Ambiente
                    # Rimuovi trattini, slash e punti rimasti all'inizio o fine
                    full_text = re.sub(r'^[\/\-\–\.]+|[\/\-\–\.]+$', '', full_text).strip()
                    
                    # Dividi Ambiente e Sottoambiente
                    parts = re.split(r'[\-\–]', full_text)
                    parts = [p.strip() for p in parts if p.strip()]
                    
                    ambiente = parts[0] if len(parts) > 0 else ""
                    sottoambiente = " - ".join(parts[1:]) if len(parts) > 1 else ""

                    # Controllo qualità: se l'ambiente è troppo lungo (>50 chars), probabilmente abbiamo preso spazzatura
                    if len(ambiente) < 60:
                        data.append({
                            "Scena": scene_num,
                            "I/E": ie,
                            "G/N": gn,
                            "Ambiente": ambiente,
                            "Sottoambiente": sottoambiente,
                            "Note": ""
                        })

    return pd.DataFrame(data)

if uploaded_file is not None:
    with st.spinner('Analisi in corso...'):
        try:
            df = parse_screenplay(uploaded_file)
            
            if not df.empty:
                st.success(f"Trovate {len(df)} scene!")
                
                # Tabella editabile
                edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
                
                # Export CSV
                csv = edited_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Scarica CSV",
                    data=csv,
                    file_name='spoglio_sceneggiatura.csv',
                    mime='text/csv',
                )
            else:
                st.warning("Nessuna scena trovata. Verifica che il PDF sia leggibile.")
                
        except Exception as e:
            st.error(f"Errore: {e}")

# Footer Istruzioni
with st.expander("Vedi testo grezzo (Debug)"):
    if uploaded_file:
        with pdfplumber.open(uploaded_file) as pdf:
            st.text(pdf.pages[0].extract_text(layout=True))