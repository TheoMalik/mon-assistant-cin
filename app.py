import streamlit as st
from tmdbv3api import TMDb, Movie, Discover
import datetime
import os

# --- CONFIGURATION TMDb ---
tmdb = TMDb()
tmdb.api_key = '5ccac4fafac407ac28bb55c4fd44fb9c' 
tmdb.language = 'fr'
movie_service = Movie()
discover = Discover()

# --- INITIALISATION ---
HISTORIQUE_FILE = "mes_films.txt"

# On s'assure que l'historique est chargé une seule fois au début
if 'historique' not in st.session_state:
    if os.path.exists(HISTORIQUE_FILE):
        with open(HISTORIQUE_FILE, "r", encoding="utf-8") as f:
            st.session_state.historique = [line.strip().split("|")[0] for line in f.readlines() if "|" in line]
    else:
        st.session_state.historique = []

# --- FONCTIONS ACTIONS (CALLBACKS) ---
def callback_ajouter_film(movie_id, title):
    movie_id_str = str(movie_id)
    if movie_id_str not in st.session_state.historique:
        # 1. Mise à jour de la mémoire vive
        st.session_state.historique.append(movie_id_str)
        # 2. Écriture physique dans le fichier
        try:
            with open(HISTORIQUE_FILE, "a", encoding="utf-8") as f:
                f.write(f"{movie_id_str}|{title}\n")
            st.toast(f"✅ {title} ajouté !")
        except Exception as e:
            st.error(f"Erreur d'écriture : {e}")

def callback_vider_historique():
    if os.path.exists(HISTORIQUE_FILE):
        os.remove(HISTORIQUE_FILE)
    st.session_state.historique = []
    st.toast("🗑️ Historique vidé")

# --- INTERFACE ---
st.set_page_config(page_title="CinéPass Companion", page_icon="🍿")

with st.sidebar:
    st.header("⚙️ Paramètres")
    st.button("🗑️ Vider mon historique", on_click=callback_vider_historique)
    st.write(f"Films vus : {len(st.session_state.historique)}")

st.title("🍿 Mon Assistant Ciné")

# --- RECHERCHE ---
st.subheader("🔍 Ajouter un film déjà vu")
search_query = st.text_input("Rechercher un film...", key="input_search")

if search_query:
    try:
        results = movie_service.search(search_query)
        # On transforme le résultat en liste pour pouvoir l'utiliser
        for r in list(results)[:3]:
            col1, col2 = st.columns([3, 1])
            with col1:
                year = r.release_date[:4] if getattr(r, 'release_date', None) else "????"
                st.write(f"**{r.title}** ({year})")
            with col2:
                # Utilisation du Callback 'on_click'
                st.button("Ajouter", 
                          key=f"btn_{r.id}", 
                          on_click=callback_ajouter_film, 
                          args=(r.id, r.title))
    except Exception as e:
        st.error(f"Erreur : {e}")

st.divider()

# --- SORTIES DE LA SEMAINE ---
st.subheader("🗓️ Sorties de la semaine")
try:
    today = datetime.date.today()
    films_semaine = discover.discover_movies({
        'primary_release_date.gte': today,
        'primary_release_date.lte': today + datetime.timedelta(days=7),
        'with_genres': '878,36',
        'region': 'FR'
    })

    for f in films_semaine:
        if str(f.id) in st.session_state.historique:
            continue
        col1, col2 = st.columns([1, 2])
        with col1:
            if getattr(f, 'poster_path', None):
                st.image(f"https://image.tmdb.org/t/p/w500{f.poster_path}")
        with col2:
            st.markdown(f"**{f.title}**")
            st.button("J'ai vu", 
                      key=f"saw_{f.id}", 
                      on_click=callback_ajouter_film, 
                      args=(f.id, f.title))
        st.divider()
except:
    st.write("Impossible de charger les sorties.")

# --- RECOMMANDATIONS ---
if st.session_state.historique:
    st.subheader("✨ Parce que tu as aimé...")
    try:
        dernier_id = st.session_state.historique[-1]
        recos = movie_service.recommendations(movie_id=dernier_id)
        cols = st.columns(3)
        for i, r in enumerate(list(recos)[:3]):
            with cols[i]:
                if getattr(r, 'poster_path', None):
                    st.image(f"https://image.tmdb.org/t/p/w500{r.poster_path}")
                st.caption(r.title)
    except:
        st.write("Ajoute plus de films !")
