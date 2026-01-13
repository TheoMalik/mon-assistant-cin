import streamlit as st
from tmdbv3api import TMDb, Movie, Discover, TV
import datetime
import os
import requests 

# --- CONFIGURATION TMDb ---
tmdb = TMDb()
API_KEY = '5ccac4fafac407ac28bb55c4fd44fb9c'  
tmdb.api_key = API_KEY
tmdb.language = 'fr'

# Services
movie_service = Movie()
tv_service = TV()
discover = Discover()

# --- GESTION DES FICHIERS ---
FILES = {
    "movie": "mes_films.txt",
    "tv": "mes_series.txt"
}

if 'historique_movie' not in st.session_state: st.session_state.historique_movie = []
if 'historique_tv' not in st.session_state: st.session_state.historique_tv = []

def charger_historique(media_type):
    file_path = FILES[media_type]
    data = []
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f.readlines():
                l = line.strip().split("|")
                if len(l) >= 2:
                    data.append({
                        'id': l[0], 'title': l[1], 
                        'vote': l[2] if len(l) > 2 else "0.0", 
                        'avis': l[3] if len(l) > 3 else "Aimé"
                    })
    return data

def sauvegarder_historique(media_type, data_list):
    file_path = FILES[media_type]
    with open(file_path, "w", encoding="utf-8") as f:
        for m in data_list:
            f.write(f"{m['id']}|{m['title']}|{m['vote']}|{m['avis']}\n")

# Fonction pour générer le texte du backup
def generer_backup(data_list):
    """Crée une chaîne de texte prête à être sauvegardée"""
    return "\n".join([f"{m['id']}|{m['title']}|{m['vote']}|{m['avis']}" for m in data_list])

st.session_state.historique_movie = charger_historique("movie")
st.session_state.historique_tv = charger_historique("tv")

# --- FONCTIONS UTILITAIRES ---
def get_safe_list(api_response):
    try:
        if hasattr(api_response, 'results'): data = api_response.results
        elif isinstance(api_response, dict) and 'results' in api_response: data = api_response['results']
        else: data = api_response
        clean_list = list(data)
        if clean_list and isinstance(clean_list[0], str): return []
        return clean_list
    except: return []

def get_providers_direct(media_id, media_type):
    try:
        url = f"https://api.themoviedb.org/3/{media_type}/{media_id}/watch/providers?api_key={API_KEY}"
        response = requests.get(url)
        data = response.json()
        if 'results' in data and 'FR' in data['results']:
            fr_data = data['results']['FR']
            if 'flatrate' in fr_data:
                return [p['provider_name'] for p in fr_data['flatrate']]
    except Exception: return []
    return []

def get_trailer(media_id, media_type):
    try:
        service = movie_service if media_type == 'movie' else tv_service
        videos = service.videos(media_id)
        for v in videos:
            if getattr(v, 'site', '') == "YouTube" and getattr(v, 'type', '') == "Trailer":
                return f"https://www.youtube.com/watch?v={v.key}"
        for v in videos:
            if getattr(v, 'site', '') == "YouTube":
                return f"https://www.youtube.com/watch?v={v.key}"
    except: return None
    return None

# --- ACTIONS ---
def callback_ajouter(media_id, title, vote, media_type):
    mid = str(media_id)
    target_list = st.session_state.historique_movie if media_type == 'movie' else st.session_state.historique_tv
    
    if not any(m['id'] == mid for m in target_list):
        target_list.append({'id': mid, 'title': title, 'vote': str(vote), 'avis': 'Aimé'})
        sauvegarder_historique(media_type, target_list)
        st.toast(f"✅ {title} ajouté !")

def callback_supprimer(media_id, media_type):
    mid = str(media_id)
    if media_type == 'movie':
        st.session_state.historique_movie = [m for m in st.session_state.historique_movie if m['id'] != mid]
        sauvegarder_historique('movie', st.session_state.historique_movie)
    else:
        st.session_state.historique_tv = [m for m in st.session_state.historique_tv if m['id'] != mid]
        sauvegarder_historique('tv', st.session_state.historique_tv)
    st.toast("🗑️ Supprimé")

