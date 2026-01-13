import streamlit as st
from tmdbv3api import TMDb, Movie, Discover, TV
import datetime
import os
import requests 
from io import StringIO

# --- CONFIGURATION TMDb ---
tmdb = TMDb()
API_KEY = '5ccac4fafac407ac28bb55c4fd44fb9c'  
tmdb.api_key = API_KEY
tmdb.language = 'fr'

# Services
movie_service = Movie()
tv_service = TV()
discover = Discover()

# --- GESTION DES FICHIERS (4 Fichiers maintenant !) ---
FILES = {
    "movie_hist": "mes_films.txt",
    "tv_hist": "mes_series.txt",
    "movie_watch": "watchlist_films.txt",
    "tv_watch": "watchlist_series.txt"
}

# Initialisation des 4 listes en mémoire
keys = ['hist_movie', 'hist_tv', 'watch_movie', 'watch_tv']
for k in keys:
    if k not in st.session_state: st.session_state[k] = []

def charger_donnees(key_type, file_path):
    """Charge un fichier texte dans une liste"""
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

def sauvegarder_donnees(file_path, data_list):
    """Sauvegarde une liste dans un fichier"""
    with open(file_path, "w", encoding="utf-8") as f:
        for m in data_list:
            f.write(f"{m['id']}|{m['title']}|{m['vote']}|{m['avis']}\n")

def importer_backup(uploaded_file, target_list_key, file_key):
    """Importe et fusionne un fichier uploadé"""
    if uploaded_file is not None:
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        count = 0
        current_ids = [m['id'] for m in st.session_state[target_list_key]]
        
        for line in stringio:
            l = line.strip().split("|")
            if len(l) >= 2:
                mid = l[0]
                # On évite les doublons
                if mid not in current_ids:
                    st.session_state[target_list_key].append({
                        'id': l[0], 'title': l[1], 
                        'vote': l[2] if len(l) > 2 else "0.0", 
                        'avis': l[3] if len(l) > 3 else "Aimé"
                    })
                    current_ids.append(mid)
                    count += 1
        
        # Sauvegarde immédiate
        sauvegarder_donnees(FILES[file_key], st.session_state[target_list_key])
        return count
    return 0

# Chargement au démarrage
st.session_state['hist_movie'] = charger_donnees('hist_movie', FILES['movie_hist'])
st.session_state['hist_tv'] = charger_donnees('hist_tv', FILES['tv_hist'])
st.session_state['watch_movie'] = charger_donnees('watch_movie', FILES['movie_watch'])
st.session_state['watch_tv'] = charger_donnees('watch_tv', FILES['tv_watch'])

# --- FONCTIONS API ---
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
def action_add_history(mid, title, vote, mode):
    key = f"hist_{mode}"
    file_key = f"{mode}_hist"
    if not any(m['id'] == str(mid) for m in st.session_state[key]):
        st.session_state[key].append({'id': str(mid), 'title': title, 'vote': str(vote), 'avis': 'Aimé'})
        sauvegarder_donnees(FILES[file_key], st.session_state[key])
        st.toast(f"✅ {title} ajouté à l'historique !")

def action_add_watchlist(mid, title, vote, mode):
    key = f"watch_{mode}"
    file_key = f"{mode}_watch"
    # On vérifie si pas déjà dans watchlist ET pas déjà dans historique
    already_seen = any(m['id'] == str(mid) for m in st.session_state[f"hist_{mode}"])
    already_watch = any(m['id'] == str(mid) for m in st.session_state[key])
    
    if not already_watch and not already_seen:
        st.session_state[key].append({'id': str(mid), 'title': title, 'vote': str(vote), 'avis': 'A voir'})
        sauvegarder_donnees(FILES[file_key], st.session_state[key])
        st.toast(f"👀 {title} ajouté à la liste !")
    elif already_seen:
        st.toast("⚠️ Déjà vu !")
    else:
        st.toast("⚠️ Déjà dans la liste !")

def action_move_watch_to_hist(mid, title, vote, mode):
    # 1. Ajouter à l'historique
    action_add_history(mid, title, vote, mode)
    # 2. Retirer de la watchlist
    action_remove(mid, mode, is_watchlist=True)
    st.rerun()

