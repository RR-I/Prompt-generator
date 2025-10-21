import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import pandas as pd
import json, re

# ==========================================================
# 🎨 CONFIGURAZIONE DELL'APP
# ==========================================================
st.set_page_config(
    page_title="Prompt Generator Universale LLM",
    page_icon="🧠",
    layout="centered"
)

st.title("🧠 Prompt Generator")
st.text("by Cristiano Caggiula-Ranking Road Italia")
st.markdown("""
Genera **prompt intelligenti e realistici** per test di posizionamento nei motori LLM (come GPT-4o),
adatti a **qualsiasi azienda o settore**.  
Puoi personalizzare settore, servizi, target, area geografica e tono comunicativo.
""")

# ==========================================================
# 🔐 INIZIALIZZAZIONE SESSION STATE
# ==========================================================
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""
if 'key_loaded_from_storage' not in st.session_state:
    st.session_state.key_loaded_from_storage = False

# ==========================================================
# 🔐 COMPONENTE PER CARICARE DA LOCALSTORAGE
# ==========================================================

def load_from_localstorage():
    """Carica la chiave dal localStorage solo una volta"""
    
    html_code = """
    <script>
        const savedKey = localStorage.getItem('openai_api_key');
        if (savedKey) {
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: savedKey
            }, '*');
        }
    </script>
    """
    
    return components.html(html_code, height=0)

# ==========================================================
# 🔐 COMPONENTE PER SALVARE/RIMUOVERE
# ==========================================================

