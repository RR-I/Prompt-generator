import streamlit as st
from openai import OpenAI
import pandas as pd
import json, re
import time

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
if 'authenticated' not in st.session_state: st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 Accesso Richiesto")
    st.markdown("Inserisci la password per accedere all'applicazione.")
    
    with st.form("login_form"):
        password_input = st.text_input("Password:", type="password")
        login_button = st.form_submit_button("🔓 Accedi", use_container_width=True)
        
        if login_button:
            try:
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

# =======================
# Funzione lato Python per mapping categorie accorpate
def accorpa_categoria(cat):
    cat = (cat or "").lower()
    if any(
        term in cat
        for term in [
            "top", "scelte consigliate", "orientamento", "consigli"
        ]
    ):
        return "Scelte consigliate / orientamento"
    if "branding" in cat or "identità" in cat:
        return "Branding / Identità"
    if (
        "parole-chiave" in cat
        or "parola chiave" in cat
        or "richieste tipiche" in cat
        or "parole" in cat
        or "keyword" in cat
    ):
        return "Parole-chiave / Richieste tipiche"
    if (
        "servizi" in cat
        or "casi d'uso" in cat
        or "specifici" in cat
        or "caso d'uso" in cat
    ):
        return "Servizi specifici / Casi d'uso"
    if "pain" in cat or "punto dolore" in cat or "domande utente" in cat:
        return "Pain points / Domande utente"
    # fallback 
    return cat.title() if cat else cat