def callback_modifier_avis(media_id, nouvel_avis, media_type):
    target_list = st.session_state.historique_movie if media_type == 'movie' else st.session_state.historique_tv
    for m in target_list:
        if m['id'] == str(media_id):
            m['avis'] = nouvel_avis
            break
    sauvegarder_historique(media_type, target_list)
    st.rerun()

def callback_vider(media_type):
    file_path = FILES[media_type]
    if os.path.exists(file_path): os.remove(file_path)
    if media_type == 'movie': st.session_state.historique_movie = []
    else: st.session_state.historique_tv = []
    st.rerun()

# --- INTERFACE ---
st.set_page_config(page_title="Popcorn Assistant", page_icon="🍿", layout="centered")

mode_visuel = st.sidebar.radio("Mode", ["🎬 Films", "📺 Séries"])
MODE = "movie" if mode_visuel == "🎬 Films" else "tv"

st.title(f"Popcorn Assistant : {mode_visuel}")

current_history = st.session_state.historique_movie if MODE == 'movie' else st.session_state.historique_tv
current_service = movie_service if MODE == 'movie' else tv_service

tab_recherche, tab_trends, tab_recos, tab_historique = st.tabs([
    "🔍 Recherche", "🔥 Tendances", "✨ Pour toi", "📜 Historique"
])

# --- TAB 1 : RECHERCHE ---
with tab_recherche:
    query = st.text_input(f"Rechercher {mode_visuel}...", key="search_input")
    if query:
        try:
            raw = current_service.search(query)
            results = get_safe_list(raw)
            if not results: st.warning("Rien trouvé.")
            else:
                for r in results[:3]:
                    titre = getattr(r, 'title', getattr(r, 'name', 'Inconnu'))
                    mid = getattr(r, 'id', None)
                    vote = getattr(r, 'vote_average', 0)
                    date_raw = getattr(r, 'release_date', getattr(r, 'first_air_date', ''))
                    annee = str(date_raw)[:4] if date_raw else "????"
                    overview = getattr(r, 'overview', '')

                    if mid:
                        col1, col2 = st.columns([3, 1])
                        with col1: st.write(f"**{titre}** ({annee})")
                        with col2: st.button("Ajouter", key=f"add_{mid}", on_click=callback_ajouter, args=(mid, titre, vote, MODE))
                        
                        plats = get_providers_direct(mid, MODE)
                        if plats: st.info(f"📺 **{', '.join(plats[:2])}**")
                        
                        if MODE == 'movie':
                            url_seances = f"https://www.allocine.fr/recherche/?q={titre.replace(' ', '+')}"
                            st.link_button("🎟️ Séances", url_seances)

                        if overview or mid:
                            with st.expander("🎥 Résumé & Trailer"):
                                if overview: st.write(f"_{overview}_")
                                vid = get_trailer(mid, MODE)
                                if vid: st.video(vid)
                        st.divider()
        except Exception as e: st.error(f"Erreur: {e}")

# --- TAB 2 : TENDANCES ---
with tab_trends:
    try:
        raw_list = []
        if MODE == 'movie':
            today = datetime.date.today()
            start = today - datetime.timedelta(days=21)
            end = today + datetime.timedelta(days=14)
            raw_list = discover.discover_movies({
                'release_date.gte': start.strftime('%Y-%m-%d'),
                'release_date.lte': end.strftime('%Y-%m-%d'),
                'with_genres': "28|12|35|53|878|36",
                'sort_by': 'popularity.desc'
            })
        else:
            raw_list = tv_service.popular()

        safe_list = get_safe_list(raw_list)
        ids_vus = [m['id'] for m in current_history]
        compteur = 0

        for f in safe_list:
            mid = getattr(f, 'id', None)
            if not mid or str(mid) in ids_vus: continue
            
            compteur += 1
            titre = getattr(f, 'title', getattr(f, 'name', 'Inconnu'))
            vote = getattr(f, 'vote_average', 0)
            poster = getattr(f, 'poster_path', None)
            date_raw = getattr(f, 'release_date', getattr(f, 'first_air_date', '????'))
            overview = getattr(f, 'overview', '')

            col1, col2 = st.columns([1, 2])
            with col1:
                if poster: st.image(f"https://image.tmdb.org/t/p/w500{poster}")
                else: st.markdown("📺")
            with col2:
                st.markdown(f"**{titre}**")
                st.caption(f"📅 {date_raw} | ⭐ {vote}/10")
                if MODE == 'movie':
                    st.link_button("🎟️ Pathé Annecy", "https://www.pathe.fr/cinemas/cinema-pathe-annecy")
                st.button("Vu", key=f"saw_{mid}", on_click=callback_ajouter, args=(mid, titre, vote, MODE))
            
            with st.expander("🎥 Infos"):
                if overview: st.write(f"_{overview}_")
                vid = get_trailer(mid, MODE)
                if vid: st.video(vid)

            st.divider()
            if compteur >= 10: break
    except Exception as e: st.error(f"Erreur tendances: {e}")