def api_key_input_component():
    """Componente per inserire e gestire la chiave API"""
    
    current_key = st.session_state.api_key
    
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * {{
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }}
            
            body {{
                font-family: "Source Sans Pro", sans-serif;
                padding: 0.5rem;
            }}
            
            .input-group {{
                margin-bottom: 1rem;
            }}
            
            label {{
                display: block;
                margin-bottom: 0.5rem;
                font-weight: 500;
                color: #262730;
                font-size: 14px;
            }}
            
            input[type="password"] {{
                width: 100%;
                padding: 0.5rem;
                border: 1px solid #d3d3d3;
                border-radius: 4px;
                font-size: 14px;
            }}
            
            input[type="password"]:focus {{
                outline: none;
                border-color: #ff4b4b;
            }}
            
            .button-group {{
                display: flex;
                gap: 0.5rem;
                margin-top: 1rem;
            }}
            
            button {{
                flex: 1;
                padding: 0.5rem 1rem;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s;
            }}
            
            .btn-save {{
                background: #4CAF50;
                color: white;
            }}
            
            .btn-save:hover {{
                background: #45a049;
            }}
            
            .btn-remove {{
                background: #f44336;
                color: white;
            }}
            
            .btn-remove:hover {{
                background: #da190b;
            }}
            
            .status {{
                margin-top: 1rem;
                padding: 0.75rem;
                border-radius: 4px;
                font-size: 14px;
                display: none;
            }}
            
            .status.success {{
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }}
            
            .status.error {{
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }}
            
            .status.info {{
                background: #d1ecf1;
                color: #0c5460;
                border: 1px solid #bee5eb;
            }}
        </style>
    </head>
    <body>
        <div class="input-group">
            <label for="apiKeyInput">🔑 Chiave API OpenAI</label>
            <input type="password" id="apiKeyInput" placeholder="sk-proj-..." value="{current_key}">
        </div>
        
        <div class="button-group">
            <button class="btn-save" onclick="saveKey()">💾 Salva nel browser</button>
            <button class="btn-remove" onclick="removeKey()">🗑️ Rimuovi</button>
        </div>
        
        <div id="status" class="status"></div>
        
        <script>
            function saveKey() {{
                const keyInput = document.getElementById('apiKeyInput');
                const key = keyInput.value.trim();
                
                if (!key) {{
                    showStatus('⚠️ Inserisci una chiave valida', 'error');
                    return;
                }}
                
                if (!key.startsWith('sk-')) {{
                    showStatus('⚠️ La chiave deve iniziare con "sk-"', 'error');
                    return;
                }}
                
                try {{
                    localStorage.setItem('openai_api_key', key);
                    sendToStreamlit('SAVE:' + key);
                    showStatus('✅ Chiave salvata con successo!', 'success');
                }} catch (error) {{
                    showStatus('❌ Errore: ' + error.message, 'error');
                }}
            }}
            
            function removeKey() {{
                try {{
                    localStorage.removeItem('openai_api_key');
                    document.getElementById('apiKeyInput').value = '';
                    sendToStreamlit('REMOVE');
                    showStatus('🗑️ Chiave rimossa', 'info');
                }} catch (error) {{
                    showStatus('❌ Errore: ' + error.message, 'error');
                }}
            }}
            
            function sendToStreamlit(value) {{
                window.parent.postMessage({{
                    type: 'streamlit:setComponentValue',
                    value: value
                }}, '*');
            }}
            
            function showStatus(message, type) {{
                const statusDiv = document.getElementById('status');
                statusDiv.textContent = message;
                statusDiv.className = 'status ' + type;
                statusDiv.style.display = 'block';
                
                setTimeout(() => {{
                    statusDiv.style.display = 'none';
                }}, 4000);
            }}
        </script>
    </body>
    </html>
    """
    
    return components.html(html_code, height=220)

# ==========================================================
# 🔑 CARICA CHIAVE DA LOCALSTORAGE (SOLO AL PRIMO AVVIO)
# ==========================================================

if not st.session_state.key_loaded_from_storage:
    stored_key = load_from_localstorage()
    if stored_key and isinstance(stored_key, str) and stored_key.startswith('sk-'):
        st.session_state.api_key = stored_key
        st.session_state.key_loaded_from_storage = True
        st.rerun()

# ==========================================================
# 🔑 GESTIONE CHIAVE API
# ==========================================================

with st.expander("🔐 Configurazione API OpenAI", expanded=not st.session_state.api_key):
    
    st.warning("""
    ⚠️ **Attenzione alla sicurezza**: 
    La chiave API verrà salvata nel browser locale in formato non criptato. 
    Usa questa funzione solo su computer personali e mai su dispositivi condivisi.
    """)
    
    # Componente per gestire la chiave
    action = api_key_input_component()
    
    # Gestisci le azioni
    if action:
        if isinstance(action, str):
            if action.startswith('SAVE:'):
                new_key = action.replace('SAVE:', '')
                if new_key and new_key.startswith('sk-'):
                    st.session_state.api_key = new_key
                    st.rerun()
            elif action == 'REMOVE':
                st.session_state.api_key = ""
                st.rerun()
    
    # Mostra stato
    if st.session_state.api_key:
        st.success(f"✅ Chiave API configurata: {st.session_state.api_key[:12]}...")

# Recupera la chiave API
api_key = st.session_state.api_key

# Blocca l'app se non c'è la chiave
if not api_key:
    st.info("👆 Inserisci e salva la chiave API OpenAI nell'expander sopra per continuare.")
    st.stop()

# Inizializza il client OpenAI
try:
    client = OpenAI(api_key=api_key)
except Exception as e:
    st.error(f"❌ Errore nella configurazione di OpenAI: {e}")
    st.info("Verifica che la chiave API sia corretta e riprova.")
    st.stop()

# ==========================================================
# 🧠 FUNZIONE DI GENERAZIONE PROMPT
# ==========================================================
def genera_prompt(settore, servizi, numero_prompt=20, area=None, target=None, tono=None, modello="gpt-4o"):
    """
    Genera prompt test per analisi semantiche LLM. Adatta il linguaggio in base al settore e ai parametri forniti.
    """
    system_msg = """
    Genera un elenco di query sintetiche (prompt) per testare il posizionamento di un'azienda nel suo settore tramite LLM.
    NON includere mai nomi di brand o aziende specifiche.
    Suddividi le query in 6 categorie:
    1. Branding / Identità
    2. Top / Scelte consigliate
    3. Consigli / Orientamento
    4. Parole-chiave / Richieste tipiche
    5. Servizi specifici / Casi d'uso
    6. Pain points / Domande utente

    Ogni prompt deve:
    - Riflettere il contesto reale di ricerca di un utente
    - Avere linguaggio naturale, realistico e coerente con il tono indicato
    - Essere pertinente all'area geografica o target, se specificati
    - Coprire vari intenti: informazionali, valutativi e transazionali
    Restituisci il risultato in formato JSON con chiavi: "categoria" e "testo".
    """

    user_msg = f"""
    Settore: {settore}
    Servizi: {servizi}
    Numero totale di prompt: {numero_prompt}
    Area geografica: {area or "Nessuna specifica"}
    Target: {target or "Generico"}
    Tono linguistico: {tono or "Neutro e naturale"}
    """

    try:
        response = client.chat.completions.create(
            model=modello,
            temperature=0.9,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ]
        )
        text_output = response.choices[0].message.content

        # Parsing del JSON dall'output
        json_match = re.search(r"\[.*\]", text_output, re.S)
        if not json_match:
            raise ValueError("Output non in formato JSON")

        prompts = json.loads(json_match.group(0))
        return pd.DataFrame(prompts)

    except Exception as e:
        st.error(f"❌ Errore nella generazione o parsing del risultato: {e}")
        return None

# ==========================================================
# 🧩 FORM DI INPUT
# ==========================================================
with st.form("prompt_form"):
    st.subheader("📋 Parametri di generazione")
    
    settore = st.text_input(
        "🏭 Settore aziendale", 
        placeholder="es. edilizia sostenibile, ristorazione, software SaaS..."
    )
    
    servizi = st.text_input(
        "🧰 Servizi o prodotti offerti", 
        placeholder="es. progettazione, assistenza, consulenza, formazione..."
    )
    
    area = st.text_input(
        "📍 Area geografica (opzionale)", 
        placeholder="es. Italia, Europa, Milano, Roma..."
    )
    
    target = st.text_input(
        "🎯 Target di riferimento (opzionale)", 
        placeholder="es. aziende, privati, enti pubblici..."
    )
    
    tono = st.text_input(
        "💬 Tono e linguaggio desiderato (opzionale)", 
        placeholder="es. professionale, amichevole, tecnico, persuasivo..."
    )
    
    numero_prompt = st.slider(
        "📈 Numero di prompt da generare", 
        10, 200, 50, step=10
    )
    
    modello = st.selectbox(
        "🤖 Modello LLM da usare", 
        ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
    )
    
    submit = st.form_submit_button("🚀 Genera Prompt", use_container_width=True)

# ==========================================================
# ⚙️ GENERAZIONE E RISULTATI
# ==========================================================
if submit:
    if not settore or not servizi:
        st.warning("⚠️ Compila almeno i campi 'Settore' e 'Servizi' per generare i prompt.")
    else:
        with st.spinner("🪄 Generazione in corso..."):
            df_prompts = genera_prompt(
                settore, 
                servizi, 
                numero_prompt, 
                area, 
                target, 
                tono, 
                modello
            )

        if df_prompts is not None and not df_prompts.empty:
            st.success(f"✅ Generati {len(df_prompts)} prompt per il settore: **{settore}**")
            
            # Mostra tabella
            st.dataframe(df_prompts, use_container_width=True)

            # Download CSV
            csv = df_prompts.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="💾 Scarica i prompt in CSV",
                data=csv,
                file_name=f"prompt_{settore.replace(' ', '_')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.error("❌ Nessun prompt generato. Prova a riformulare i parametri.")

# ==========================================================
# 📊 FOOTER
# ==========================================================
st.divider()
st.caption("🔒 La tua chiave API viene salvata solo nel browser locale (localStorage) e non viene mai trasmessa a terzi.")
