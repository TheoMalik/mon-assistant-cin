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

# --- FONCTION DE NETTOYAGE RENFORCÉE ---
def get_safe_list(api_response):
    """Transforme n'importe quelle réponse API en une liste Python propre."""
    try:
        # 1. On cherche la liste cachée dans l'attribut .results
        if hasattr(api_response, 'results'):
            data = api_response.results
        # 2. Ou dans la clé ['results'] (si c'est un dictionnaire)
        elif isinstance(api_response, dict) and 'results' in api_response:
            data = api_response['results']
        # 3. Sinon on prend l'objet tel quel
        else:
            data = api_response
            
        # 4. ÉTAPE CRUCIALE : On force la conversion en liste pure
        # Cela "casse" l'enveloppe AsObj qui empêchait le découpage [:3]
        clean_list = list(data)
        
        # 5. Sécurité anti-bug : Si la liste contient des chaînes de texte (ex: 'page', 'total'),
        # c'est qu'on a converti le menu au lieu des films. On annule.
        if clean_list and isinstance(clean_list[0], str):
            return []
            
        return clean_list
    except:
        return []

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
        raw_results = movie_service.search(search_query)
        # On utilise la nouvelle fonction blindée
        clean_results = get_safe_list(raw_results)
        
        if not clean_results:
            st.warning("Aucun film trouvé.")
        else:
            # Maintenant clean_results est une vraie liste, on peut couper [:3] sans peur
            for r in clean_results[:3]:
                # Lecture sécurisée des attributs (compatible dict et objet)
                titre = getattr(r, 'title', r.get('title')) if hasattr(r, 'title') or isinstance(r, dict) else 'Titre Inconnu'
                m_id = getattr(r, 'id', r.get('id')) if hasattr(r, 'id') or isinstance(r, dict) else None
                vote = getattr(r, 'vote_average', r.get('vote_average', 0)) if hasattr(r, 'vote_average') or isinstance(r, dict) else 0
                date_full = getattr(r, 'release_date', r.get('release_date', '')) if hasattr(r, 'release_date') or isinstance(r, dict) else ''
                annee = str(date_full)[:4] if date_full else "????"

                if m_id:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{titre}** ({annee})")
                    with col2:
                        st.button("Ajouter", key=f"btn_{m_id}", on_click=callback_ajouter_film, args=(m_id, titre, vote))
    except Exception as e:
        st.error(f"Erreur technique : {e}")

st.divider()

# --- SECTION 2 : A L'AFFICHE (Ciblé & Populaire) ---
st.subheader("🗓️ À l'affiche (Sélection Populaire)")
try:
    today = datetime.date.today()
    # On garde la fenêtre large qui fonctionne (-3 semaines / +2 semaines)
    start_date = today - datetime.timedelta(days=21)
    end_date = today + datetime.timedelta(days=14)
    
    # Genres : Action(28), Aventure(12), Comédie(35), Thriller(53), SF(878), Histoire(36)
    # J'ai retiré Drame et Animation pour cibler "Blockbusters", dis-moi si tu veux les remettre.
    raw_films = discover.discover_movies({
        'release_date.gte': start_date.strftime('%Y-%m-%d'),
        'release_date.lte': end_date.strftime('%Y-%m-%d'),
        'with_genres': "28,12,35,53,878,36", 
        'sort_by': 'popularity.desc'
    })

    liste_films = get_safe_list(raw_films)
    ids_vus = [m['id'] for m in st.session_state.historique]
    compteur = 0

    if not liste_films:
        st.info("Aucun film correspondant à tes genres pour le moment.")
    else:
        for f in liste_films:
            # Sécurités habituelles
            m_id = getattr(f, 'id', f.get('id')) if hasattr(f, 'id') or isinstance(f, dict) else None
            if not m_id or str(m_id) in ids_vus: continue
            
            compteur += 1
            col1, col2 = st.columns([1, 2])
            
            # Données
            vote_f = getattr(f, 'vote_average', f.get('vote_average', 0)) if hasattr(f, 'vote_average') or isinstance(f, dict) else 0
            titre = getattr(f, 'title', f.get('title', 'Sans titre')) if hasattr(f, 'title') or isinstance(f, dict) else 'Sans titre'
            path = getattr(f, 'poster_path', f.get('poster_path')) if hasattr(f, 'poster_path') or isinstance(f, dict) else None
            date_sortie = getattr(f, 'release_date', f.get('release_date', '????')) if hasattr(f, 'release_date') or isinstance(f, dict) else '????'

            with col1:
                if path: st.image(f"https://image.tmdb.org/t/p/w500{path}")
                else: st.markdown("🎬")
            with col2:
                st.markdown(f"**{titre}**")
                st.caption(f"Sortie : {date_sortie} | ⭐ {vote_f}/10")
                st.button("J'ai vu", key=f"saw_{m_id}", on_click=callback_ajouter_film, args=(m_id, titre, vote_f))
            
            st.divider()
            if compteur >= 10: break # Top 10 des résultats
            
        if compteur == 0:
            st.info("Tu es à jour sur les gros films du moment !")

except Exception as e:
    st.error(f"Erreur technique : {e}")
    
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
                
                with cols[i]:
                    if path: st.image(f"https://image.tmdb.org/t/p/w500{path}")
                    st.caption(f"{titre}")
    except:
        pass
st.divider()

# --- SECTION 4 : HISTORIQUE ---
st.subheader("📜 Mon Historique & Avis")
if st.session_state.historique:
    for movie in reversed(st.session_state.historique):
        with st.expander(f"{movie['title']} — ⭐ {movie['vote']}/10"):
            col_avis, col_del = st.columns([3, 1])
            with col_avis:
                choix = ["Aimé", "Bof"]
                idx = choix.index(movie['avis']) if movie['avis'] in choix else 0
                nouvel_avis = st.radio("Avis :", choix, index=idx, key=f"rad_{movie['id']}", horizontal=True)
                if nouvel_avis != movie['avis']:
                    callback_modifier_avis(movie['id'], nouvel_avis)
            with col_del:
                st.button("Supprimer", key=f"del_{movie['id']}", on_click=callback_supprimer_film, args=(movie['id'],))
    
    if st.button("🗑️ Tout effacer", key="clear_all"):
        callback_vider_tout()
else:
    st.info("Ton historique est vide.")
