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

# --- INITIALISATION ---
HISTORIQUE_FILE = "mes_films.txt"

# Initialisation de l'historique en mémoire (ID + Titre)
if 'historique' not in st.session_state:
    if os.path.exists(HISTORIQUE_FILE):
        with open(HISTORIQUE_FILE, "r", encoding="utf-8") as f:
            # On stocke des dictionnaires {'id': '...', 'title': '...'}
            lignes = [line.strip().split("|") for line in f.readlines() if "|" in line]
            st.session_state.historique = [{'id': l[0], 'title': l[1]} for l in lignes]
    else:
        st.session_state.historique = []

# --- FONCTIONS ACTIONS (CALLBACKS) ---
def callback_ajouter_film(movie_id, title):
    movie_id_str = str(movie_id)
    # On vérifie si le film n'est pas déjà dans la liste
    if not any(m['id'] == movie_id_str for m in st.session_state.historique):
        # 1. Mise à jour de la mémoire
        st.session_state.historique.append({'id': movie_id_str, 'title': title})
        # 2. Écriture physique
        with open(HISTORIQUE_FILE, "a", encoding="utf-8") as f:
            f.write(f"{movie_id_str}|{title}\n")
        st.toast(f"✅ {title} ajouté !")

def callback_supprimer_film(movie_id):
    movie_id_str = str(movie_id)
    # 1. Filtrer la liste en mémoire
    st.session_state.historique = [m for m in st.session_state.historique if m['id'] != movie_id_str]
    # 2. Réécrire entièrement le fichier avec la nouvelle liste
    with open(HISTORIQUE_FILE, "w", encoding="utf-8") as f:
        for m in st.session_state.historique:
            f.write(f"{m['id']}|{m['title']}\n")
    st.toast("🗑️ Film supprimé de l'historique")

def callback_vider_tout():
    if os.path.exists(HISTORIQUE_FILE):
        os.remove(HISTORIQUE_FILE)
    st.session_state.historique = []
    st.toast("🧹 Historique entièrement vidé")

# --- INTERFACE ---
st.set_page_config(page_title="CinéPass Companion", page_icon="🍿")

# --- BARRE LATÉRALE : GESTION DE L'HISTORIQUE ---
with st.sidebar:
    st.header("🎬 Mon Historique")
    
    if not st.session_state.historique:
        st.write("Aucun film dans la liste.")
    else:
        st.write(f"Nombre de films : {len(st.session_state.historique)}")
        st.divider()
        # Affichage de chaque film avec un bouton supprimer
        for movie in st.session_state.historique:
            col_t, col_b = st.columns([4, 1])
            col_t.write(movie['title'])
            col_b.button("❌", key=f"del_{movie['id']}", on_click=callback_supprimer_film, args=(movie['id'],))
        
        st.divider()
        if st.button("🗑️ Tout effacer", on_click=callback_vider_tout):
            st.rerun()

st.title("🍿 Mon Assistant Ciné")

# --- RECHERCHE ---
st.subheader("🔍 Ajouter un film déjà vu")
search_query = st.text_input("Rechercher un film...", key="input_search")

if search_query:
    try:
        results = movie_service.search(search_query)
        for r in list(results)[:3]:
            col1, col2 = st.columns([3, 1])
            with col1:
                year = r.release_date[:4] if getattr(r, 'release_date', None) else "????"
                st.write(f"**{r.title}** ({year})")
            with col2:
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

    # Liste des IDs déjà vus pour filtrer
    ids_vus = [m['id'] for m in st.session_state.historique]

    for f in films_semaine:
        if str(f.id) in ids_vus:
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
        # On recommande à partir du dernier film ajouté
        dernier_id = st.session_state.historique[-1]['id']
        recos = movie_service.recommendations(movie_id=dernier_id)
        cols = st.columns(3)
        for i, r in enumerate(list(recos)[:3]):
            with cols[i]:
                if getattr(r, 'poster_path', None):
                    st.image(f"https://image.tmdb.org/t/p/w500{r.poster_path}")
                st.caption(r.title)
    except:
        st.write("Ajoute d'autres films pour voir des recommandations !")
