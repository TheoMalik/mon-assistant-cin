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

if 'historique' not in st.session_state:
    st.session_state.historique = []
    if os.path.exists(HISTORIQUE_FILE):
        with open(HISTORIQUE_FILE, "r", encoding="utf-8") as f:
            for line in f.readlines():
                l = line.strip().split("|")
                if len(l) >= 2:
                    st.session_state.historique.append({
                        'id': l[0], 'title': l[1], 
                        'vote': l[2] if len(l) > 2 else "0.0", 
                        'avis': l[3] if len(l) > 3 else "Aimé"
                    })

# --- FONCTIONS ACTIONS ---
def callback_ajouter_film(movie_id, title, vote):
    movie_id_str = str(movie_id)
    if not any(m['id'] == movie_id_str for m in st.session_state.historique):
        st.session_state.historique.append({'id': movie_id_str, 'title': title, 'vote': str(vote), 'avis': 'Aimé'})
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

def callback_vider_tout():
    if os.path.exists(HISTORIQUE_FILE): os.remove(HISTORIQUE_FILE)
    st.session_state.historique = []
    st.rerun()

# --- INTERFACE ---
st.set_page_config(page_title="CinéPass Companion", page_icon="🍿")
st.title("🍿 Mon Assistant Ciné")

# --- SECTION 1 : RECHERCHE ---
st.subheader("🔍 Ajouter un film déjà vu")
search_query = st.text_input("Rechercher un film...", key="input_search")

if search_query:
    try:
        results_raw = movie_service.search(search_query)
        # SÉCURITÉ : On extrait la liste de films
        results_list = results_raw.results if hasattr(results_raw, 'results') else list(results_raw)
        
        for r in results_list[:3]:
            # On vérifie que 'r' n'est pas une simple chaîne de texte
            if isinstance(r, str): continue
            
            col1, col2 = st.columns([3, 1])
            vote_global = getattr(r, 'vote_average', 0)
            with col1:
                st.write(f"**{r.title}** (⭐ {vote_global}/10)")
            with col2:
                st.button("Ajouter", key=f"btn_{r.id}", on_click=callback_ajouter_film, args=(r.id, r.title, vote_global))
    except Exception as e:
        st.error(f"Erreur recherche : {e}")

st.divider()

# --- SECTION 2 : SORTIES DE LA SEMAINE ---
st.subheader("🗓️ Sorties Cinéma de la semaine")
try:
    today = datetime.date.today()
    films_raw = discover.discover_movies({
        'primary_release_date.gte': today,
        'primary_release_date.lte': today + datetime.timedelta(days=7),
        'with_genres': "28,12,35,53,18,878,36,16",
        'region': 'FR',
        'sort_by': 'popularity.desc'
    })

    # SÉCURITÉ : On s'assure d'avoir la liste 'results'
    liste_films = films_raw.results if hasattr(films_raw, 'results') else list(films_raw)
    ids_vus = [m['id'] for m in st.session_state.historique]
    compteur = 0

    for f in liste_films:
        if isinstance(f, str) or str(getattr(f, 'id', '')) in ids_vus: continue
        compteur += 1
        
        col1, col2 = st.columns([1, 2])
        vote_f = getattr(f, 'vote_average', 0)
        with col1:
            path = getattr(f, 'poster_path', None)
            if path: st.image(f"https://image.tmdb.org/t/p/w500{path}")
        with col2:
            st.markdown(f"**{getattr(f, 'title', 'Sans titre')}**")
            st.caption(f"⭐ {vote_f}/10")
            st.button("J'ai vu", key=f"saw_{f.id}", on_click=callback_ajouter_film, args=(f.id, f.title, vote_f))
        
        st.divider()
        if compteur >= 10: break 
except Exception as e:
    st.error(f"Erreur chargement sorties : {e}")

# --- SECTION 3 : RECOMMANDATIONS ---
films_aimes = [m for m in st.session_state.historique if m['avis'] == 'Aimé']
if films_aimes:
    st.subheader(f"✨ Parce que tu as aimé '{films_aimes[-1]['title']}'")
    try:
        recos_raw = movie_service.recommendations(movie_id=films_aimes[-1]['id'])
        recos_list = recos_raw.results if hasattr(recos_raw, 'results') else list(recos_raw)
        if recos_list:
            cols = st.columns(3)
            for i, r in enumerate(recos_list[:3]):
                if isinstance(r, str): continue
                with cols[i]:
                    path = getattr(r, 'poster_path', None)
                    if path: st.image(f"https://image.tmdb.org/t/p/w500{path}")
                    st.caption(f"{getattr(r, 'title', '')} (⭐ {getattr(r, 'vote_average', 0)})")
    except:
        pass
st.divider()

# --- SECTION 4 : MON HISTORIQUE & AVIS ---
st.subheader("📜 Mon Historique & Avis")
if st.session_state.historique:
    for movie in reversed(st.session_state.historique):
        with st.expander(f"{movie['title']} — ⭐ {movie['vote']}/10"):
            col_avis, col_del = st.columns([3, 1])
            with col_avis:
                choix = ["Aimé", "Bof"]
                index_actuel = choix.index(movie['avis']) if movie['avis'] in choix else 0
                nouvel_avis = st.radio(f"Avis :", choix, index=index_actuel, key=f"rad_{movie['id']}", horizontal=True)
                if nouvel_avis != movie['avis']:
                    callback_modifier_avis(movie['id'], nouvel_avis)
            with col_del:
                st.button("Supprimer", key=f"del_{movie['id']}", on_click=callback_supprimer_film, args=(movie['id'],))
    
    if st.button("🗑️ Tout effacer", key="clear_all"):
        callback_vider_tout()
else:
    st.info("Ton historique est vide.")
