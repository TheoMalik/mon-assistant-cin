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

# --- INITIALISATION SÉCURISÉE ---
if 'historique' not in st.session_state:
    st.session_state.historique = []
    if os.path.exists(HISTORIQUE_FILE):
        with open(HISTORIQUE_FILE, "r", encoding="utf-8") as f:
            for line in f.readlines():
                l = line.strip().split("|")
                if len(l) >= 2:
                    # On gère les anciens fichiers (2 colonnes) et les nouveaux (4 colonnes)
                    m_id = l[0]
                    m_title = l[1]
                    m_vote = l[2] if len(l) > 2 else "0.0"  # Note par défaut si manquante
                    m_avis = l[3] if len(l) > 3 else "Aimé" # Avis par défaut si manquant
                    st.session_state.historique.append({
                        'id': m_id, 
                        'title': m_title, 
                        'vote': m_vote, 
                        'avis': m_avis
                    })
# --- FONCTIONS ACTIONS ---
def callback_ajouter_film(movie_id, title, vote):
    movie_id_str = str(movie_id)
    if not any(m['id'] == movie_id_str for m in st.session_state.historique):
        # Par défaut, un film ajouté est considéré comme "Aimé"
        nouvel_entree = {'id': movie_id_str, 'title': title, 'vote': str(vote), 'avis': 'Aimé'}
        st.session_state.historique.append(nouvel_entree)
        sauvegarder_fichier()
        st.toast(f"✅ {title} ajouté !")

def callback_modifier_avis(movie_id, nouvel_avis):
    for m in st.session_state.historique:
        if m['id'] == str(movie_id):
            m['avis'] = nouvel_avis
            break
    sauvegarder_fichier()
    st.rerun()

def callback_supprimer_film(movie_id):
    st.session_state.historique = [m for m in st.session_state.historique if m['id'] != str(movie_id)]
    sauvegarder_fichier()
    st.toast("🗑️ Supprimé")

def sauvegarder_fichier():
    with open(HISTORIQUE_FILE, "w", encoding="utf-8") as f:
        for m in st.session_state.historique:
            f.write(f"{m['id']}|{m['title']}|{m['vote']}|{m['avis']}\n")

# --- INTERFACE ---
st.set_page_config(page_title="CinéPass Companion", page_icon="🍿")
st.title("🍿 Mon Assistant Ciné")

# --- RECHERCHE ---
st.subheader("🔍 Ajouter un film déjà vu")
search_query = st.text_input("Rechercher un film...", key="input_search")

if search_query:
    try:
        results = movie_service.search(search_query)
        for r in list(results)[:3]:
            col1, col2 = st.columns([3, 1])
            vote_global = getattr(r, 'vote_average', 0)
            with col1:
                st.write(f"**{r.title}** (⭐ {vote_global}/10)")
            with col2:
                st.button("Ajouter", key=f"btn_{r.id}", on_click=callback_ajouter_film, args=(r.id, r.title, vote_global))
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
    ids_vus = [m['id'] for m in st.session_state.historique]
    for f in films_semaine:
        if str(f.id) in ids_vus: continue
        col1, col2 = st.columns([1, 2])
        vote_f = getattr(f, 'vote_average', 0)
        with col1:
            if getattr(f, 'poster_path', None):
                st.image(f"https://image.tmdb.org/t/p/w500{f.poster_path}")
        with col2:
            st.markdown(f"**{f.title}** \n⭐ {vote_f}/10")
            st.button("J'ai vu", key=f"saw_{f.id}", on_click=callback_ajouter_film, args=(f.id, f.title, vote_f))
        st.divider()
except:
    st.write("Erreur chargement sorties.")

# --- RECOMMANDATIONS (FILTRÉES) ---
# On cherche le dernier film que l'utilisateur a "Aimé"
films_aimes = [m for m in st.session_state.historique if m['avis'] == 'Aimé']

if films_aimes:
    st.subheader(f"✨ Parce que tu as aimé '{films_aimes[-1]['title']}'")
    try:
        recos = movie_service.recommendations(movie_id=films_aimes[-1]['id'])
        cols = st.columns(3)
        for i, r in enumerate(list(recos)[:3]):
            with cols[i]:
                if getattr(r, 'poster_path', None):
                    st.image(f"https://image.tmdb.org/t/p/w500{r.poster_path}")
                st.caption(f"{r.title} (⭐ {getattr(r, 'vote_average', 0)})")
    except:
        st.write("Plus de recommandations bientôt !")
elif st.session_state.historique:
    st.info("Change l'avis d'un film en 'Aimé' pour voir des recommandations !")

st.divider()

# --- MON HISTORIQUE AVEC NOTATION ---
st.subheader("📜 Mon Historique & Avis")
if not st.session_state.historique:
    st.info("Ton historique est vide.")
else:
    for movie in reversed(st.session_state.historique):
        with st.expander(f"{movie['title']} — Note : {movie['vote']}/10"):
            col_avis, col_del = st.columns([3, 1])
            with col_avis:
                # Sélecteur d'avis
                choix = ["Aimé", "Bof"]
                index_actuel = choix.index(movie['avis']) if movie['avis'] in choix else 0
                nouvel_avis = st.radio(f"Ton avis sur {movie['title']} :", choix, index=index_actuel, key=f"rad_{movie['id']}", horizontal=True)
                if nouvel_avis != movie['avis']:
                    callback_modifier_avis(movie['id'], nouvel_avis)
            with col_del:
                st.button("Supprimer", key=f"del_{movie['id']}", on_click=callback_supprimer_film, args=(movie['id'],))
