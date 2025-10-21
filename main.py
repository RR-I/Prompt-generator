import streamlit as st
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

# ==========================================================
# 🔐 SISTEMA DI AUTENTICAZIONE
# ==========================================================

# Inizializza session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# Se non autenticato, mostra form di login
if not st.session_state.authenticated:
    st.title("🔐 Accesso Richiesto")
    st.markdown("Inserisci la password per accedere all'applicazione.")
    
    with st.form("login_form"):
        password_input = st.text_input("Password:", type="password")
        login_button = st.form_submit_button("🔓 Accedi", use_container_width=True)
        
        if login_button:
            try:
                # Verifica la password dai secrets
                correct_password = st.secrets["APP_PASSWORD"]
                
                if password_input == correct_password:
                    st.session_state.authenticated = True
                    st.success("✅ Accesso consentito!")
                    st.rerun()
                else:
                    st.error("❌ Password errata. Riprova.")
            except Exception as e:
                st.error(f"❌ Errore nella configurazione dei secrets: {e}")
                st.info("Assicurati di aver configurato APP_PASSWORD nei secrets.")
    
    st.stop()

# ==========================================================
# 📱 HEADER E LOGOUT
# ==========================================================
col1, col2 = st.columns([4, 1])
with col1:
    st.title("🧠 Prompt Generator")
    st.text("by Cristiano Caggiula-Ranking Road Italia")
with col2:
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

st.markdown("""
Genera **prompt intelligenti e realistici** per test di posizionamento nei motori LLM (come GPT-4o),
adatti a **qualsiasi azienda o settore**.  
Puoi personalizzare settore, servizi, target, area geografica e tono comunicativo.
""")

# ==========================================================
# 🔑 CONFIGURAZIONE OPENAI
# ==========================================================

try:
    api_key = st.secrets["OPENAI_API_KEY"]
    client = OpenAI(api_key=api_key)
except Exception as e:
    st.error(f"❌ Errore nella configurazione di OpenAI: {e}")
    st.info("Assicurati di aver configurato OPENAI_API_KEY nei secrets.")
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
st.caption("🔒 Applicazione protetta da password. La chiave API è configurata in modo sicuro nei secrets.")
