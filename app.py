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

# --- GESTION DE L'HISTORIQUE ---
HISTORIQUE_FILE = "mes_films.txt"

def sauvegarder_film(movie_id, title):
    with open(HISTORIQUE_FILE, "a") as f:
        f.write(f"{movie_id}|{title}\n")

def charger_historique():
    if not os.path.exists(HISTORIQUE_FILE) or os.stat(HISTORIQUE_FILE).st_size == 0:
        return []
    with open(HISTORIQUE_FILE, "r") as f:
        # On ignore les lignes vides
        return [line.strip().split("|")[0] for line in f.readlines() if "|" in line]

# --- INTERFACE MOBILE ---
st.set_page_config(page_title="CinéPass Companion", page_icon="🎬")

st.title("🍿 Mon Assistant Ciné")
st.subheader("Sorties SF & Histoire de la semaine")

# --- BARRE LATÉRALE (SIDEBAR) ---
with st.sidebar:
    st.header("⚙️ Paramètres")
    if st.button("🗑️ Vider mon historique"):
        if os.path.exists(HISTORIQUE_FILE):
            os.remove(HISTORIQUE_FILE)
            st.success("Historique supprimé !")
            st.rerun()
        else:
            st.info("L'historique est déjà vide.")

# Date du jour et de la semaine prochaine
today = datetime.date.today()
next_week = today + datetime.timedelta(days=7)

# Récupération des films (Genres : 878=SF, 36=Histoire)
films = discover.discover_movies({
    'primary_release_date.gte': today,
    'primary_release_date.lte': next_week,
    'with_genres': '878,36',
    'region': 'FR'
})

historique = charger_historique()

if not films:
    st.write("Pas de sorties SF/Histoire cette semaine. Teste un autre genre ?")
else:
    for f in films:
        # On n'affiche pas les films déjà vus
        if str(f.id) in historique:
            continue
            
        with st.container():
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(f"https://image.tmdb.org/t/p/w500{f.poster_path}")
            with col2:
                st.markdown(f"**{f.title}**")
                st.caption(f"Sortie : {f.release_date} | ⭐ {f.vote_average}/10")
                st.write(f"{f.overview[:150]}...")
                
                if st.button(f"J'ai vu {f.title}", key=f.id):
                    sauvegarder_film(f.id, f.title)
                    st.success("Ajouté à l'historique !")
                    st.rerun()
            st.divider()

# --- RECOMMANDATIONS BASÉES SUR L'HISTORIQUE ---
if historique:
    st.subheader("✨ Parce que tu as aimé...")
    # On prend le dernier film vu pour recommander
    last_movie_id = historique[-1]
    recos = movie_service.recommendations(movie_id=last_movie_id)
    
    cols = st.columns(3)
    for i, r in enumerate(recos[:3]):
        with cols[i]:
            st.image(f"https://image.tmdb.org/t/p/w500{r.poster_path}")
            st.caption(r.title)


# --- BARRE DE RECHERCHE SÉCURISÉE ---
st.divider()
st.subheader("🔍 Ajouter un film déjà vu")
search_query = st.text_input("Rechercher un film (ex: Inception, Gladiator...)")

if search_query:
    try:
        search_results = movie_service.search(search_query)
        
        # On vérifie si on a bien reçu des résultats avant de boucler
        if search_results and len(search_results) > 0:
            for r in search_results[:3]: 
                col_s1, col_s2 = st.columns([3, 1])
                with col_s1:
                    # On sécurise l'affichage de la date au cas où elle est vide
                    year = r.release_date[:4] if getattr(r, 'release_date', None) else "????"
                    st.write(f"{r.title} ({year})")
                with col_s2:
                    if st.button("Ajouter", key=f"search_{r.id}"):
                        sauvegarder_film(r.id, r.title)
                        st.success("Ajouté !")
                        st.rerun()
        else:
            st.warning("Aucun film trouvé pour cette recherche.")
            
    except Exception as e:
        st.error("Oups ! Petit souci avec la recherche. Réessaie avec un autre titre.")