# ==========================================================
# 🧠 FUNZIONE DI GENERAZIONE PROMPT (VERSIONE ROBUSTA)
# ==========================================================
def genera_prompt(settore, servizi, numero_prompt=20, area=None, target=None, tono=None, modello="gpt-4o"):
    """
    Genera prompt con batch ottimizzati e retry intelligente.
    (output = pd.DataFrame, con colonna 'categoria' già processata)
    """
    system_msg = """
Genera un elenco di query sintetiche (prompt) per testare il posizionamento di un'azienda nel suo settore tramite LLM.
NON includere mai nomi di brand o aziende specifiche.
Suddividi le query in 5 categorie (distribuisci equamente):
1. Branding / Identità
2. Scelte consigliate / orientamento
3. Parole-chiave / Richieste tipiche
4. Servizi specifici / Casi d'uso
5. Pain points / Domande utente

Ogni prompt deve:
- Riflettere il contesto reale di ricerca di un utente
- Avere linguaggio naturale, realistico e coerente con il tono indicato
- Essere pertinente all'area geografica o target, se specificati
- Coprire vari intenti: informazionali, valutativi e transazionali

CRITICAMENTE IMPORTANTE: Devi generare ESATTAMENTE il numero di prompt richiesto.
Se richiesti 50 prompt, genera 50 prompt. Non 48, non 52, ma ESATTAMENTE 50.
Conta bene prima di rispondere.

Restituisci SOLO un array JSON valido con chiavi: "categoria" e "testo".
Non aggiungere testo prima o dopo il JSON.
Non usare markdown code blocks.
"""

    all_prompts = []

    # Dimensione batch dinamica basata sul numero totale
    if numero_prompt <= 30:
        batch_size = numero_prompt
        num_batches = 1
    elif numero_prompt <= 100:
        batch_size = 25
        num_batches = (numero_prompt + batch_size - 1) // batch_size
    else:
        batch_size = 30
        num_batches = (numero_prompt + batch_size - 1) // batch_size

    progress_bar = st.progress(0)
    status_text = st.empty()

    for i in range(num_batches):
        prompts_da_generare = min(batch_size, numero_prompt - len(all_prompts))
        esempio_precedenti = ""
        if all_prompts:
            ultimi = all_prompts[-10:]
            esempio_precedenti = f"\n\n⚠️ Esempi di prompt GIÀ generati (NON ripetere concetti simili):\n"
            for p in ultimi:
                esempio_precedenti += f"- {p['testo']}\n"

        user_msg = f"""
Genera {prompts_da_generare} prompt per:

📋 Settore: {settore}
🔧 Servizi/Prodotti: {servizi}
📍 Area geografica: {area or "Non specificata - considera contesto generale"}
🎯 Target: {target or "Generico - privati e aziende"}
💬 Tono: {tono or "Naturale e professionale"}
{esempio_precedenti}

REGOLE FERREE:
1. Genera ESATTAMENTE {prompts_da_generare} prompt (conta prima di rispondere!)
2. Varia gli intenti: informativi, comparativi, transazionali
3. Distribuisci equamente tra le 5 categorie
4. Usa linguaggio naturale (come cercherebbe un vero utente)
5. NON ripetere concetti già espressi sopra
6. Sii creativo e specifico per il settore

Formato di output richiesto:
[
  {{"categoria": "nome categoria", "testo": "testo del prompt"}},
  ...
]

Rispondi SOLO con l'array JSON, nient'altro.
"""

        status_text.text(f"๋࣭ ⭑⚝ Batch {i+1}/{num_batches} | Generati: {len(all_prompts)}/{numero_prompt} prompt")

        max_retry = 3
        batch_success = False
        for tentativo in range(max_retry):
            try:
                response = client.chat.completions.create(
                    model=modello,
                    temperature=0.9,
                    max_tokens=4096,
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_msg}
                    ]
                )
                text_output = response.choices[0].message.content.strip()
                # Pulizia output (rimuovi eventuale markup)
                text_output = re.sub(r'^```json\s*', '', text_output)
                text_output = re.sub(r'^```\s*', '', text_output)
                text_output = re.sub(r'\s*```$', '', text_output)
                text_output = text_output.strip()
                json_match = re.search(r'\[.*\]', text_output, re.DOTALL)
                if not json_match:
                    raise ValueError("Nessun array JSON trovato nell'output")

                prompts_batch = json.loads(json_match.group(0))
                # Validazione struttura
                prompts_validi = []
                for p in prompts_batch:
                    if isinstance(p, dict) and 'categoria' in p and 'testo' in p:
                        testo = p['testo'].strip()
                        if testo and len(testo) > 10:  # Almeno 10 caratteri
                            prompts_validi.append(p)

                if not prompts_validi:
                    raise ValueError("Nessun prompt valido nel batch")
                # Filtra duplicati (case-insensitive e normalizzato)
                testi_esistenti = {
                    p['testo'].lower().strip().replace("  ", " ") 
                    for p in all_prompts
                }
                nuovi_prompts = []
                for p in prompts_validi:
                    testo_normalizzato = p['testo'].lower().strip().replace("  ", " ")
                    if testo_normalizzato not in testi_esistenti:
                        nuovi_prompts.append(p)
                        testi_esistenti.add(testo_normalizzato)
                all_prompts.extend(nuovi_prompts)
                # Feedback visivo (aggiorna nello stesso container)
                if len(nuovi_prompts) == prompts_da_generare:
                    status_text.success(f"✅ Batch {i+1}/{num_batches}: generati {len(nuovi_prompts)}/{prompts_da_generare} prompt | Totale: {len(all_prompts)}/{numero_prompt}")
                elif len(nuovi_prompts) > 0:
                    status_text.info(f"ℹ️ Batch {i+1}/{num_batches}: generati {len(nuovi_prompts)}/{prompts_da_generare} prompt (alcuni duplicati) | Totale: {len(all_prompts)}/{numero_prompt}")
                else:
                    status_text.warning(f"⚠️ Batch {i+1}/{num_batches}: tutti duplicati, riprovo...")
                    continue

                batch_success = True
                break  # Successo, esci dal retry loop

            except json.JSONDecodeError as e:
                if tentativo < max_retry - 1:
                    status_text.warning(f"⚠️ Batch {i+1} - Errore JSON (tentativo {tentativo+1}/{max_retry}), riprovo...")
                    time.sleep(1)
                else:
                    status_text.error(f"❌ Batch {i+1} fallito dopo {max_retry} tentativi")

            except Exception as e:
                if tentativo < max_retry - 1:
                    status_text.warning(f"⚠️ Batch {i+1} - Tentativo {tentativo+1}/{max_retry}: {str(e)[:100]}")
                    time.sleep(1)
                else:
                    status_text.error(f"❌ Batch {i+1} fallito: {str(e)[:100]}")

        if not batch_success:
            status_text.warning(f"⚠️ Batch {i+1} saltato, continuo...")

        progress_bar.progress(min((i + 1) / num_batches, 1.0))
        if len(all_prompts) >= numero_prompt:
            break

    progress_bar.empty()
    status_text.empty()
    # Taglia al numero esatto
    all_prompts = all_prompts[:numero_prompt]
    percentuale = (len(all_prompts) / numero_prompt * 100) if numero_prompt > 0 else 0

    if len(all_prompts) == numero_prompt:
        st.success(f"🎉 Completato! Generati esattamente {numero_prompt} prompt")
    elif percentuale >= 90:
        st.info(f"✅ Generati {len(all_prompts)}/{numero_prompt} prompt ({percentuale:.0f}%)")
    elif percentuale >= 70:
        st.warning(f"⚠️ Generati {len(all_prompts)}/{numero_prompt} prompt ({percentuale:.0f}%). Considera di rigenerare per ottenere il numero completo.")
    else:
        st.error(f"❌ Generati solo {len(all_prompts)}/{numero_prompt} prompt ({percentuale:.0f}%). Riprova o riduci il numero richiesto.")

    if all_prompts:
        dfp = pd.DataFrame(all_prompts)
        # Accorpa categorie ambigue in cluster categorie fissate a 5 gruppi
        dfp['categoria'] = dfp['categoria'].apply(accorpa_categoria)
        return dfp
    else:
        return None

