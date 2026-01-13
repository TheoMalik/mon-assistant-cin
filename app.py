import streamlit as st
from tmdbv3api import TMDb, Movie, Discover
import datetime
import os

# --- CONFIGURATION TMDb ---
tmdb = TMDb()
tmdb.api_key = 'TA_CLE_API_ICI' # <--- Assure-toi que ta clé est bien là
tmdb.language = 'fr'
movie_service = Movie()
discover = Discover()

# --- GESTION DE L'HISTORIQUE ---
HISTORIQUE_FILE = "mes_films.txt"

def sauvegarder_film(movie_id, title):
    with open(HISTORIQUE_FILE, "a") as f:
        f.write(f"{movie_id}|{title}\n")

def charger_historique():
    if not os.path.exists(HISTORIQUE_FILE) or os.stat(HISTORIQUE_FILE).st_size == 0:
        return []
    with open(HISTORIQUE_FILE, "r") as f:
        return [line.strip().split("|")[0] for line in f.readlines() if "|" in line]

# --- INTERFACE ---
st.set_page_config(page_title="CinéPass Companion", page_icon="🎬")

# Barre latérale pour les réglages
with st.sidebar:
    st.header("⚙️ Paramètres")
    if st.button("🗑️ Vider mon historique"):
        if os.path.exists(HISTORIQUE_FILE):
            os.remove(HISTORIQUE_FILE)
            st.success("Historique vidé !")
            st.rerun()

st.title("🍿 Mon Assistant Ciné")

# --- SECTION 1 : RECHERCHE SÉCURISÉE ---
st.subheader("🔍 Ajouter un film déjà vu")
search_query = st.text_input("Rechercher un film (ex: Inception, Avatar...)")

if search_query:
    try:
        search_results = movie_service.search(search_query)
        # On vérifie si on a des résultats exploitables
        if hasattr(search_results, 'results') and search_results.results:
            results_to_show = search_results.results[:3]
        elif isinstance(search_results, list):
            results_to_show = search_results[:3]
        else:
            results_to_show = []

        if results_to_show:
            for r in results_to_show:
                col_s1, col_s2 = st.columns([3, 1])
                with col_s1:
                    date = getattr(r, 'release_date', '????-')
                    year = date[:4] if date else "????"
                    st.write(f"**{r.title}** ({year})")
                with col_s2:
                    if st.button("Ajouter", key=f"search_{r.id}"):
                        sauvegarder_film(r.id, r.title)
                        st.success("Ajouté !")
                        st.rerun()
        else:
            st.warning("Aucun résultat trouvé.")
    except Exception as e:
        st.error(f"Erreur de recherche. Essaie un titre plus simple.")

st.divider()

# --- SECTION 2 : SORTIES DE LA SEMAINE ---
st.subheader("🗓️ Sorties SF & Histoire (Annecy)")
today = datetime.date.today()
next_week = today + datetime.timedelta(days=7)

films = discover.discover_movies({
    'primary_release_date.gte': today,
    'primary_release_date.lte': next_week,
    'with_genres': '878,36',
    'region': 'FR'
})

historique = charger_historique()

if not films:
    st.info("Rien de spécial en SF/Histoire cette semaine.")
else:
    for f in films:
        if str(f.id) in historique: continue
        col1, col2 = st.columns([1, 2])
        with col1:
            poster = f"https://image.tmdb.org/t/p/w500{f.poster_path}" if f.poster_path else None
            if poster: st.image(poster)
        with col2:
            st.markdown(f"**{f.title}**")
            st.caption(f"Sortie : {f.release_date} | ⭐ {f.vote_average}/10")
            if st.button(f"J'ai vu", key=f"main_{f.id}"):
                sauvegarder_film(f.id, f.title)
                st.rerun()
        st.divider()

# --- SECTION 3 : RECOMMANDATIONS ---
if historique:
    st.subheader("✨ Recommandations pour toi")
    try:
        recos = movie_service.recommendations(movie_id=historique[-1])
        cols = st.columns(3)
        for i, r in enumerate(recos[:3]):
            with cols[i]:
                if r.poster_path: st.image(f"https://image.tmdb.org/t/p/w500{r.poster_path}")
                st.caption(r.title)
    except:
        st.write("Ajoute plus de films pour débloquer les recos !")