def action_remove(mid, mode, is_watchlist=False):
    key = f"watch_{mode}" if is_watchlist else f"hist_{mode}"
    file_key = f"{mode}_watch" if is_watchlist else f"{mode}_hist"
    
    st.session_state[key] = [m for m in st.session_state[key] if m['id'] != str(mid)]
    sauvegarder_donnees(FILES[file_key], st.session_state[key])
    st.toast("🗑️ Retiré")

def action_modifier_avis(mid, new_avis, mode):
    key = f"hist_{mode}"
    file_key = f"{mode}_hist"
    for m in st.session_state[key]:
        if m['id'] == str(mid):
            m['avis'] = new_avis
            break
    sauvegarder_donnees(FILES[file_key], st.session_state[key])
    st.rerun()

# --- INTERFACE ---
st.set_page_config(page_title="Popcorn Assistant", page_icon="🍿", layout="centered")

mode_visuel = st.sidebar.radio("Mode", ["🎬 Films", "📺 Séries"])
MODE = "movie" if mode_visuel == "🎬 Films" else "tv"

st.title(f"Popcorn Assistant : {mode_visuel}")

current_service = movie_service if MODE == 'movie' else tv_service
hist_key = f"hist_{MODE}"
watch_key = f"watch_{MODE}"

tab_recherche, tab_trends, tab_watchlist, tab_recos, tab_historique = st.tabs([
    "🔍 Recherche", "🔥 Tendances", "📋 Ma Liste", "✨ Pour toi", "📜 Historique"
])

# --- TAB 1 : RECHERCHE ---
with tab_recherche:
    query = st.text_input(f"Rechercher {mode_visuel}...", key="search_input")
    if query:
        try:
            results = get_safe_list(current_service.search(query))
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
                        with col2: 
                            # Double Bouton : Vu ou À voir
                            c_vu, c_voir = st.columns(2)
                            with c_vu: st.button("✅", key=f"add_h_{mid}", on_click=action_add_history, args=(mid, titre, vote, MODE), help="Marquer comme Vu")
                            with c_voir: st.button("👀", key=f"add_w_{mid}", on_click=action_add_watchlist, args=(mid, titre, vote, MODE), help="Ajouter à Ma Liste")

                        plats = get_providers_direct(mid, MODE)
                        if plats: st.info(f"📺 **{', '.join(plats[:2])}**")
                        
                        if MODE == 'movie':
                            url_seances = f"https://www.allocine.fr/recherche/?q={titre.replace(' ', '+')}"
                            st.link_button("🎟️ Séances", url_seances)

                        if overview or mid:
                            with st.expander("🎥 Infos"):
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
        ids_vus = [m['id'] for m in st.session_state[hist_key]]
        ids_watch = [m['id'] for m in st.session_state[watch_key]]
        compteur = 0

        for f in safe_list:
            mid = getattr(f, 'id', None)
            # On n'affiche pas ceux déjà vus
            if not mid or str(mid) in ids_vus: continue
            
            compteur += 1
            titre = getattr(f, 'title', getattr(f, 'name', 'Inconnu'))
            vote = getattr(f, 'vote_average', 0)
            poster = getattr(f, 'poster_path', None)
            date_raw = getattr(f, 'release_date', getattr(f, 'first_air_date', '????'))

            col1, col2 = st.columns([1, 2])
            with col1:
                if poster: st.image(f"https://image.tmdb.org/t/p/w500{poster}")
                else: st.markdown("📺")
            with col2:
                st.markdown(f"**{titre}**")
                st.caption(f"📅 {date_raw} | ⭐ {vote}/10")
                
                c_a, c_b = st.columns(2)
                with c_a: st.button("✅ Vu", key=f"tr_vu_{mid}", on_click=action_add_history, args=(mid, titre, vote, MODE))
                with c_b: 
                    # Si déjà dans watchlist, on désactive
                    if str(mid) in ids_watch: st.caption("Déjà listé")
                    else: st.button("👀 +", key=f"tr_w_{mid}", on_click=action_add_watchlist, args=(mid, titre, vote, MODE))

            st.divider()
            if compteur >= 10: break
    except Exception as e: st.error(f"Erreur tendances: {e}")

