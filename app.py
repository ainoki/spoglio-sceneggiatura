import streamlit as st
import pdfplumber
import pandas as pd
import re

# Configurazione Pagina
st.set_page_config(page_title="Spoglio Sceneggiatura", layout="wide")

st.title("🎬 Spoglio Sceneggiatura Automatico")
st.markdown("Versione Finale: accetta anche scene speciali (es. Titoli/Montaggi) prive di INT/EST.")

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

                # --- 1. FIX SPAZIATURA CHIRURGICO ---
                # Corregge spazi strani solo nelle parole chiave note
                line = line.replace("E S T", "EST")
                line = line.replace("I N T", "INT")
                line = line.replace("E X T", "EXT")
                line = line.replace("G I O R N O", "GIORNO")
                line = line.replace("N O T T E", "NOTTE")
                line = line.replace("S E R A", "SERA")
                line = line.replace("A L B A", "ALBA")
                line = line.replace("T R A M O N T O", "TRAMONTO")
                
                # Corregge "1 ." in "1."
                line = re.sub(r'(\d+)\s+\.', r'\1.', line)

                # --- 2. RICONOSCIMENTO SCENA (RELAXED) ---
                # Cerca semplicemente un numero seguito da un punto all'inizio della riga
                regex_start = r'^(\d+)\.\s+(.*)'
                
                match = re.search(regex_start, line)
                
                if match:
                    scene_num = match.group(1)
                    raw_content = match.group(2).strip()
                    
                    # FILTRO DI SICUREZZA:
                    # Per evitare di prendere liste numerate nei dialoghi (es. "1. Ciao"),
                    # accettiamo la riga SOLO SE:
                    # A) Contiene parole chiave (INT/EST/EXT)
                    # OPPURE
                    # B) È scritta quasi tutta in MAIUSCOLO (come la Scena 6)
                    
                    is_header_keywords = re.search(r'\b(EST|INT|EXT|I\/E|E\/I)\b', raw_content, re.IGNORECASE)
                    
                    # Calcoliamo se la riga è prevalentemente maiuscola (ignorando numeri e simboli)
                    clean_chars = re.sub(r'[^a-zA-Z]', '', raw_content)
                    is_uppercase = clean_chars.isupper() if clean_chars else False
                    
                    # Se non ha le parole chiave E non è maiuscola, probabilmente non è una scena
                    if not is_header_keywords and not is_uppercase:
                        continue

                    # --- 3. ESTRAZIONE DATI ---
                    full_text = raw_content
                    ie = ""
                    gn = ""
                    
                    # A. Trova I/E (Opzionale)
                    match_ie = re.search(r'\b(EST-INT|INT-EST|EST/INT|INT/EST|I/E|E/I|EST|INT|EXT)\b', full_text, re.IGNORECASE)
                    if match_ie:
                        ie = match_ie.group(0).upper()
                        full_text = full_text.replace(ie, "", 1).strip()
                    
                    # B. Trova G/N (Opzionale)
                    match_gn = re.search(r'\b(GIORNO|NOTTE|ALBA|TRAMONTO|SERA|POMERIGGIO)\b', full_text, re.IGNORECASE)
                    if match_gn:
                        gn = match_gn.group(0).upper()
                        full_text = full_text.replace(gn, "", 1).strip()
                    
                    # C. Pulizia residui iniziali
                    full_text = re.sub(r'^[\s\/\-\–\.]+', '', full_text).strip()
                    
                    # D. Split Ambiente / Sottoambiente
                    # Dividiamo sul trattino
                    parts = re.split(r'[\-\–]', full_text)
                    parts = [p.strip() for p in parts if p.strip()]
                    
                    ambiente = parts[0] if len(parts) > 0 else ""
                    sottoambiente = " - ".join(parts[1:]) if len(parts) > 1 else ""

                    # Controllo lunghezza (evita false catture di paragrafi lunghi)
                    if len(ambiente) < 100: 
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
                st.warning("Nessuna scena trovata.")

        except Exception as e:
            st.error(f"Errore: {e}")