# ==========================================================
# 🧩 FORM DI INPUT
# ==========================================================
with st.sidebar:
    with st.form("prompt_form"):
        st.subheader("📋 Parametri di generazione")
        settore = st.text_input("🏭 Settore aziendale", placeholder="es. edilizia sostenibile, ristorazione, software SaaS...")
        servizi = st.text_input("🧰 Servizi o prodotti offerti", placeholder="es. progettazione, assistenza, consulenza, formazione...")
        area    = st.text_input("📍 Area geografica (opzionale)", placeholder="es. Italia, Europa, Milano...")
        target  = st.text_input("🎯 Target di riferimento (opzionale)", placeholder="es. aziende, privati, enti pubblici...")
        tono    = st.text_input("💬 Tono e linguaggio desiderato (opzionale)", placeholder="es. professionale, amichevole, tecnico...")
        numero_prompt = st.slider("📈 Numero di prompt da generare", 10, 200, 50, step=10)
        modello = st.selectbox("🤖 Modello LLM da usare", [
            "gpt-4", "gpt-4o", "gpt-4o-mini", "gpt-4-turbo","gpt-4-turbo-preview", "gpt-4.1", "gpt-5.1-chat-latest"
        ], index=1)
        submit = st.form_submit_button("🚀 Genera Prompt", use_container_width=True)

# ==========================================================
# ⚙️ GENERAZIONE E RISULTATI
# ==========================================================
if submit:
    if not settore or not servizi:
        st.warning("⚠️ Compila almeno i campi 'Settore' e 'Servizi' per generare i prompt.")
    else:
        with st.spinner("🔄 Generazione in corso..."):
            start_time = time.time()
            df_prompts = genera_prompt(
                settore, servizi, numero_prompt, area, target, tono, modello
            )
            elapsed_time = time.time() - start_time            
        if df_prompts is not None and not df_prompts.empty:
            st.session_state['df_prompts'] = df_prompts
            st.session_state['elapsed_time'] = elapsed_time
            st.session_state['settore'] = settore

# ==========================================================
# 📊 VISUALIZZAZIONE RISULTATI (CON CACHE)
# ==========================================================
if 'df_prompts' in st.session_state:
    df_prompts = st.session_state['df_prompts']
    elapsed_time = st.session_state['elapsed_time']
    settore = st.session_state.get('settore', 'output')

    st.success(f"✅ Processo completato in {elapsed_time:.1f} secondi")
    st.subheader("📊 Riepilogo")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🎯 Prompt Generati", len(df_prompts))
    with col2:
        st.metric("📁 Categorie", df_prompts['categoria'].nunique())
    with col3:
        st.metric("⏱️ Tempo", f"{elapsed_time:.1f}s")

    st.subheader("📈 Distribuzione per Categoria")
    tutte_categorie_fisse = [
        "Branding / Identità",
        "Scelte consigliate / orientamento",
        "Parole-chiave / Richieste tipiche",
        "Servizi specifici / Casi d'uso",
        "Pain points / Domande utente"
    ]
    # Forza tutte in ordine e anche se mancanti zero ricorsività (Cart Type)
    cat_count = {cat:0 for cat in tutte_categorie_fisse}
    for c,v in df_prompts['categoria'].value_counts().items():
        cat_count[c] = v
    st.bar_chart(pd.Series(cat_count))
    with st.expander("📋 Dettagli per categoria", expanded=False):
        df_prompts['lunghezza'] = df_prompts['testo'].str.len()
        summary = df_prompts.groupby('categoria').agg({
            'testo': 'count', 'lunghezza': 'mean'
        }).reindex(tutte_categorie_fisse).fillna(0).round(0)
        summary.columns = ['Numero Prompt', 'Lunghezza Media']
        st.dataframe(summary, use_container_width=True)

    st.subheader("📋 Esplora i Prompt")
    tutte_categorie = ['Tutte'] + tutte_categorie_fisse
    categoria_filtro = st.selectbox(
        "Filtra per categoria:",
        tutte_categorie,
        key="filtro_cat"
    )
    if categoria_filtro == 'Tutte':
        df_filtered = df_prompts
    else:
        df_filtered = df_prompts[df_prompts['categoria'] == categoria_filtro]
    st.info(f"📊 Visualizzati {len(df_filtered)} prompt")
    st.dataframe(
        df_filtered[['categoria', 'testo']],
        use_container_width=True,
        height=400,
        column_config={ "categoria": "Categoria", "testo": "Prompt" },
        hide_index=True
    )

    st.subheader("💾 Scarica Risultati")
    csv = df_prompts[['categoria', 'testo']].to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Scarica CSV",
        data=csv,
        file_name=f"prompt_{settore.replace(' ', '_')}_{len(df_prompts)}.csv",
        mime="text/csv", use_container_width=True
    )
    if st.button("🔄 Genera Nuovi Prompt", type="secondary", use_container_width=True):
        del st.session_state['df_prompts']
        del st.session_state['elapsed_time']
        st.rerun()

# ==========================================================
# 📊 FOOTER
# ==========================================================
st.divider()
st.caption("🔒 Applicazione protetta da password. La chiave API è configurata in modo sicuro nei secrets.")
st.caption("💡 Tip: I risultati rimangono visibili finché non generi nuovi prompt!")