# --- TAB 3 : MA LISTE (WATCHLIST) ---
with tab_watchlist:
    watchlist = st.session_state[watch_key]
    if watchlist:
        st.write(f"Tu as **{len(watchlist)}** {mode_visuel} à voir.")
        for media in watchlist:
            with st.container():
                c1, c2, c3 = st.columns([3, 1, 1])
                with c1: 
                    st.write(f"**{media['title']}**")
                    # On affiche le streaming ici aussi, c'est utile pour la watchlist
                    p = get_providers_direct(media['id'], MODE)
                    if p: st.caption(f"Sur : {', '.join(p[:2])}")
                
                with c2: st.button("✅ Vu", key=f"w_to_h_{media['id']}", on_click=action_move_watch_to_hist, args=(media['id'], media['title'], media['vote'], MODE))
                with c3: st.button("🗑️", key=f"w_del_{media['id']}", on_click=action_remove, args=(media['id'], MODE, True))
                st.divider()
    else:
        st.info("Ta liste est vide. Ajoute des films depuis la Recherche ou les Tendances !")

# --- TAB 4 : POUR TOI ---
with tab_recos:
    likes = [m for m in st.session_state[hist_key] if m['avis'] == 'Aimé']
    if likes:
        last = likes[-1]
        st.subheader(f"Parce que tu as aimé '{last['title']}'")
        try:
            if MODE == 'movie': raw_recos = movie_service.recommendations(movie_id=last['id'])
            else: raw_recos = tv_service.recommendations(tv_id=last['id'])
            recos = get_safe_list(raw_recos)
            
            if recos:
                cols = st.columns(2)
                for i in range(min(4, len(recos))):
                    r = recos[i]
                    titre = getattr(r, 'title', getattr(r, 'name', ''))
                    mid = getattr(r, 'id', None)
                    poster = getattr(r, 'poster_path', None)
                    vote = getattr(r, 'vote_average', 0)
                    
                    with cols[i % 2]:
                        if poster: st.image(f"https://image.tmdb.org/t/p/w500{poster}")
                        st.caption(f"**{titre}**")
                        if mid:
                            p = get_providers_direct(mid, MODE)
                            if p: st.info(f"📺 {', '.join(p[:2])}")
                            
                            c_a, c_b = st.columns(2)
                            with c_a: st.button("✅", key=f"rec_vu_{mid}", on_click=action_add_history, args=(mid, titre, vote, MODE))
                            with c_b: st.button("👀", key=f"rec_w_{mid}", on_click=action_add_watchlist, args=(mid, titre, vote, MODE))
                        st.divider()
        except: pass
    else:
        st.info("Ajoute des titres 'Aimés' pour avoir des recos.")

# --- TAB 5 : HISTORIQUE + IMPORT/EXPORT ---
with tab_historique:
    st.subheader("💾 Gestion des données")
    
    # EXPORT
    txt_backup = "\n".join([f"{m['id']}|{m['title']}|{m['vote']}|{m['avis']}" for m in st.session_state[hist_key]])
    nom_fichier = f"backup_{MODE}.txt"
    st.download_button(f"📥 Télécharger l'historique {mode_visuel}", data=txt_backup, file_name=nom_fichier, mime="text/plain")
    
    # IMPORT
    st.caption("Restaurer un backup (fusionne avec la liste actuelle)")
    uploaded_file = st.file_uploader("Choisir un fichier .txt", type="txt", key=f"upl_{MODE}")
    if uploaded_file:
        file_key = f"{MODE}_hist"
        if st.button("Importer maintenant"):
            nb = importer_backup(uploaded_file, hist_key, file_key)
            if nb > 0: st.success(f"{nb} éléments importés ! Recharge la page si besoin.")
            else: st.warning("Aucun nouvel élément trouvé ou fichier vide.")

    st.divider()

    # LISTE
    history = st.session_state[hist_key]
    if history:
        st.write(f"**{len(history)}** {mode_visuel} vus.")
        for media in reversed(history):
            with st.expander(f"{media['title']} — ⭐ {media['vote']}/10"):
                c1, c2 = st.columns([3, 1])
                with c1:
                    opts = ["Aimé", "Bof"]
                    idx = opts.index(media['avis']) if media['avis'] in opts else 0
                    new_avis = st.radio("Avis", opts, index=idx, key=f"rad_{media['id']}", horizontal=True)
                    if new_avis != media['avis']:
                        action_modifier_avis(media['id'], new_avis, MODE)
                with c2:
                    st.button("🗑️", key=f"del_{media['id']}", on_click=action_remove, args=(media['id'], MODE, False))
