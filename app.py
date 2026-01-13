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

# --- FONCTIONS UTILITAIRES ---
def get_safe_list(api_response):
    """Nettoie la réponse API"""
    try:
        if hasattr(api_response, 'results'): data = api_response.results
        elif isinstance(api_response, dict) and 'results' in api_response: data = api_response['results']
        else: data = api_response
        clean_list = list(data)
        if clean_list and isinstance(clean_list[0], str): return []
        return clean_list
    except: return []

def get_trailer(movie_id):
    """Récupère le lien YouTube de la bande-annonce"""
    try:
        # On demande les vidéos associées au film
        videos = movie_service.videos(movie_id)
        # On cherche une vidéo de type "Trailer" sur "YouTube"
        for v in videos:
            if getattr(v, 'site', '') == "YouTube" and getattr(v, 'type', '') == "Trailer":
                return f"https://www.youtube.com/watch?v={v.key}"
        # Si pas de trailer, on cherche un "Teaser"
        for v in videos:
            if getattr(v, 'site', '') == "YouTube":
                return f"https://www.youtube.com/watch?v={v.key}"
    except:
        return None
    return None

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
        clean_results = get_safe_list(movie_service.search(search_query))
        if not clean_results: st.warning("Aucun film trouvé.")
        else:
            for r in clean_results[:3]:
                # Extraction des données
                titre = getattr(r, 'title', r.get('title', 'Inconnu')) if hasattr(r, 'title') or isinstance(r, dict) else 'Inconnu'
                m_id = getattr(r, 'id', r.get('id')) if hasattr(r, 'id') or isinstance(r, dict) else None
                vote = getattr(r, 'vote_average', r.get('vote_average', 0)) if hasattr(r, 'vote_average') or isinstance(r, dict) else 0
                annee = str(getattr(r, 'release_date', r.get('release_date', '')))[0:4]
                overview = getattr(r, 'overview', r.get('overview', 'Pas de résumé.')) if hasattr(r, 'overview') or isinstance(r, dict) else ''

                if m_id:
                    col1, col2 = st.columns([3, 1])
                    with col1: st.write(f"**{titre}** ({annee})")
                    with col2: st.button("Ajouter", key=f"btn_{m_id}", on_click=callback_ajouter_film, args=(m_id, titre, vote))
                    
                    # Pitch + Trailer
                    with st.expander(f"ℹ️ Résumé & Bande-annonce de {titre}"):
                        if overview: st.write(f"_{overview}_")
                        trailer_url = get_trailer(m_id)
                        if trailer_url: st.video(trailer_url)
                        else: st.caption("Pas de bande-annonce trouvée.")

    except Exception as e: st.error(f"Erreur : {e}")

st.divider()

# --- SECTION 2 : A L'AFFICHE ---
st.subheader("🗓️ À l'affiche (Sélection Populaire)")
try:
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=21)
    end_date = today + datetime.timedelta(days=14)
    # Action|Aventure|Comédie|Thriller|SF|Histoire
    genres_cible = "28|12|35|53|878|36"
    
    raw_films = discover.discover_movies({
        'release_date.gte': start_date.strftime('%Y-%m-%d'),
        'release_date.lte': end_date.strftime('%Y-%m-%d'),
        'with_genres': genres_cible, 
        'sort_by': 'popularity.desc'
    })

    liste_films = get_safe_list(raw_films)
    ids_vus = [m['id'] for m in st.session_state.historique]
    compteur = 0

    if not liste_films:
        st.info("Aucun film correspondant à tes genres pour le moment.")
    else:
        for f in liste_films:
            m_id = getattr(f, 'id', f.get('id')) if hasattr(f, 'id') or isinstance(f, dict) else None
            if not m_id or str(m_id) in ids_vus: continue
            
            compteur += 1
            # Extraction des données
            vote_f = getattr(f, 'vote_average', f.get('vote_average', 0)) if hasattr(f, 'vote_average') or isinstance(f, dict) else 0
            titre = getattr(f, 'title', f.get('title', 'Sans titre')) if hasattr(f, 'title') or isinstance(f, dict) else 'Sans titre'
            path = getattr(f, 'poster_path', f.get('poster_path')) if hasattr(f, 'poster_path') or isinstance(f, dict) else None
            date_sortie = getattr(f, 'release_date', f.get('release_date', '????')) if hasattr(f, 'release_date') or isinstance(f, dict) else '????'
            overview = getattr(f, 'overview', f.get('overview', 'Pas de résumé.')) if hasattr(f, 'overview') or isinstance(f, dict) else ''

            col1, col2 = st.columns([1, 2])
            with col1:
                if path: st.image(f"https://image.tmdb.org/t/p/w500{path}")
                else: st.markdown("🎬")
            with col2:
                st.markdown(f"**{titre}**")
                st.caption(f"Sortie : {date_sortie} | ⭐ {vote_f}/10")
                st.button("J'ai vu", key=f"saw_{m_id}", on_click=callback_ajouter_film, args=(m_id, titre, vote_f))
            
            # Pitch + Trailer (Dans un expander pour gagner de la place)
            with st.expander(f"🎥 Voir résumé et bande-annonce"):
                if overview: st.write(f"_{overview}_")
                # Attention : ceci ajoute un appel API par film affiché, ça peut ralentir un peu l'affichage
                trailer_url = get_trailer(m_id)
                if trailer_url: st.video(trailer_url)
                else: st.caption("Pas de bande-annonce trouvée.")

            st.divider()
            if compteur >= 10: break 
            
        if compteur == 0: st.info("Tu es à jour sur les gros films du moment !")
except Exception as e:
    st.error(f"Erreur sorties : {e}")

# --- SECTION 3 : RECOMMANDATIONS ---
films_aimes = [m for m in st.session_state.historique if m['avis'] == 'Aimé']
if films_aimes:
    st.subheader(f"✨ Parce que tu as aimé '{films_aimes[-1]['title']}'")
    try:
        raw_recos = movie_service.recommendations(movie_id=films_aimes[-1]['id'])
        recos_list = get_safe_list(raw_recos)
        
        if recos_list:
            cols = st.columns(3)
            for i in range(min(3, len(recos_list))):
                r = recos_list[i]
                titre = getattr(r, 'title', r.get('title')) if hasattr(r, 'title') or isinstance(r, dict) else ''
                path = getattr(r, 'poster_path', r.get('poster_path')) if hasattr(r, 'poster_path') or isinstance(r, dict) else None
                m_id = getattr(r, 'id', r.get('id')) if hasattr(r, 'id') or isinstance(r, dict) else None
                
                with cols[i]:
                    if path: st.image(f"https://image.tmdb.org/t/p/w500{path}")
                    st.caption(f"{titre}")
                    if m_id:
                        with st.expander("ℹ️"): # Petit bouton infos pour les recos
                            overview = getattr(r, 'overview', r.get('overview', '')) if hasattr(r, 'overview') or isinstance(r, dict) else ''
                            if overview: st.caption(overview[:150] + "...") # Résumé court
    except: pass
st.divider()

# --- SECTION 4 : HISTORIQUE ---
st.subheader("📜 Mon Historique")
if st.session_state.historique:
    for movie in reversed(st.session_state.historique):
        with st.
