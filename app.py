import streamlit as st
from tmdbv3api import TMDb, Movie, Discover
import datetime
import os

# --- CONFIGURATION TMDb ---
tmdb = TMDb()
# Remplace par ta vraie clé entre les guillemets
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
        return [line.strip().split("|")[0] for line in f.readlines() if "|" in line]

# --- INTERFACE ---
st.set_page_config(page_title="CinéPass Companion", page_icon="🍿")

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header("⚙️ Paramètres")
    if st.button("🗑️ Vider mon historique"):
        if os.path.exists(HISTORIQUE_FILE):
            os.remove(HISTORIQUE_FILE)
            st.success("Historique supprimé !")
            st.rerun()
        else:
            st.info("L'historique est déjà vide.")

st.title("🍿 Mon Assistant Ciné")

# --- SECTION 1 : RECHERCHE SÉCURISÉE ---
st.subheader("🔍 Ajouter un film déjà vu")
search_query = st.text_input("Rechercher un film (ex: Avatar, Inception...)")

if search_query:
    try:
        search_results = movie_service.search(search_query)
        
        # --- LA CORRECTION EST ICI ---
        # On force la conversion en liste pour éviter l'erreur "slice"
        results_list = list(search_results)
        
        if results_list:
            # Maintenant on peut prendre les 3 premiers sans erreur
            for r in results_list[:3]:
                col_s1, col_s2 = st.columns([3, 1])
                with col_s1:
                    # On sécurise la date
                    date_val = getattr(r, 'release_date', '')
                    year = date_val[:4] if date_val else "????"
                    st.write(f"**{r.title}** ({year})")
                with col_s2:
                    if st.button("Ajouter", key=f"search_{r.id}"):
                        sauvegarder_film(r.id, r.title)
                        st.success("Ajouté !")
                        st.rerun()
        else:
            st.warning("Aucun film trouvé.")

    except Exception as e:
        # On garde l'affichage de l'erreur réelle au cas où, mais ça ne devrait plus servir
        st.error(f"Erreur : {e}")

st.divider()

# --- SECTION 2 : SORTIES DE LA SEMAINE ---
st.subheader("🗓️ Sorties SF & Histoire (Annecy)")
try:
    today = datetime.date.today()
    next_week = today + datetime.timedelta(days=7)

    films = discover.discover_movies({
        'primary_release_date.gte': today,
        'primary_release_date.lte': next_week,
        'with_genres': '878,36', # SF et Histoire
        'region': 'FR'
    })

    historique = charger_historique()

    if not films:
        st.info("Rien de spécial en SF/Histoire cette semaine.")
    else:
        for f in films:
            if str(f.id) in historique:
                continue
            col1, col2 = st.columns([1, 2])
            with col1:
                path = getattr(f, 'poster_path', None)
                if path:
                    st.image(f"https://image.tmdb.org/t/p/w500{path}")
            with col2:
                st.markdown(f"**{f.title}**")
                st.caption(f"Sortie : {getattr(f, 'release_date', 'Inconnue')} | ⭐ {getattr(f, 'vote_average', 0)}/10")
                if st.button(f"J'ai vu", key=f"main_{f.id}"):
                    sauvegarder_film(f.id, f.title)
                    st.rerun()
            st.divider()
except Exception as e:
        st.error(f"L'erreur réelle est : {e}")

# --- SECTION 3 : RECOMMANDATIONS ---
if historique:
    st.subheader("✨ Parce que tu as aimé...")
    try:
        # On se base sur le dernier film ajouté
        recos = movie_service.recommendations(movie_id=historique[-1])
        if recos:
            cols = st.columns(3)
            for i, r in enumerate(recos[:3]):
                with cols[i]:
                    path = getattr(r, 'poster_path', None)
                    if path:
                        st.image(f"https://image.tmdb.org/t/p/w500{path}")
                    st.caption(r.title)
    except Exception:
        st.write("Ajoute plus de films pour débloquer les recommandations !")