# --- TAB 3 : RECOMMANDATIONS ---
with tab_recos:
    likes = [m for m in current_history if m['avis'] == 'Aimé']
    
    if likes:
        last = likes[-1]
        st.subheader(f"Parce que tu as aimé '{last['title']}'")
        try:
            if MODE == 'movie':
                raw_recos = movie_service.recommendations(movie_id=last['id'])
            else:
                raw_recos = tv_service.recommendations(tv_id=last['id'])
                
            recos = get_safe_list(raw_recos)
            
            if recos:
                cols = st.columns(2)
                for i in range(min(4, len(recos))):
                    r = recos[i]
                    titre = getattr(r, 'title', getattr(r, 'name', ''))
                    mid = getattr(r, 'id', None)
                    poster = getattr(r, 'poster_path', None)
                    overview = getattr(r, 'overview', '')
                    
                    with cols[i % 2]:
                        if poster: st.image(f"https://image.tmdb.org/t/p/w500{poster}")
                        st.caption(f"**{titre}**")
                        
                        if mid:
                            plats = get_providers_direct(mid, MODE)
                            if plats: st.info(f"📺 {', '.join(plats[:2])}")
                            
                            with st.expander("ℹ️"):
                                if overview: st.caption(overview[:150] + "...")
                                vid = get_trailer(mid, MODE)
                                if vid: st.video(vid)
                            
                            if st.button("➕ Vu", key=f"rec_add_{mid}"):
                                vote = getattr(r, 'vote_average', 0)
                                callback_ajouter(mid, titre, vote, MODE)
                                st.rerun()
                        st.divider()
        except Exception as e: st.write(f"Pas de recos dispos ({e})")
    else:
        st.info(f"Ajoute des {mode_visuel} 'Aimés' pour avoir des recos !")

# --- TAB 4 : HISTORIQUE + BACKUP ---
with tab_historique:
    st.subheader(f"💾 Sauvegarde & Restauration")
    st.caption("Télécharge ton historique pour ne pas le perdre.")
    
    # Création du texte de backup pour le mode actuel
    txt_backup = generer_backup(current_history)
    nom_fichier = f"backup_films.txt" if MODE == 'movie' else f"backup_series.txt"
    
    st.download_button(
        label=f"📥 Télécharger mon historique ({mode_visuel})",
        data=txt_backup,
        file_name=nom_fichier,
        mime="text/plain"
    )
    st.divider()

    if current_history:
        st.write(f"**{len(current_history)}** {mode_visuel} vus.")
        for media in reversed(current_history):
            with st.expander(f"{media['title']} — ⭐ {media['vote']}/10"):
                c1, c2 = st.columns([3, 1])
                with c1:
                    opts = ["Aimé", "Bof"]
                    idx = opts.index(media['avis']) if media['avis'] in opts else 0
                    new_avis = st.radio("Avis", opts, index=idx, key=f"rad_{media['id']}", horizontal=True)
                    if new_avis != media['avis']:
                        callback_modifier_avis(media['id'], new_avis, MODE)
                with c2:
                    st.button("🗑️", key=f"del_{media['id']}", on_click=callback_supprimer, args=(media['id'], MODE))
        
        st.divider()
        if st.button("⚠️ Tout effacer (Irréversible)", key="clear_all"): callback_vider(MODE)
    else:
        st.info("Historique vide.")
