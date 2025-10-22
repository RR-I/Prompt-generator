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
# 🧠 FUNZIONE DI GENERAZIONE PROMPT (VERSIONE ROBUSTA)
# ==========================================================
def genera_prompt(settore, servizi, numero_prompt=20, area=None, target=None, tono=None, modello="gpt-4o"):
    """
    Genera prompt con batch ottimizzati e retry intelligente.
    Versione robusta con validazione e gestione errori avanzata.
    """
    system_msg = """
Genera un elenco di query sintetiche (prompt) per testare il posizionamento di un'azienda nel suo settore tramite LLM.
NON includere mai nomi di brand o aziende specifiche.
Suddividi le query in 6 categorie (distribuisci equamente):
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
        
        # Stringhe di esempio di prompt già generati (solo gli ultimi 10 per risparmiare token)
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
3. Distribuisci equamente tra le 6 categorie
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
                
                # Pulizia output (rimuovi markdown se presente)
                text_output = re.sub(r'^```json\s*', '', text_output)
                text_output = re.sub(r'^```\s*', '', text_output)
                text_output = re.sub(r'\s*```$', '', text_output)
                text_output = text_output.strip()
                
                # Parsing del JSON
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
        
        # Se il batch non è riuscito dopo tutti i retry, continua comunque

        if not batch_success:
            status_text.warning(f"⚠️ Batch {i+1} saltato, continuo...")
        
        progress_bar.progress(min((i + 1) / num_batches, 1.0))
        
        # Se abbiamo raggiunto o superato il target, esci
        if len(all_prompts) >= numero_prompt:
            break
    
    progress_bar.empty()
    status_text.empty()
    
    # Taglia al numero esatto
    all_prompts = all_prompts[:numero_prompt]
    
    # Messaggio finale dettagliato
    percentuale = (len(all_prompts) / numero_prompt * 100) if numero_prompt > 0 else 0
    
    if len(all_prompts) == numero_prompt:
        st.success(f"🎉 Completato! Generati esattamente {numero_prompt} prompt")
    elif percentuale >= 90:
        st.info(f"✅ Generati {len(all_prompts)}/{numero_prompt} prompt ({percentuale:.0f}%)")
    elif percentuale >= 70:
        st.warning(f"⚠️ Generati {len(all_prompts)}/{numero_prompt} prompt ({percentuale:.0f}%). Considera di rigenerare per ottenere il numero completo.")
    else:
        st.error(f"❌ Generati solo {len(all_prompts)}/{numero_prompt} prompt ({percentuale:.0f}%). Riprova o riduci il numero richiesto.")
    
    return pd.DataFrame(all_prompts) if all_prompts else None

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
        ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]
    )
    
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
                settore, 
                servizi, 
                numero_prompt, 
                area, 
                target, 
                tono, 
                modello
            )
            
            elapsed_time = time.time() - start_time

        if df_prompts is not None and not df_prompts.empty:
            st.success(f"✅ Processo completato in {elapsed_time:.1f} secondi")
            
            # ==========================================================
            # 📊 STATISTICHE E METRICHE
            # ==========================================================
            st.subheader("📊 Statistiche Generazione")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("🎯 Prompt Generati", len(df_prompts), delta=f"{len(df_prompts)/numero_prompt*100:.0f}%")
            with col2:
                st.metric("📁 Categorie", df_prompts['categoria'].nunique())
            with col3:
                st.metric("⏱️ Tempo", f"{elapsed_time:.1f}s")
            with col4:
                media_lunghezza = df_prompts['testo'].str.len().mean()
                st.metric("📏 Lunghezza Media", f"{media_lunghezza:.0f} char")
            
            # ==========================================================
            # 📈 GRAFICI INTERATTIVI
            # ==========================================================
            st.subheader("📈 Analisi Visuale")
            
            # Calcola statistiche per categoria
            categoria_stats = df_prompts.groupby('categoria').agg({
                'testo': ['count', lambda x: x.str.len().mean()]
            }).round(0)
            categoria_stats.columns = ['count', 'avg_length']
            categoria_stats = categoria_stats.reset_index()
            categoria_stats = categoria_stats.sort_values('count', ascending=True)
            
            # TAB per organizzare i grafici
            tab1, tab2, tab3 = st.tabs(["📊 Distribuzione", "📏 Lunghezza Prompt", "🔤 Word Cloud"])
            
            with tab1:
                # Grafico a barre orizzontali (più leggibile)
                import plotly.express as px
                
                fig_bar = px.bar(
                    categoria_stats,
                    y='categoria',
                    x='count',
                    orientation='h',
                    title='Distribuzione Prompt per Categoria',
                    labels={'count': 'Numero di Prompt', 'categoria': 'Categoria'},
                    color='count',
                    color_continuous_scale='Blues',
                    text='count'
                )
                fig_bar.update_traces(textposition='outside')
                fig_bar.update_layout(
                    showlegend=False,
                    height=400,
                    xaxis_title="Numero di Prompt",
                    yaxis_title="",
                    font=dict(size=12)
                )
                st.plotly_chart(fig_bar, use_container_width=True)
                
                # Grafico a torta
                fig_pie = px.pie(
                    categoria_stats,
                    values='count',
                    names='categoria',
                    title='Percentuale per Categoria',
                    hole=0.4,  # Donut chart
                    color_discrete_sequence=px.colors.sequential.RdBu
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(height=400)
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with tab2:
                # Box plot per lunghezza prompt
                df_prompts['lunghezza'] = df_prompts['testo'].str.len()
                
                fig_box = px.box(
                    df_prompts,
                    x='categoria',
                    y='lunghezza',
                    title='Distribuzione Lunghezza Prompt per Categoria',
                    labels={'lunghezza': 'Lunghezza (caratteri)', 'categoria': 'Categoria'},
                    color='categoria',
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig_box.update_layout(
                    showlegend=False,
                    height=400,
                    xaxis_title="",
                    xaxis_tickangle=-45
                )
                st.plotly_chart(fig_box, use_container_width=True)
                
                # Istogramma generale
                fig_hist = px.histogram(
                    df_prompts,
                    x='lunghezza',
                    nbins=30,
                    title='Distribuzione Generale Lunghezza Prompt',
                    labels={'lunghezza': 'Lunghezza (caratteri)', 'count': 'Frequenza'},
                    color_discrete_sequence=['#636EFA']
                )
                fig_hist.update_layout(
                    showlegend=False,
                    height=350,
                    yaxis_title="Numero di Prompt"
                )
                st.plotly_chart(fig_hist, use_container_width=True)
                
                # Statistiche descrittive
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📏 Minima", f"{df_prompts['lunghezza'].min()} char")
                with col2:
                    st.metric("📏 Media", f"{df_prompts['lunghezza'].mean():.0f} char")
                with col3:
                    st.metric("📏 Massima", f"{df_prompts['lunghezza'].max()} char")
            
            with tab3:
                try:
                    from wordcloud import WordCloud
                    import matplotlib.pyplot as plt
                    
                    # Genera word cloud
                    text = ' '.join(df_prompts['testo'])
                    
                    # Rimuovi stop words comuni italiane
                    stopwords_ita = set([
                        'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'uno', 'una', 'di', 'a', 'da', 
                        'in', 'con', 'su', 'per', 'tra', 'fra', 'come', 'del', 'della', 'dei', 
                        'delle', 'al', 'alla', 'ai', 'alle', 'dal', 'dalla', 'dai', 'dalle', 
                        'nel', 'nella', 'nei', 'nelle', 'sul', 'sulla', 'sui', 'sulle', 'e', 
                        'o', 'ma', 'se', 'che', 'chi', 'cui', 'quale', 'quanto', 'quando', 'dove',
                        'sono', 'è', 'ho', 'hai', 'ha', 'abbiamo', 'avete', 'hanno', 'essere', 'avere'
                    ])
                    
                    wordcloud = WordCloud(
                        width=1600,
                        height=800,
                        background_color='white',
                        colormap='viridis',
                        stopwords=stopwords_ita,
                        collocations=False,
                        relative_scaling=0.5,
                        min_font_size=10
                    ).generate(text)
                    
                    fig_wc, ax = plt.subplots(figsize=(16, 8))
                    ax.imshow(wordcloud, interpolation='bilinear')
                    ax.axis('off')
                    ax.set_title('Word Cloud dei Prompt Generati', fontsize=20, pad=20)
                    st.pyplot(fig_wc)
                    
                    # Top 10 parole più frequenti
                    st.subheader("🔝 Top 10 Parole più Frequenti")
                    word_freq = wordcloud.words_
                    top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
                    
                    df_words = pd.DataFrame(top_words, columns=['Parola', 'Frequenza'])
                    
                    fig_top = px.bar(
                        df_words,
                        x='Frequenza',
                        y='Parola',
                        orientation='h',
                        title='',
                        color='Frequenza',
                        color_continuous_scale='Viridis'
                    )
                    fig_top.update_layout(
                        showlegend=False,
                        height=400,
                        yaxis={'categoryorder': 'total ascending'}
                    )
                    st.plotly_chart(fig_top, use_container_width=True)
                    
                except ImportError:
                    st.info("💡 Per visualizzare il Word Cloud, installa la libreria: `pip install wordcloud matplotlib`")
                    
                    # Alternativa semplice: conteggio parole
                    st.subheader("🔤 Analisi Parole Chiave")
                    all_words = ' '.join(df_prompts['testo']).lower().split()
                    word_counts = pd.Series(all_words).value_counts().head(20)
                    
                    fig_words = px.bar(
                        x=word_counts.values,
                        y=word_counts.index,
                        orientation='h',
                        title='Top 20 Parole più Frequenti',
                        labels={'x': 'Frequenza', 'y': 'Parola'}
                    )
                    fig_words.update_layout(height=500, yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig_words, use_container_width=True)
            
            # ==========================================================
            # 📋 TABELLA DATI
            # ==========================================================
            st.subheader("📋 Prompt Generati")
            
            # Aggiungi filtro per categoria
            col_filter1, col_filter2 = st.columns(2)
            with col_filter1:
                categorie_selezionate = st.multiselect(
                    "Filtra per categoria:",
                    options=df_prompts['categoria'].unique(),
                    default=df_prompts['categoria'].unique()
                )
            with col_filter2:
                min_length = st.slider(
                    "Lunghezza minima caratteri:",
                    0, int(df_prompts['lunghezza'].max()),
                    0
                )
            
            # Applica filtri
            df_filtered = df_prompts[
                (df_prompts['categoria'].isin(categorie_selezionate)) & 
                (df_prompts['lunghezza'] >= min_length)
            ]
            
            st.info(f"📊 Visualizzati {len(df_filtered)} di {len(df_prompts)} prompt")
            
            # Mostra tabella con lunghezza
            df_display = df_filtered[['categoria', 'testo', 'lunghezza']].copy()
            st.dataframe(
                df_display,
                use_container_width=True,
                height=400,
                column_config={
                    "categoria": st.column_config.TextColumn("Categoria", width="medium"),
                    "testo": st.column_config.TextColumn("Prompt", width="large"),
                    "lunghezza": st.column_config.NumberColumn("Caratteri", width="small")
                }
            )

            # ==========================================================
            # 💾 DOWNLOAD
            # ==========================================================
            st.subheader("💾 Download Risultati")
            
            col_dl1, col_dl2 = st.columns(2)
            
            with col_dl1:
                # CSV completo
                csv = df_prompts.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Scarica CSV Completo",
                    data=csv,
                    file_name=f"prompt_{settore.replace(' ', '_')}_{numero_prompt}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col_dl2:
                # Excel con formattazione
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_prompts.to_excel(writer, index=False, sheet_name='Prompt')
                    categoria_stats.to_excel(writer, index=False, sheet_name='Statistiche')
                
                st.download_button(
                    label="📊 Scarica Excel con Statistiche",
                    data=output.getvalue(),
                    file_name=f"prompt_{settore.replace(' ', '_')}_{numero_prompt}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        else:
            st.error("❌ Nessun prompt generato. Prova a riformulare i parametri o riduci il numero richiesto.")
# ==========================================================
# 📊 FOOTER
# ==========================================================
st.divider()
st.caption("🔒 Applicazione protetta da password. La chiave API è configurata in modo sicuro nei secrets.")
st.caption("💡 Tip: Per numeri elevati (150+) potrebbero volerci alcuni minuti. Sii paziente!")
