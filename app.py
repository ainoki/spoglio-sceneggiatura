import streamlit as st
import pdfplumber
import pandas as pd
import re

# Configurazione Pagina
st.set_page_config(page_title="Spoglio Sceneggiatura", layout="wide")

st.title("🎬 Spoglio Sceneggiatura Automatico")
st.markdown("Versione aggiornata: corregge la spaziatura senza unire le parole dell'ambiente.")

uploaded_file = st.file_uploader("Carica la tua sceneggiatura (PDF)", type="pdf")

def parse_screenplay(file):
    data = []
    
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            # Estrazione testo mantenendo il layout
            text = page.extract_text(layout=True)
            
            if not text:
                continue

            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line: continue

                # --- FIX SPAZIATURA CHIRURGICO ---
                # Invece di togliere tutti gli spazi, correggiamo solo le parole chiave note
                # che nel tuo PDF appaiono spaziate (E S T -> EST)
                line = line.replace("E S T", "EST")
                line = line.replace("I N T", "INT")
                line = line.replace("E X T", "EXT")
                line = line.replace("G I O R N O", "GIORNO")
                line = line.replace("N O T T E", "NOTTE")
                line = line.replace("S E R A", "SERA")
                line = line.replace("A L B A", "ALBA")
                line = line.replace("T R A M O N T O", "TRAMONTO")
                
                # Correggiamo anche "1 ." in "1."
                line = re.sub(r'(\d+)\s+\.', r'\1.', line)

                # --- RICONOSCIMENTO SCENA ---
                # Cerca numero, punto e una delle parole chiave
                regex_scene = r'^(\d+)\.\s*.*(EST|INT|EXT|I\/E|E\/I)'
                
                match = re.search(regex_scene, line, re.IGNORECASE)
                
                if match:
                    scene_num = match.group(1)
                    
                    # Rimuoviamo il numero iniziale per pulire
                    full_text = re.sub(r'^\d+\.\s*', '', line).strip()
                    
                    # --- ESTRAZIONE DATI ---
                    ie = ""
                    gn = ""
                    
                    # 1. Trova I/E
                    match_ie = re.search(r'\b(EST-INT|INT-EST|EST/INT|INT/EST|I/E|E/I|EST|INT|EXT)\b', full_text, re.IGNORECASE)
                    if match_ie:
                        ie = match_ie.group(0).upper()
                        # Rimuoviamo IE dalla stringa
                        full_text = full_text.replace(ie, "", 1).strip()
                    
                    # 2. Trova G/N
                    match_gn = re.search(r'\b(GIORNO|NOTTE|ALBA|TRAMONTO|SERA|POMERIGGIO)\b', full_text, re.IGNORECASE)
                    if match_gn:
                        gn = match_gn.group(0).upper()
                        # Rimuoviamo GN dalla stringa
                        full_text = full_text.replace(gn, "", 1).strip()
                    
                    # 3. Pulizia Separatori iniziali (trattini, slash, punti rimasti)
                    full_text = re.sub(r'^[\s\/\-\–\.]+', '', full_text).strip()
                    
                    # 4. Dividi Ambiente e Sottoambiente
                    # Divide sul trattino (-) o lineetta lunga (–)
                    parts = re.split(r'[\-\–]', full_text)
                    parts = [p.strip() for p in parts if p.strip()]
                    
                    ambiente = parts[0] if len(parts) > 0 else ""
                    # Unisce il resto come sottoambiente
                    sottoambiente = " - ".join(parts[1:]) if len(parts) > 1 else ""

                    # Filtro anti-spazzatura (se l'ambiente è lunghissimo, non è una scena)
                    if len(ambiente) < 80: 
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
                st.warning("Nessuna scena trovata. Controlla il formato del PDF.")
                st.write("Suggerimento: Verifica se il PDF è un testo selezionabile e non una scansione.")

        except Exception as e:
            st.error(f"Si è verificato un errore: {e}")
