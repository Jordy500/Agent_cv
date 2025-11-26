import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
import sys

# Ajouter le dossier utils au path
sys.path.insert(0, str(Path(__file__).parent / "utils"))
from data_loader import calculate_dashboard_metrics, get_matching_jobs, load_cv_data, get_user_by_name, load_notification_history, format_notification_time, load_job_offers
from state_store import load_user_state, save_user_state
from job_scanner import run_job_scan
from cv_uploader import save_and_analyze_cv
from profile_saver import save_user_profile
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from agents.job_offer_analyzer import JobOfferAnalyzer

# Configuration de la page
st.set_page_config(
    page_title="Smart Agent - Job Matcher",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Charger le CSS personnalisé
def load_css():
    css_file = Path(__file__).parent / "assets" / "style.css"
    if css_file.exists():
        with open(css_file) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# Initialiser la session state
if 'page' not in st.session_state:
    st.session_state.page = 'landing'
if 'current_user' not in st.session_state:
    st.session_state.current_user = 'Jordy'  # Utilisateur par défaut

# Fonction pour changer de page
def go_to_dashboard():
    st.session_state.page = 'dashboard'
    st.rerun()

# Page d'accueil avec la boule jaune
if st.session_state.page == 'landing':
    # Masquer le menu et le footer Streamlit
    hide_streamlit_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stDeployButton {display:none;}
        
        /* Fond noir plein écran */
        .stApp {
            background-color: #000000 !important;
        }
        
        /* Supprimer tous les paddings */
        .main .block-container {
            padding: 0 !important;
            max-width: 100% !important;
        }
        
        section.main > div {
            padding: 0 !important;
        }
        
        /* Animation pulse */
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.02); }
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        /* Centrage absolu du bouton */
        div[data-testid="stButton"] {
            position: fixed !important;
            top: 50% !important;
            left: 50% !important;
            margin-left: -150px !important;
            margin-top: -150px !important;
            z-index: 100 !important;
        }
        
        div[data-testid="stButton"] button {
            width: 300px !important;
            height: 300px !important;
            background: radial-gradient(circle at 30% 30%, #E6C200 0%, #D4AF37 30%, #C4A000 70%, #B8860B 100%) !important;
            border-radius: 50% !important;
            border: none !important;
            box-shadow: 
                inset -10px -10px 30px rgba(0, 0, 0, 0.4),
                inset 10px 10px 30px rgba(255, 255, 255, 0.2),
                0 20px 60px rgba(212, 175, 55, 0.4),
                0 40px 30px -20px rgba(0, 0, 0, 0.5) !important;
            animation: pulse 2s infinite !important;
            cursor: pointer !important;
            font-size: 38px !important;
            font-weight: bold !important;
            color: #FFFFFF !important;
            text-shadow: 2px 2px 8px rgba(0, 0, 0, 0.6) !important;
            padding: 0 !important;
            line-height: 1.2 !important;
            position: relative !important;
        }
        
        div[data-testid="stButton"] button::before {
            content: '';
            position: absolute;
            top: 10%;
            left: 15%;
            width: 40%;
            height: 40%;
            background: radial-gradient(circle, rgba(255, 255, 255, 0.2) 0%, transparent 60%);
            border-radius: 50%;
            filter: blur(10px);
        }
        
        div[data-testid="stButton"] button:hover {
            transform: scale(1.05) !important;
            box-shadow: 
                inset -10px -10px 30px rgba(0, 0, 0, 0.5),
                inset 10px 10px 30px rgba(255, 255, 255, 0.25),
                0 25px 80px rgba(212, 175, 55, 0.5),
                0 45px 35px -25px rgba(0, 0, 0, 0.6) !important;
        }
        
        div[data-testid="stButton"] button:focus {
            outline: none !important;
            box-shadow: 
                inset -10px -10px 30px rgba(0, 0, 0, 0.5),
                inset 10px 10px 30px rgba(255, 255, 255, 0.25),
                0 25px 80px rgba(212, 175, 55, 0.5),
                0 45px 35px -25px rgba(0, 0, 0, 0.6) !important;
        }
        
        /* Texte invitation - centré en bas */
        .invite-text {
            position: fixed;
            bottom: 25%;
            left: 50%;
            transform: translateX(-50%);
            text-align: center;
            font-size: 20px;
            color: #999;
            animation: fadeIn 2s ease-in;
            z-index: 50;
        }
        </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    
    # Bouton boule cliquable
    if st.button("SMART\nAGENT", key="sphere-btn"):
        go_to_dashboard()
    
    # Texte en dessous
    st.markdown('<div class="invite-text">Cliquez pour commencer</div>', unsafe_allow_html=True)

# Dashboard principal
elif st.session_state.page == 'dashboard':
    # Charger le script de gestion de la sidebar
    sidebar_html = Path(__file__).parent / "sidebar_handler.html"
    if sidebar_html.exists():
        with open(sidebar_html) as f:
            components.html(f.read(), height=0)
    
    # CSS global pour la sidebar
    st.markdown("""
    <style>
    /* Masquer la barre noire supérieure et le bouton deploy */
    header[data-testid="stHeader"] { display: none !important; }
    .stDeployButton { display: none !important; }
    
    /* Sidebar - styles de base */
    section[data-testid="stSidebar"] {
        background: rgba(30, 30, 40, 0.95) !important;
        backdrop-filter: blur(10px) !important;
    }
    
    section[data-testid="stSidebar"] > div {
        background: transparent !important;
    }
    
    /* Boutons de navigation style rectangulaire */
    div[data-testid="stRadio"] > div {
        gap: 10px !important;
    }
    
    div[data-testid="stRadio"] label {
        background: rgba(255, 255, 255, 0.1) !important;
        padding: 12px 20px !important;
        border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        transition: all 0.3s ease !important;
        cursor: pointer !important;
        color: white !important;
        font-weight: 500 !important;
    }
    
    div[data-testid="stRadio"] label:hover {
        background: rgba(255, 255, 255, 0.2) !important;
        border-color: rgba(230, 194, 0, 0.5) !important;
    }
    
    /* Bouton sélectionné */
    div[data-testid="stRadio"] label:has(input:checked) {
        background: linear-gradient(135deg, #E6C200 0%, #D4AF37 100%) !important;
        border-color: #D4AF37 !important;
        box-shadow: 0 4px 15px rgba(230, 194, 0, 0.3) !important;
    }
    
    /* Style du bouton retour */
    .stButton button {
        background: rgba(255, 255, 255, 0.1) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 8px !important;
        padding: 12px 20px !important;
        font-weight: 500 !important;
        width: 100% !important;
    }
    
    .stButton button:hover {
        background: rgba(255, 255, 255, 0.2) !important;
        border-color: rgba(230, 194, 0, 0.5) !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Titre principal
    st.markdown("<h1 style='text-align: center;'>Smart Agent</h1>", unsafe_allow_html=True)
    
    # Sidebar avec navigation
    with st.sidebar:
        page_selection = st.radio("Navigation", ["Accueil", "Mon Profil", "Mes Offres"], label_visibility="collapsed")
        # Sélecteur de profil actif basé sur cv_data.json
        try:
            names_list = [cv.get('name','') for cv in load_cv_data() if cv.get('name')]
            names_list = sorted(list({n for n in names_list if n}))
        except Exception:
            names_list = []
        current_user = st.session_state.get('current_user', 'Jordy')
        if names_list:
            selected_user = st.selectbox("Profil actif", names_list, index=names_list.index(current_user) if current_user in names_list else 0)
            if selected_user != current_user:
                st.session_state.current_user = selected_user
                st.rerun()
        else:
            st.caption("Aucun profil trouvé. Saisissez un nom puis téléversez un CV.")
            new_name = st.text_input("Nom du profil", value=current_user or "Utilisateur")
            if st.button("Utiliser ce nom"):
                st.session_state.current_user = new_name.strip() or "Utilisateur"
                st.rerun()
        
        # Spacer pour pousser le bouton en bas
        st.markdown("<div style='height: calc(100vh - 300px);'></div>", unsafe_allow_html=True)
        
        if st.button("Retour à l'accueil", use_container_width=True):
            st.session_state.page = 'landing'
            st.rerun()
    
    # PAGE ACCUEIL - Fond dégradé bleu-rouge
    if page_selection == "Accueil":
        st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(135deg, #2C3E50 0%, #34495E 25%, #3498DB 50%, #E67E22 75%, #E74C3C 100%) !important;
        }
        
        /* Texte en blanc pour contraste sur fond sombre */
        .stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp label, .stApp div[data-testid="stMarkdownContainer"] {
            color: white !important;
        }
        
        /* Métriques avec fond semi-transparent */
        div[data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.1) !important;
            padding: 15px !important;
            border-radius: 10px !important;
            backdrop-filter: blur(10px) !important;
        }
        
        div[data-testid="stMetric"] label {
            color: white !important;
        }
        
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
            color: white !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.header("Tableau de Bord")
        
        # Charger les données du profil actif
        current_user = st.session_state.get('current_user', 'Jordy')
        user_data = get_user_by_name(current_user)
        cv_data_list = load_cv_data()
        jordy_cv = next((cv for cv in cv_data_list if cv.get('name') == current_user), None)
        
        # Calculer les métriques pour Jordy
        if jordy_cv:
            user_skills = jordy_cv.get('analysis', {}).get('skills', [])
            matched_jobs = get_matching_jobs(user_skills, min_match_percentage=0)
            avg_score = round(sum(j['match_percentage'] for j in matched_jobs) / len(matched_jobs)) if matched_jobs else 0
        else:
            matched_jobs = []
            avg_score = 0
        
        # Métriques personnelles
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Emails Reçus", "12", "+2")
        with col2:
            st.metric("Offres Matchées", len(matched_jobs), "+3")
        with col3:
            st.metric("Score Moyen", f"{avg_score}%", "+5%")
        with col4:
            st.metric("Profil", "Actif", "")
        
        st.divider()
        
        st.subheader("Dernières Notifications")
        
        # Charger l'historique des notifications pour l'utilisateur actif
        notif_email = None
        if jordy_cv:
            notif_email = jordy_cv.get('email')
        if not notif_email and user_data:
            notif_email = user_data.get('email')
        notifications = load_notification_history(user_email=notif_email, limit=5)
        
        if notifications:
            for notif in notifications:
                timestamp = notif.get('timestamp', '')
                job_count = notif.get('job_count', 0)
                status = notif.get('status', 'success')
                
                # Formater le temps relatif
                time_str = format_notification_time(timestamp)
                
                # Icône selon le statut
                icon = "✅" if status == "success" else "❌"
                
                # Afficher dans un conteneur stylisé
                st.markdown(f"""
                <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid {'#10B981' if status == 'success' else '#EF4444'};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-size: 14px; color: #E5E7EB;">{icon} <b>{job_count}</b> offre{'s' if job_count > 1 else ''} envoyée{'s' if job_count > 1 else ''}</span>
                        </div>
                        <div style="font-size: 12px; color: #9CA3AF;">{time_str}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Aucune notification récente. Lancez un scan pour trouver des offres !")
        
        # Bouton de scan avec gestion d'état
        if 'scanning' not in st.session_state:
            st.session_state.scanning = False
        
        if st.button("Lancer un Scan d'Offres", use_container_width=True, disabled=st.session_state.scanning):
            st.session_state.scanning = True
            with st.spinner("Scan en cours... Cela peut prendre jusqu'à 2 minutes."):
                success, message = run_job_scan()
                
                if success:
                    st.success(message)
                else:
                    st.error(message)
            
            st.session_state.scanning = False
            st.rerun()
    
    # PAGE MON PROFIL - Fond dégradé violet-bleu
    elif page_selection == "Mon Profil":
        st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(135deg, #4A5568 0%, #5A67D8 30%, #667EEA 60%, #9F7AEA 100%) !important;
        }
        
        /* Texte en blanc pour contraste sur fond sombre */
        .stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp label, .stApp div[data-testid="stMarkdownContainer"] {
            color: white !important;
        }
        
        /* Inputs avec texte visible */
        .stApp input {
            background: rgba(255, 255, 255, 0.9) !important;
            color: #333 !important;
        }
        
        .stApp select {
            background: rgba(255, 255, 255, 0.9) !important;
            color: #333 !important;
        }
        
        .profile-circle {
            width: 150px;
            height: 150px;
            border-radius: 50%;
            background: linear-gradient(135deg, #E6C200 0%, #D4AF37 30%, #C4A000 70%, #B8860B 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 20px;
            box-shadow: 
                inset -5px -5px 15px rgba(0, 0, 0, 0.3),
                inset 5px 5px 15px rgba(255, 255, 255, 0.2),
                0 10px 30px rgba(0, 0, 0, 0.4);
            font-size: 48px;
            font-weight: bold;
            color: white;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.6);
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.header("Mon Profil")
        
        # Charger les données du profil actif
        current_user = st.session_state.get('current_user', 'Jordy')
        user_data = get_user_by_name(current_user)
        cv_data_list = load_cv_data()
        jordy_cv = next((cv for cv in cv_data_list if cv.get('name') == current_user), None)
        
        # Cercle de profil avec initiales
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            initials = ''.join([part[0].upper() for part in current_user.split() if part])[:2] or 'U'
            st.markdown(f'<div class="profile-circle">{initials}</div>', unsafe_allow_html=True)
        
        # Valeurs par défaut depuis les données
        default_email = jordy_cv.get('email', 'j53276019@gmail.com') if jordy_cv else 'j53276019@gmail.com'
        default_keywords = ", ".join(user_data.get('preferred_jobs', [])) if user_data else "data analyst, data scientist"

        # Informations personnelles et formation gérées automatiquement via l'analyse de CV
        st.info("Les informations personnelles et la formation sont extraites automatiquement de votre CV. Modifiez votre CV pour les mettre à jour.")
        email = default_email
        
        st.divider()
        
        st.subheader("Mon CV")
        
        # Afficher le CV actuel si disponible
        if jordy_cv and jordy_cv.get('path'):
            st.info(f"📄 CV actuel : {Path(jordy_cv['path']).name}")
            
            # Afficher les compétences détectées
            skills = jordy_cv.get('analysis', {}).get('skills', [])
            if skills:
                st.success(f"✨ Compétences détectées : {', '.join(skills)}")
        
        uploaded_file = st.file_uploader("Téléchargez votre CV (PDF)", type=['pdf'])
        
        if uploaded_file is not None:
            if st.button("📤 Analyser ce CV"):
                with st.spinner("Analyse du CV en cours..."):
                    success, message, skills, final_name, final_email = save_and_analyze_cv(uploaded_file, current_user, email)
                    
                    if success:
                        st.success(message)
                        if skills:
                            st.write("**Compétences détectées :**")
                            st.write(", ".join(skills))
                        # Afficher l'email détecté et basculer le profil actif
                        if final_email:
                            st.info(f"Email détecté sur le CV : {final_email}")
                        # Basculer le profil actif sur le nom détecté du CV
                        st.session_state.current_user = final_name
                        st.rerun()
                    else:
                        st.error(message)
        
        st.divider()
        
        st.subheader("Préférences de Recherche")
        col1, col2 = st.columns(2)
        
        with col1:
            keywords = st.text_input("Mots-clés", value=default_keywords)
            location = st.text_input("Localisation recherchée", value="Paris, Île-de-France")
        
        with col2:
            contract_type = st.multiselect("Type de contrat", ["CDI", "CDD", "Stage", "Alternance"], default=["CDI"])
        
        match_score = st.slider("Score de matching minimum (%)", 50, 100, 70)
        
        if st.button("Enregistrer mon profil", use_container_width=True):
            # Préparer les données du profil
            profile_data = {
                'email': email,
                'keywords': [k.strip() for k in keywords.split(',')],
                'location': location,
                'contract_types': contract_type,
                'match_score': match_score,
                'notify_via_email': True
            }
            
            success, message = save_user_profile(current_user, profile_data)
            
            if success:
                st.success(message)
            else:
                st.error(message)
    
    # PAGE MES OFFRES - Fond blanc
    elif page_selection == "Mes Offres":
        st.markdown("""
        <style>
        .stApp {
            background: #FFFFFF !important;
        }
        
        /* Texte en noir pour fond blanc */
        .stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp label, .stApp div[data-testid="stMarkdownContainer"] {
            color: #333 !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.header("Mes Offres d'Emploi")
        
        # Filtres
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_status = st.selectbox("Statut", ["Toutes", "Nouvelles", "Vues", "Favorites"]) 
        with col2:
            filter_score = st.selectbox("Score", ["Tous", ">90%", ">80%", ">70%", ">60%", ">50%"])
        with col3:
            filter_date = st.selectbox("Date", ["Toutes", "Aujourd'hui", "Cette semaine", "Ce mois"])
        
        st.divider()
        
        # Charger les données du profil actif
        current_user = st.session_state.get('current_user', 'Jordy')
        cv_data_list = load_cv_data()
        jordy_cv = next((cv for cv in cv_data_list if cv.get('name') == current_user), None)
        
        if jordy_cv:
            user_skills = jordy_cv.get('analysis', {}).get('skills', [])
            # Charger l'état utilisateur (favoris, vues, masquées)
            user_state = load_user_state(current_user)
            favorites = set(user_state.get('favorites', []))
            viewed = set(user_state.get('viewed', []))
            hidden = set(user_state.get('hidden', []))
            
            # Filtrer par score minimum
            min_score = 0
            if filter_score == ">90%":
                min_score = 90
            elif filter_score == ">80%":
                min_score = 80
            elif filter_score == ">70%":
                min_score = 70
            elif filter_score == ">60%":
                min_score = 60
            elif filter_score == ">50%":
                min_score = 50
            
            # Obtenir les offres correspondantes
            # Charger offres et calculer score ATS
            job_offers = load_job_offers()
            cv_list = [jordy_cv]
            fallback_skills = user_skills
            analyzer = JobOfferAnalyzer(job_offers)
            analyzer.compare_job_offers(cv_skills=fallback_skills, cv_data=cv_list)
            offers_ats = analyzer.analyzed_offers or []

            # Filtrer par score sélectionné
            def offer_id(job: dict) -> str:
                return job.get('url') or f"{job.get('title','')}::{job.get('company','')}"

            def percent_ats(job: dict) -> int:
                return int((job.get('ats_score') or 0) * 100)

            # Appliquer min_score sur ATS
            offers_ats = [o for o in offers_ats if percent_ats(o) >= min_score]

            # Exclure masquées
            offers_ats = [o for o in offers_ats if offer_id(o) not in hidden]

            # Filtre statut
            if filter_status == "Nouvelles":
                offers_ats = [o for o in offers_ats if offer_id(o) not in viewed]
            elif filter_status == "Vues":
                offers_ats = [o for o in offers_ats if offer_id(o) in viewed]
            elif filter_status == "Favorites":
                offers_ats = [o for o in offers_ats if offer_id(o) in favorites]
            
            if offers_ats:
                st.success(f"✨ {len(offers_ats)} offre(s) trouvée(s) correspondant à votre profil (tri ATS)")

                # Trier par score ATS décroissant
                offers_ats.sort(key=lambda o: (o.get('ats_score') or 0), reverse=True)

                for job in offers_ats:
                    percent = percent_ats(job)
                    border_color = "#4CAF50" if percent >= 80 else "#FFA726" if percent >= 60 else "#D4AF37"

                    req_skills = job.get('required_skills', [])
                    matched_sk = job.get('matched_skills', [])
                    matched_clean = [s.split(' (similar:')[0] for s in matched_sk]
                    missing_list = [s for s in req_skills if s not in matched_clean]
                    missing_skills = ", ".join(missing_list)
                    missing_html = f'<p style="margin: 5px 0; color: #dc3545;">✗ Manque: {missing_skills}</p>' if missing_skills else ""

                    url = job.get('url')
                    link_html = f' | <a href="{url}" target="_blank" style="text-decoration: none; font-weight: 600; color: #1f78d1;">Ouvrir l’offre</a>' if url else ""
                    src = job.get('source')
                    created = job.get('created','')
                    created_badge = f"<span style='background:#eef2f7;color:#394b59;padding:2px 8px;border-radius:10px;margin-left:8px;font-size:12px;'>🗓 {created[:10]}</span>" if created else ""
                    source_badge = f"<span style='background:#f5efe3;color:#7a5b1f;padding:2px 8px;border-radius:10px;margin-left:8px;font-size:12px;'>🔎 {src}</span>" if src else ""

                    desc = (job.get('description','') or '')
                    short_desc = (desc[:220] + '…') if len(desc) > 220 else desc

                    st.markdown(f"""
                    <div style="background: white; border-radius: 10px; padding: 20px; margin: 10px 0; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1); border-left: 4px solid {border_color};">
                        <h3 style="margin: 0; color: #333;">{job['title']} - {job['company']}</h3>
                        <p style="color: #666; margin: 5px 0;">{short_desc} | <span style=\"background: linear-gradient(135deg, #E6C200 0%, #D4AF37 100%); color: white; padding: 3px 10px; border-radius: 12px; font-weight: bold;\">{percent}% ATS</span>{created_badge}{source_badge}{link_html}</p>
                        <p style="margin: 10px 0; color: #28a745;">✓ {len(matched_clean)}/{len(req_skills)} compétences matchées</p>
                        {missing_html}
                    </div>
                    """, unsafe_allow_html=True)

                    # Actions utilisateur: Favori / Vu / Masquer
                    bcol1, bcol2, bcol3 = st.columns([1,1,1])
                    oid = offer_id(job)
                    fav_label = "⭐ Retirer des favoris" if oid in favorites else "⭐ Ajouter aux favoris"
                    if bcol1.button(fav_label, key=f"fav_{oid}"):
                        if oid in favorites:
                            favorites.remove(oid)
                        else:
                            favorites.add(oid)
                        user_state['favorites'] = list(favorites)
                        save_user_state(current_user, user_state)
                        st.rerun()

                    vu_label = "👁️ Marqué vu" if oid in viewed else "👁️ Marquer comme vu"
                    if bcol2.button(vu_label, key=f"view_{oid}"):
                        viewed.add(oid)
                        user_state['viewed'] = list(viewed)
                        save_user_state(current_user, user_state)
                        st.rerun()

                    if bcol3.button("Masquer", key=f"hide_{oid}"):
                        hidden.add(oid)
                        user_state['hidden'] = list(hidden)
                        save_user_state(current_user, user_state)
                        st.rerun()

                    # Détails de l'offre sous forme d'expander (plus fiable)
                    with st.expander(f"Voir les détails • {job['title']} - {job.get('company','')}"):
                        st.markdown(f"**Titre:** {job.get('title','')}")
                        st.markdown(f"**Entreprise:** {job.get('company','')}")
                        st.markdown(f"**Description:** {desc}")
                        url = job.get('url')
                        if url:
                            st.markdown(f"**Lien:** [{url}]({url})")
                        else:
                            st.info("Aucun lien fourni pour cette offre.")
                        req = job.get('requirements', {})
                        st.markdown(f"**Exigences détectées:** {req.get('required_years','?')} ans • {req.get('required_education','?')} • {req.get('seniority','?')}")
            else:
                st.info("Aucune offre ne correspond à vos critères. Essayez de réduire le score minimum.")
        else:
            st.warning("Aucun CV analysé. Veuillez télécharger votre CV dans la section 'Mon Profil'.")
