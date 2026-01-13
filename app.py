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
        results = movie_service.search(search_query)
        for r in list(results)[:3]:
            col1, col2 = st.columns([3, 1])
            vote_global = getattr(r, 'vote_average', 0)
            with col1:
                st.write(f"**{r.title}** (⭐ {vote_global}/10)")
            with col2:
                st.button("Ajouter", key=f"btn_{r.id}", on_click=callback_ajouter_film, args=(r.id, r.title, vote_global))
    except Exception as e:
        st.error(f"Erreur recherche : {e}")

st.divider()

# --- SECTION 2 : SORTIES DE LA SEMAINE (MULTI-GENRES) ---
st.subheader("🗓️ Sorties Cinéma de la semaine")
try:
    today = datetime.date.today()
    next_week = today + datetime.timedelta(days=7)
    
    # Genres : Action(28), Aventure(12), Comédie(35), Thriller(53), Drame(18), SF(878), Histoire(36), Animation(16)
    genre_ids = "28,12,35,53,18,878,36,16"
    
    films_semaine = discover.discover_movies({
        'primary_release_date.gte': today,
        'primary_release_date.lte': next_week,
        'with_genres': genre_ids,
        'region': 'FR',
        'sort_by': 'popularity.desc'
    })

    ids_vus = [m['id'] for m in st.session_state.historique]
    compteur = 0

    for f in films_semaine:
        if str(f.id) in ids_vus: continue
        compteur += 1
        col1, col2 = st.columns([1, 2])
        vote_f = getattr(f, 'vote_average', 0)
        with col1:
            path = getattr(f, 'poster_path', None)
            if path: st.image(f"https://image.tmdb.org/t/p/w500{path}")
        with col2:
            st.markdown(f"**{f.title}**")
            st.caption(f"⭐ {vote_f}/10 | Genre principal : {f.genre_ids[0] if f.genre_ids else 'N/A'}")
            st.button("J'ai vu", key=f"saw_{f.id}", on_click=callback_ajouter_film, args=(f.id, f.title, vote_f))
        st.divider()
        if compteur >= 10: break # On affiche les 10 films les plus populaires
except Exception as e:
        st.error(f"Erreur recherche : {e}")

# --- SECTION 3 : RECOMMANDATIONS ---
films_aimes = [m for m in st.session_state.historique if m['avis'] == 'Aimé']
if films_aimes:
    st.subheader(f"✨ Parce que tu as aimé '{films_aimes[-1]['title']}'")
    try:
        recos = movie_service.recommendations(movie_id=films_aimes[-1]['id'])
        cols = st.columns(3)
        for i, r in enumerate(list(recos)[:3]):
            with cols[i]:
                path = getattr(r, 'poster_path', None)
                if path: st.image(f"https://image.tmdb.org/t/p/w500{path}")
                st.caption(f"{r.title} (⭐ {getattr(r, 'vote_average', 0)})")
    except:
        st.write("Ajoute plus de films !")
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
