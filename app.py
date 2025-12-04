import streamlit as st
import pdfplumber
import pandas as pd
import re

# Configurazione Pagina
st.set_page_config(page_title="Spoglio Sceneggiatura", layout="wide")

st.title("🎬 Spoglio Sceneggiatura Automatico")
st.markdown("Versione Finale Pro: gestisce intestazioni spezzate su più righe (es. 'CAMERA DA' [a capo] 'LETTO').")

uploaded_file = st.file_uploader("Carica la tua sceneggiatura (PDF)", type="pdf")

def parse_screenplay(file):
    data = []
    
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text(layout=True)
            if not text: continue

            lines = text.split('\n')
            
            # Usiamo un ciclo while per poter gestire manualmente l'indice delle righe
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # Se la riga è vuota, passa alla prossima
                if not line: 
                    i += 1
                    continue

                # --- 1. NORMALIZZAZIONE ---
                line = line.replace("E S T", "EST").replace("I N T", "INT").replace("E X T", "EXT")
                line = line.replace("G I O R N O", "GIORNO").replace("N O T T E", "NOTTE")
                line = re.sub(r'(\d+)\s+\.', r'\1.', line)

                # --- 2. IDENTIFICAZIONE SCENA ---
                regex_start = r'^(\d+)\.\s+(.*)'
                match = re.search(regex_start, line)
                
                if match:
                    scene_num = match.group(1)
                    raw_content = match.group(2).strip()
                    
                    # Filtro validità (Maiuscolo o parole chiave)
                    is_header_keywords = re.search(r'\b(EST|INT|EXT|I\/E|E\/I)\b', raw_content, re.IGNORECASE)
                    clean_chars = re.sub(r'[^a-zA-Z]', '', raw_content)
                    is_uppercase = clean_chars.isupper() if clean_chars else False
                    
                    if not is_header_keywords and not is_uppercase:
                        i += 1
                        continue

                    # --- 3. FIX "SCENA SPEZZATA" (La Magia) ---
                    # Controlliamo se dobbiamo unire la riga successiva
                    if i + 1 < len(lines):
                        next_line = lines[i+1].strip()
                        
                        # Criteri per unire la riga successiva:
                        # A. La riga successiva è TUTTA MAIUSCOLA (e non è un numero pagina)
                        # B. E (La riga attuale finisce con preposizione/trattino OPPURE La prossima ha uno slash)
                        
                        is_next_upper = re.sub(r'[^a-zA-Z]', '', next_line).isupper()
                        is_page_num = re.match(r'^\d+\.$', next_line) # Evita numeri pagina isolati
                        
                        # Preposizioni che indicano che la frase non è finita
                        connector_pattern = r'(DA|DI|DEL|DELLA|SU|CON|\-|–|\/)$'
                        ends_with_connector = re.search(connector_pattern, raw_content, re.IGNORECASE)
                        
                        # Se la prossima ha uno slash (es. LETTO/INGRESSO) è quasi sicuramente un ambiente
                        has_slash = "/" in next_line
                        
                        if is_next_upper and not is_page_num:
                            if ends_with_connector or has_slash:
                                # UNISCIAMO LE RIGHE!
                                raw_content += " " + next_line
                                # Saltiamo la riga successiva nel prossimo giro perché l'abbiamo appena usata
                                i += 1

                    # --- 4. ESTRAZIONE DATI ---
                    full_text = raw_content
                    ie = ""
                    gn = ""
                    
                    # Trova I/E
                    match_ie = re.search(r'\b(EST-INT|INT-EST|EST/INT|INT/EST|I/E|E/I|EST|INT|EXT)\b', full_text, re.IGNORECASE)
                    if match_ie:
                        ie = match_ie.group(0).upper()
                        full_text = full_text.replace(ie, "", 1).strip()
                    
                    # Trova G/N
                    match_gn = re.search(r'\b(GIORNO|NOTTE|ALBA|TRAMONTO|SERA|POMERIGGIO)\b', full_text, re.IGNORECASE)
                    if match_gn:
                        gn = match_gn.group(0).upper()
                        full_text = full_text.replace(gn, "", 1).strip()
                    
                    # Pulizia finale e Split
                    full_text = re.sub(r'^[\s\/\-\–\.]+', '', full_text).strip()
                    parts = re.split(r'[\-\–]', full_text)
                    parts = [p.strip() for p in parts if p.strip()]
                    
                    ambiente = parts[0] if len(parts) > 0 else ""
                    sottoambiente = " - ".join(parts[1:]) if len(parts) > 1 else ""

                    if len(ambiente) < 120: 
                        data.append({
                            "Scena": scene_num,
                            "I/E": ie,
                            "G/N": gn,
                            "Ambiente": ambiente,
                            "Sottoambiente": sottoambiente,
                            "Note": ""
                        })
                
                # Avanzamento indice ciclo while
                i += 1

    return pd.DataFrame(data)

if uploaded_file is not None:
    with st.spinner('Analisi in corso...'):
        try:
            df = parse_screenplay(uploaded_file)
            
            if not df.empty:
                st.success(f"Trovate {len(df)} scene!")
                edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
                csv = edited_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Scarica CSV", csv, 'spoglio_sceneggiatura.csv', 'text/csv')
            else:
                st.warning("Nessuna scena trovata.")

        except Exception as e:
            st.error(f"Errore: {e}")
