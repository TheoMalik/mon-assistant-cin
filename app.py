import streamlit as st
from tmdbv3api import TMDb, Movie, Discover
import datetime
import os

# --- CONFIGURATION TMDb ---
tmdb = TMDb()
# METS TA VRAIE CLÉ ICI
tmdb.api_key = '5ccac4fafac407ac28bb55c4fd44fb9c' 
tmdb.language = 'fr'
movie_service = Movie()
discover = Discover()

# --- GESTION DE L'HISTORIQUE ---
HISTORIQUE_FILE = "mes_films.txt"

def sauvegarder_film(movie_id, title):
    # 1. Écriture dans le fichier pour la persistance
    with open(HISTORIQUE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{movie_id}|{title}\n")
    # 2. Mise à jour de la mémoire immédiate de l'app
    if 'historique' in st.session_state:
        st.session_state['historique'].append(str(movie_id))

def charger_historique():
    if not os.path.exists(HISTORIQUE_FILE) or os.stat(HISTORIQUE_FILE).st_size == 0:
        return []
    with open(HISTORIQUE_FILE, "r", encoding="utf-8") as f:
        return [line.strip().split("|")[0] for line in f.readlines() if "|" in line]

# Initialisation de la session au démarrage
if 'historique' not in st.session_state:
    st.session_state['historique'] = charger_historique()

# --- INTERFACE ---
st.set_page_config(page_title="CinéPass Companion", page_icon="🍿", layout="centered")

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header("⚙️ Paramètres")
    if st.button("🗑️ Vider mon historique"):
        if os.path.exists(HISTORIQUE_FILE):
            os.remove(HISTORIQUE_FILE)
        st.session_state['historique'] = []
        st.success("Historique vidé !")
        st.rerun()

st.title("🍿 Mon Assistant Ciné")

# --- SECTION 1 : RECHERCHE ---
st.subheader("🔍 Ajouter un film déjà vu")
search_query = st.text_input("Rechercher un film (ex: Avatar, Inception...)", key="main_search")

if search_query:
    try:
        search_results = movie_service.search(search_query)
        results_list = list(search_results)
        
        if results_list:
            for r in results_list[:3]:
                col_s1, col_s2 = st.columns([3, 1])
                with col_s1:
                    date_val = getattr(r, 'release_date', '')
                    year = date_val[:4] if date_val else "????"
                    st.write(f"**{r.title}** ({year})")
                with col_s2:
                    # On change la clé du bouton pour qu'elle soit unique
                    if st.button("Ajouter", key=f"btn_search_{r.id}"):
                        sauvegarder_film(r.id, r.title)
                        st.toast(f"✅ {r.title} ajouté !")
                        st.rerun()
        else:
            st.warning("Aucun film trouvé.")
    except Exception as e:
        st.error(f"Erreur recherche : {e}")

st.divider()

# --- SECTION 2 : SORTIES DE LA SEMAINE ---
st.subheader("🗓️ Sorties SF & Histoire (Annecy)")
try:
    today = datetime.date.today()
    next_week = today + datetime.timedelta(days=7)
    
    films_semaine = discover.discover_movies({
        'primary_release_date.gte': today,
        'primary_release_date.lte': next_week,
        'with_genres': '878,36',
        'region': 'FR'
    })

    # On utilise la liste en mémoire pour filtrer
    historique_actuel = st.session_state['historique']

    films_a_afficher = [f for f in films_semaine if str(f.id) not in historique_actuel]

    if not films_a_afficher:
        st.info("Rien de nouveau en SF/Histoire pour tes goûts cette semaine.")
    else:
        for f in films_a_afficher:
            col1, col2 = st.columns([1, 2])
            with col1:
                if getattr(f, 'poster_path', None):
                    st.image(f"https://image.tmdb.org/t/p/w500{f.poster_path}")
            with col2:
                st.markdown(f"**{f.title}**")
                st.caption(f"Sortie : {f.release_date} | ⭐ {f.vote_average}/10")
                if st.button("J'ai vu", key=f"btn_week_{f.id}"):
                    sauvegarder_film(f.id, f.title)
                    st.toast(f"🍿 Super ! Ajouté à ton historique.")
                    st.rerun()
            st.divider()
except Exception as e:
    st.error(f"Erreur sorties : {e}")

# --- SECTION 3 : RECOMMANDATIONS ---
if st.session_state['historique']:
    st.subheader("✨ Parce que tu as aimé...")
    try:
        dernier_id = st.session_state['historique'][-1]
        recos = movie_service.recommendations(movie_id=dernier_id)
        
        if recos:
            cols = st.columns(3)
            for i, r in enumerate(recos[:3]):
                with cols[i]:
                    if getattr(r, 'poster_path', None):
                        st.image(f"https://image.tmdb.org/t/p/w500{r.poster_path}")
                    st.caption(r.title)
    except:
        st.write("Continue d'ajouter des films pour affiner tes recommandations !")
