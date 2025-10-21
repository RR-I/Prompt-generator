import streamlit as st
from streamlit_js_eval import streamlit_js_eval
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
# 🔑 INIZIALIZZAZIONE SESSION STATE
# ==========================================================
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""
if 'key_loaded' not in st.session_state:
    st.session_state.key_loaded = False

# ==========================================================
# 🔐 GESTIONE CHIAVE API CON LOCALSTORAGE
# ==========================================================
with st.expander("🔐 Configurazione API OpenAI", expanded=not st.session_state.api_key):
    
    # Disclaimer sicurezza
    st.warning("""
    ⚠️ **Attenzione alla sicurezza**: 
    La chiave API verrà salvata nel browser locale in formato non criptato. 
    Usa questa funzione solo su computer personali e mai su dispositivi condivisi.
    """)
    
    # Prova a caricare dal localStorage (solo al primo caricamento)
    if not st.session_state.key_loaded:
        try:
            stored_key = streamlit_js_eval(
                js_expressions="localStorage.getItem('openai_api_key')",
                key='get_api_key'
            )
            if stored_key and stored_key != "null":
                st.session_state.api_key = stored_key
                st.session_state.key_loaded = True
        except:
            pass
    
    # Input per la chiave API
    api_key_input = st.text_input(
        "Inserisci la tua chiave API OpenAI:", 
        value=st.session_state.api_key,
        type="password",
        help="La chiave verrà salvata nel tuo browser locale"
    )
    
    # Pulsanti di gestione
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 Salva nel browser", use_container_width=True):
            if api_key_input:
                st.session_state.api_key = api_key_input
                st.session_state.key_loaded = True
                # Salva nel localStorage
                try:
                    streamlit_js_eval(
                        js_expressions=f"localStorage.setItem('openai_api_key', '{api_key_input}')",
                        key=f'save_api_key_{hash(api_key_input)}'
                    )
                    st.success("✅ Chiave salvata nel browser!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore nel salvataggio: {e}")
            else:
                st.warning("Inserisci una chiave valida")
    
    with col2:
        if st.button("🗑️ Rimuovi dal browser", use_container_width=True):
            st.session_state.api_key = ""
            st.session_state.key_loaded = False
            try:
                streamlit_js_eval(
                    js_expressions="localStorage.removeItem('openai_api_key')",
                    key='remove_api_key'
                )
                st.info("Chiave rimossa dal browser")
                st.rerun()
            except Exception as e:
                st.error(f"Errore nella rimozione: {e}")
    
    # Mostra stato
    if st.session_state.api_key:
        st.info(f"✅ Chiave API configurata: {st.session_state.api_key[:10]}...")

# Recupera la chiave API
api_key = st.session_state.api_key

# Blocca l'app se non c'è la chiave
if not api_key:
    st.warning("⚠️ Per continuare, inserisci e salva una chiave API OpenAI valida.")
    st.stop()

# Inizializza il client OpenAI
try:
    client = OpenAI(api_key=api_key)
except Exception as e:
    st.error(f"❌ Errore nella configurazione di OpenAI: {e}")
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
st.caption("🔒 La tua chiave API viene salvata solo nel browser locale e non viene mai trasmessa a terzi.")
