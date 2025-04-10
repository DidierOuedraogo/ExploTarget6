import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from streamlit_option_menu import option_menu
import uuid
import json
from datetime import datetime
import base64
from io import BytesIO

# Configuration de la page
st.set_page_config(
    page_title="Preliminary Explo Target Estimation",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Appliquer un style CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2C3E50;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: 700;
    }
    .sub-header {
        font-size: 1.8rem;
        color: #34495E;
        margin-top: 2rem;
        margin-bottom: 1rem;
        font-weight: 600;
    }
    .card {
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        padding: 20px;
        margin-bottom: 20px;
        background-color: white;
    }
    .highlight {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 5px;
        border-left: 5px solid #4CAF50;
    }
    .styled-table {
        border-collapse: collapse;
        width: 100%;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
    }
    .styled-table thead tr {
        background-color: #34495E;
        color: #ffffff;
        text-align: left;
    }
    .styled-table th,
    .styled-table td {
        padding: 12px 15px;
    }
    .styled-table tbody tr {
        border-bottom: 1px solid #dddddd;
    }
    .styled-table tbody tr:nth-of-type(even) {
        background-color: #f3f3f3;
    }
    .styled-table tbody tr:last-of-type {
        border-bottom: 2px solid #34495E;
    }
    .footer {
        text-align: center;
        padding: 20px;
        font-size: 0.8rem;
        color: #666;
        border-top: 1px solid #eee;
        margin-top: 30px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        padding: 10px 16px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4CAF50 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# Fonction pour initialiser l'état de session
def init_session_state():
    if 'corps_mineralises' not in st.session_state:
        st.session_state.corps_mineralises = []
    if 'scenarios' not in st.session_state:
        st.session_state.scenarios = []
    if 'current_scenario' not in st.session_state:
        st.session_state.current_scenario = {
            "id": str(uuid.uuid4()),
            "nom": "Nouveau scénario",
            "date_creation": datetime.now().strftime("%Y-%m-%d"),
            "corps_mineralises": []
        }

# Initialiser l'état de session
init_session_state()

# Fonction pour télécharger les données
def download_data(df, filename):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}.csv">Télécharger les données (CSV)</a>'
    return href

# Fonction pour créer un PDF rapport
def create_download_link(val, filename):
    b64 = base64.b64encode(val).decode()
    return f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}.pdf">Télécharger le rapport PDF</a>'

# Fonction pour créer une visualisation 3D d'un corps minéralisé de type filon
def create_filon_3d(corps, corps_idx, opacity=0.7):
    """
    Crée une représentation 3D d'un corps minéralisé de type filon.
    
    Args:
        corps: dictionnaire contenant les propriétés du corps minéralisé
        corps_idx: indice pour la couleur
        opacity: opacité du corps (0-1)
    
    Returns:
        Une trace plotly Mesh3d
    """
    # Paramètres du corps
    azimuth_rad = np.radians(corps["azimuth"])
    inclinaison_rad = np.radians(corps["inclinaison"])
    
    # Point central du corps
    x0, y0 = 0, 0
    z0 = corps["elevation_toit"] - corps["epaisseur"] * np.sin(inclinaison_rad) / 2
    
    # Modélisation d'un filon:
    # - épaisseur: largeur perpendiculaire au plan du filon
    # - puissance: plus grand allongement dans le plan du filon
    # - profondeur: extension en profondeur, le long de l'inclinaison
    
    # Vecteurs unitaires pour le système d'axes du filon
    # Axe principal (direction d'allongement - puissance)
    axe_puissance_x = np.sin(azimuth_rad)
    axe_puissance_y = np.cos(azimuth_rad)
    axe_puissance_z = 0
    
    # Axe de profondeur (suivant l'inclinaison)
    axe_profondeur_x = np.sin(azimuth_rad + np.pi/2) * np.cos(inclinaison_rad)
    axe_profondeur_y = np.cos(azimuth_rad + np.pi/2) * np.cos(inclinaison_rad)
    axe_profondeur_z = -np.sin(inclinaison_rad)  # Négatif car on va vers le bas
    
    # Axe d'épaisseur (perpendiculaire au plan du filon)
    axe_epaisseur_x = -np.sin(azimuth_rad) * np.sin(inclinaison_rad)
    axe_epaisseur_y = -np.cos(azimuth_rad) * np.sin(inclinaison_rad)
    axe_epaisseur_z = -np.cos(inclinaison_rad)
    
    # Générer les 8 sommets du parallélépipède
    # Format: (±puissance/2, ±profondeur/2, ±épaisseur/2)
    vertices = []
    for p in [-1, 1]:  # Puissance
        for d in [-1, 1]:  # Profondeur
            for e in [-1, 1]:  # Épaisseur
                # Calculer les coordonnées de chaque sommet
                x = x0 + p * corps["puissance"]/2 * axe_puissance_x + d * corps["profondeur"]/2 * axe_profondeur_x + e * corps["epaisseur"]/2 * axe_epaisseur_x
                y = y0 + p * corps["puissance"]/2 * axe_puissance_y + d * corps["profondeur"]/2 * axe_profondeur_y + e * corps["epaisseur"]/2 * axe_epaisseur_y
                z = z0 + p * corps["puissance"]/2 * axe_puissance_z + d * corps["profondeur"]/2 * axe_profondeur_z + e * corps["epaisseur"]/2 * axe_epaisseur_z
                vertices.append((x, y, z))
    
    # Extraire les coordonnées x, y, z des sommets
    x = [v[0] for v in vertices]
    y = [v[1] for v in vertices]
    z = [v[2] for v in vertices]
    
    # Indices des faces (triangulation) - définit chaque face du filon
    # Front faces
    i = [0, 0, 1, 1, 2, 2, 3, 3]
    j = [1, 2, 3, 0, 6, 3, 7, 2]
    k = [2, 0, 0, 3, 3, 7, 6, 6]
    
    # Back faces
    i.extend([4, 4, 5, 5, 6, 6, 7, 7])
    j.extend([5, 6, 7, 4, 2, 7, 3, 6])
    k.extend([6, 4, 4, 7, 6, 3, 7, 2])
    
    # Side faces
    i.extend([0, 0, 1, 1, 4, 4, 5, 5])
    j.extend([4, 1, 5, 0, 7, 0, 1, 4])
    k.extend([5, 5, 1, 4, 0, 3, 0, 7])
    
    # Couleur basée sur l'indice
    colors = px.colors.qualitative.Plotly
    color = colors[corps_idx % len(colors)]
    
    # Créer le mesh 3D
    return go.Mesh3d(
        x=x, y=y, z=z,
        i=i, j=j, k=k,
        name=corps["nom"],
        color=color,
        opacity=opacity,
        hovertemplate=f"<b>{corps['nom']}</b><br>" +
        f"Teneur: {corps['teneur']} {corps['unite_teneur']}<br>" +
        f"Puissance: {corps['puissance']} m<br>" +
        f"Épaisseur: {corps['epaisseur']} m<br>" +
        f"Profondeur: {corps['profondeur']} m<br>" +
        f"Volume: {corps['puissance'] * corps['epaisseur'] * corps['profondeur']:,.0f} m³<br>" +
        f"Tonnage: {corps['puissance'] * corps['epaisseur'] * corps['profondeur'] * corps['densite']:,.0f} t<br>" +
        "<extra></extra>"
    )

# Menu de navigation latéral
with st.sidebar:
    st.image("https://via.placeholder.com/150x100.png?text=MineralEst+Pro", width=200)
    st.markdown("### Preliminary Explo Target Estimation")
    
    selected = option_menu(
        "Menu Principal",
        ["Accueil", "Estimation de Ressources", "Planification de Forage", "Scénarios", "Guide Utilisateur"],
        icons=['house', 'gem', 'drill', 'diagram-3', 'book'],
        menu_icon="list", default_index=0,
        styles={
            "container": {"padding": "5px", "background-color": "#f0f2f6"},
            "icon": {"color": "orange", "font-size": "18px"}, 
            "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px"},
            "nav-link-selected": {"background-color": "#4CAF50"},
        }
    )

# Page d'accueil
if selected == "Accueil":
    st.markdown('<h1 class="main-header">Preliminary Explo Target Estimation</h1>', unsafe_allow_html=True)
    st.markdown('<h3 style="text-align: center;">Logiciel d\'estimation de ressources minérales pour l\'exploration</h3>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 🚀 Caractéristiques principales")
        st.markdown("""
        - Estimation rapide des ressources minérales
        - Planification efficace des campagnes de forage
        - Analyse de sensibilité des paramètres clés
        - Comparaison de différents scénarios d'exploration
        - Optimisation budgétaire pour les phases suivantes
        """)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 📊 Derniers projets")
        if len(st.session_state.scenarios) > 0:
            for i, scenario in enumerate(st.session_state.scenarios[-3:]):
                st.markdown(f"**{scenario['nom']}** - {scenario['date_creation']}")
                st.markdown(f"Corps minéralisés: {len(scenario['corps_mineralises'])}")
                st.markdown("---")
        else:
            st.info("Aucun projet existant. Créez votre premier scénario dans l'onglet 'Scénarios'.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 🔍 Démarrage rapide")
        st.markdown("""
        1. **Créez un nouveau scénario** dans l'onglet "Scénarios"
        2. **Ajoutez des corps minéralisés** avec leurs caractéristiques
        3. **Estimez les ressources** en fonction de la maille de forage
        4. **Planifiez** des forages additionnels pour affiner l'estimation
        5. **Exportez** vos résultats et votre plan de forage
        """)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 📈 Statistiques du projet")
        
        metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
        with metrics_col1:
            st.metric("Scénarios", len(st.session_state.scenarios))
        with metrics_col2:
            corps_total = sum([len(s["corps_mineralises"]) for s in st.session_state.scenarios])
            st.metric("Corps minéralisés", corps_total)
        with metrics_col3:
            st.metric("Version", "1.2.0")
            
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 👤 À propos de l'auteur")
        st.markdown("""
        **Didier Ouedraogo, P.Geo.**
        
        Expert en géologie minière et exploration avec plus de 20 ans d'expérience dans le développement de méthodes d'estimation de ressources et la planification de campagnes de forage.
        """)
        st.markdown('</div>', unsafe_allow_html=True)

# Page d'estimation de ressources
elif selected == "Estimation de Ressources":
    st.markdown('<h1 class="main-header">Estimation de Ressources Minérales</h1>', unsafe_allow_html=True)
    
    # Section pour sélectionner/créer un scénario
    scenario_tab1, scenario_tab2 = st.tabs(["Scénario actuel", "Sélectionner un scénario"])
    
    with scenario_tab1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Scénario courant")
        scenario_name = st.text_input("Nom du scénario", st.session_state.current_scenario["nom"])
        st.session_state.current_scenario["nom"] = scenario_name
        
        # Afficher les corps minéralisés du scénario actuel
        if len(st.session_state.current_scenario["corps_mineralises"]) > 0:
            st.markdown("### Corps minéralisés dans ce scénario")
            corps_df = pd.DataFrame(st.session_state.current_scenario["corps_mineralises"])
            st.dataframe(corps_df[["nom", "puissance", "epaisseur", "profondeur", "teneur", "densite"]])
        else:
            st.info("Aucun corps minéralisé défini. Ajoutez-en un dans le formulaire ci-dessous.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with scenario_tab2:
        if len(st.session_state.scenarios) > 0:
            selected_scenario = st.selectbox(
                "Sélectionner un scénario existant",
                options=range(len(st.session_state.scenarios)),
                format_func=lambda i: st.session_state.scenarios[i]["nom"]
            )
            if st.button("Charger ce scénario"):
                st.session_state.current_scenario = st.session_state.scenarios[selected_scenario].copy()
                st.success(f"Scénario '{st.session_state.current_scenario['nom']}' chargé avec succès!")
                st.rerun()
        else:
            st.info("Aucun scénario sauvegardé. Créez un nouveau scénario et ajoutez-y des corps minéralisés.")
    
    # Formulaire pour ajouter un corps minéralisé
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h2 class="sub-header">Ajouter un corps minéralisé</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        nom_corps = st.text_input("Nom du corps minéralisé", "Corps-" + str(len(st.session_state.current_scenario["corps_mineralises"]) + 1))
        puissance = st.number_input("Puissance (m)", min_value=0.1, max_value=1000.0, value=100.0, step=10.0,
                                  help="Plus grand allongement du corps minéralisé dans son plan")
        epaisseur = st.number_input("Épaisseur (m)", min_value=0.1, max_value=500.0, value=5.0, step=0.5,
                                   help="Largeur perpendiculaire au plan du filon (ce que traverseraient les forages)")
        profondeur = st.number_input("Profondeur (m)", min_value=0.1, max_value=2000.0, value=200.0, step=10.0,
                                    help="Extension en profondeur le long de l'inclinaison")
    
    with col2:
        teneur = st.number_input("Teneur moyenne", min_value=0.01, max_value=100.0, value=1.5, step=0.1)
        unite_teneur = st.selectbox("Unité de teneur", ["g/t (or, argent)", "% (métaux de base)"])
        densite = st.number_input("Densité (t/m³)", min_value=1.0, max_value=10.0, value=2.7, step=0.1)
        
        azimuth = st.number_input("Azimuth (°)", min_value=0, max_value=360, value=90, step=5,
                                help="Direction du corps minéralisé, 0° = Nord, 90° = Est, etc.")
        inclinaison = st.number_input("Inclinaison (°)", min_value=0, max_value=90, value=60, step=5,
                                     help="Angle d'inclinaison par rapport à l'horizontale")
        elevation_toit = st.number_input("Élévation du toit (m)", min_value=-2000.0, max_value=0.0, value=-50.0, step=10.0,
                                        help="Élévation du point le plus haut du corps minéralisé (valeur négative pour sous la surface)")
    
    if st.button("Ajouter ce corps minéralisé"):
        nouveau_corps = {
            "id": str(uuid.uuid4()),
            "nom": nom_corps,
            "puissance": puissance,
            "epaisseur": epaisseur,
            "profondeur": profondeur,
            "teneur": teneur,
            "unite_teneur": unite_teneur,
            "densite": densite,
            "azimuth": azimuth,
            "inclinaison": inclinaison,
            "elevation_toit": elevation_toit
        }
        st.session_state.current_scenario["corps_mineralises"].append(nouveau_corps)
        st.success(f"Corps minéralisé '{nom_corps}' ajouté avec succès!")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Calcul et affichage des résultats
    if len(st.session_state.current_scenario["corps_mineralises"]) > 0:
        st.markdown('<h2 class="sub-header">Paramètres de la maille de forage</h2>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            maille_x = st.number_input("Espacement en X (m)", min_value=10.0, max_value=1000.0, value=100.0, step=10.0)
        with col2:
            maille_y = st.number_input("Espacement en Y (m)", min_value=10.0, max_value=1000.0, value=100.0, step=10.0)
        with col3:
            substance = st.selectbox(
                "Substance principale",
                ["Or", "Argent", "Cuivre", "Zinc", "Plomb", "Nickel", "Fer", "Autre"]
            )
        
        # Paramètres de classification personnalisables
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Paramètres de classification des ressources")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            maille_mesurees = st.number_input("Maille max. pour ressources mesurées (m)", min_value=10.0, max_value=100.0, value=50.0, step=5.0)
            facteur_mesurees = st.number_input("Facteur de confiance - Mesurées", min_value=0.5, max_value=1.0, value=0.95, step=0.01)
        with col2:
            maille_indiquees = st.number_input("Maille max. pour ressources indiquées (m)", min_value=50.0, max_value=200.0, value=100.0, step=10.0)
            facteur_indiquees = st.number_input("Facteur de confiance - Indiquées", min_value=0.5, max_value=1.0, value=0.8, step=0.01)
        with col3:
            facteur_inferees = st.number_input("Facteur de confiance - Inférées", min_value=0.3, max_value=0.8, value=0.6, step=0.01)
        st.markdown('</div>', unsafe_allow_html=True)
            
        # Déterminer la classification en fonction de la maille
        maille_moyenne = (maille_x + maille_y) / 2
        if maille_moyenne < maille_mesurees:
            classification = "Mesurées"
            facteur_confiance = facteur_mesurees
        elif maille_moyenne <= maille_indiquees:
            classification = "Indiquées"
            facteur_confiance = facteur_indiquees
        else:
            classification = "Inférées"
            facteur_confiance = facteur_inferees
            
        st.markdown('<div class="highlight">', unsafe_allow_html=True)
        st.markdown(f"**Classification des ressources basée sur la maille**: {classification} (facteur de confiance: {facteur_confiance:.2f})")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Calcul des ressources pour chaque corps et total
        st.markdown('<h2 class="sub-header">Estimation des ressources</h2>', unsafe_allow_html=True)
        
        resultats = []
        total_tonnage = 0
        total_metal = 0
        
        for corps in st.session_state.current_scenario["corps_mineralises"]:
            # Volume du corps minéralisé (m³)
            volume = corps["puissance"] * corps["epaisseur"] * corps["profondeur"]
            
            # Tonnage (tonnes)
            tonnage = volume * corps["densite"]
            
            # Tonnage ajusté par le facteur de confiance
            tonnage_ajuste = tonnage * facteur_confiance
            
            # Quantité de métal/minéral
            if "g/t" in corps["unite_teneur"]:
                metal_unit = "onces"
                metal_quantite = tonnage_ajuste * corps["teneur"] / 31.1035  # Conversion g à onces troy
            else:
                metal_unit = "tonnes"
                metal_quantite = tonnage_ajuste * corps["teneur"] / 100  # Conversion % à tonnes
            
            resultats.append({
                "nom": corps["nom"],
                "volume": volume,
                "tonnage_brut": tonnage,
                "tonnage_ajuste": tonnage_ajuste,
                "teneur": corps["teneur"],
                "unite_teneur": corps["unite_teneur"],
                "metal_quantite": metal_quantite,
                "metal_unit": metal_unit
            })
            
            total_tonnage += tonnage_ajuste
            total_metal += metal_quantite
        
        # Afficher les résultats par corps minéralisé
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Résultats par corps minéralisé")
        
        # Conversion en DataFrame pour un affichage propre
        resultats_df = pd.DataFrame(resultats)
        resultats_df["volume"] = resultats_df["volume"].map('{:,.0f}'.format)
        resultats_df["tonnage_brut"] = resultats_df["tonnage_brut"].map('{:,.0f}'.format)
        resultats_df["tonnage_ajuste"] = resultats_df["tonnage_ajuste"].map('{:,.0f}'.format)
        resultats_df["metal_quantite"] = resultats_df["metal_quantite"].map('{:,.0f}'.format)
        
        st.dataframe(resultats_df[["nom", "volume", "tonnage_ajuste", "teneur", "unite_teneur", "metal_quantite", "metal_unit"]])
        
        # Afficher le total
        st.markdown(f"""
        <div class="highlight">
        <h3>Résultat total pour le scénario "{st.session_state.current_scenario["nom"]}":</h3>
        <p>Tonnage total: <b>{total_tonnage:,.0f} tonnes</b></p>
        <p>Quantité de métal: <b>{total_metal:,.0f} {resultats[0]["metal_unit"]}</b></p>
        <p>Classification: <b>{classification}</b></p>
        </div>
        """, unsafe_allow_html=True)
        
        # Ajouter un bouton pour exporter les résultats
        st.markdown(download_data(resultats_df, f"resultats_{st.session_state.current_scenario['nom']}"), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Visualisation des résultats
        st.markdown('<h2 class="sub-header">Visualisation</h2>', unsafe_allow_html=True)
        
        viz_tab1, viz_tab2 = st.tabs(["Graphiques", "Modèle 3D simplifié"])
        
        with viz_tab1:
            col1, col2 = st.columns(2)
            
            with col1:
                # Graphique de distribution des tonnages
                fig1 = px.bar(
                    resultats_df,
                    x="nom",
                    y="tonnage_ajuste",
                    title="Distribution des tonnages par corps minéralisé",
                    labels={"nom": "Corps minéralisé", "tonnage_ajuste": "Tonnage ajusté"},
                    text_auto='.2s'
                )
                fig1.update_layout(height=400)
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                # Graphique de distribution des teneurs
                fig2 = px.bar(
                    resultats_df,
                    x="nom",
                    y="teneur",
                    title=f"Distribution des teneurs par corps minéralisé",
                    labels={"nom": "Corps minéralisé", "teneur": f"Teneur"},
                    text_auto='.2f'
                )
                fig2.update_layout(height=400)
                st.plotly_chart(fig2, use_container_width=True)
                
            # Analyse de sensibilité
            st.subheader("Analyse de sensibilité")
            
            corps_sensibilite = st.selectbox(
                "Sélectionner un corps minéralisé pour l'analyse de sensibilité",
                options=range(len(st.session_state.current_scenario["corps_mineralises"])),
                format_func=lambda i: st.session_state.current_scenario["corps_mineralises"][i]["nom"]
            )
            
            corps = st.session_state.current_scenario["corps_mineralises"][corps_sensibilite]
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Sensibilité à la teneur
                teneurs_test = np.linspace(max(0.1, corps["teneur"] * 0.5), corps["teneur"] * 1.5, 10)
                volume = corps["puissance"] * corps["epaisseur"] * corps["profondeur"]
                tonnage_ajuste = volume * corps["densite"] * facteur_confiance
                
                if "g/t" in corps["unite_teneur"]:
                    metals = tonnage_ajuste * teneurs_test / 31.1035
                    metal_unit = "onces"
                else:
                    metals = tonnage_ajuste * teneurs_test / 100
                    metal_unit = "tonnes"
                
                fig_sens1 = px.line(
                    x=teneurs_test, 
                    y=metals,
                    markers=True,
                    title=f"Sensibilité à la teneur - {corps['nom']}",
                    labels={"x": f"Teneur ({corps['unite_teneur']})", "y": f"Quantité de métal ({metal_unit})"}
                )
                st.plotly_chart(fig_sens1, use_container_width=True)
            
            with col2:
                # Sensibilité à l'épaisseur
                epaisseurs_test = np.linspace(max(0.1, corps["epaisseur"] * 0.5), corps["epaisseur"] * 1.5, 10)
                volumes_test = corps["puissance"] * epaisseurs_test * corps["profondeur"]
                tonnages_test = volumes_test * corps["densite"] * facteur_confiance
                
                fig_sens2 = px.line(
                    x=epaisseurs_test, 
                    y=tonnages_test,
                    markers=True,
                    title=f"Sensibilité à l'épaisseur - {corps['nom']}",
                    labels={"x": "Épaisseur (m)", "y": "Tonnage (tonnes)"}
                )
                st.plotly_chart(fig_sens2, use_container_width=True)
                
        with viz_tab2:
            st.subheader("Représentation 3D simplifiée des corps minéralisés")
            
            # Création d'une visualisation 3D simplifiée
            fig = go.Figure()
            
            # Ajout du plan de surface (z=0)
            x_surface = np.linspace(-300, 300, 2)
            y_surface = np.linspace(-300, 300, 2)
            X_surface, Y_surface = np.meshgrid(x_surface, y_surface)
            Z_surface = np.zeros_like(X_surface)
            
            fig.add_trace(go.Surface(
                x=X_surface, y=Y_surface, z=Z_surface,
                colorscale=[[0, 'green'], [1, 'green']],
                showscale=False,
                opacity=0.3,
                name="Surface du sol"
            ))
            
            for i, corps in enumerate(st.session_state.current_scenario["corps_mineralises"]):
                # Ajout du corps minéralisé en utilisant la fonction de création de filon 3D
                fig.add_trace(create_filon_3d(corps, i))
                
                # Paramètres du corps pour l'affichage des lignes directrices
                azimuth_rad = np.radians(corps["azimuth"])
                inclinaison_rad = np.radians(corps["inclinaison"])
                
                # Point central du corps
                x0, y0 = 0, 0
                z0 = corps["elevation_toit"] - corps["epaisseur"] * np.sin(inclinaison_rad) / 2
                
                # Vecteurs unitaires pour les axes du filon
                # Axe principal (direction d'allongement - puissance)
                axe_puissance_x = np.sin(azimuth_rad)
                axe_puissance_y = np.cos(azimuth_rad)
                axe_puissance_z = 0
                
                # Axe de profondeur (suivant l'inclinaison)
                axe_profondeur_x = np.sin(azimuth_rad + np.pi/2) * np.cos(inclinaison_rad)
                axe_profondeur_y = np.cos(azimuth_rad + np.pi/2) * np.cos(inclinaison_rad)
                axe_profondeur_z = -np.sin(inclinaison_rad)  # Négatif car on va vers le bas
                
                # Ajout d'une ligne suivant l'axe de puissance (direction)
                fig.add_trace(go.Scatter3d(
                    x=[x0 - corps["puissance"]/2 * axe_puissance_x, x0 + corps["puissance"]/2 * axe_puissance_x],
                    y=[y0 - corps["puissance"]/2 * axe_puissance_y, y0 + corps["puissance"]/2 * axe_puissance_y],
                    z=[z0, z0],
                    mode='lines',
                    line=dict(color='black', width=3),
                    name=f"Direction {corps['nom']}",
                    showlegend=i==0
                ))
                
                # Ajout d'une ligne suivant l'axe de plongement (inclinaison)
                fig.add_trace(go.Scatter3d(
                    x=[x0, x0 + 50 * axe_profondeur_x],
                    y=[y0, y0 + 50 * axe_profondeur_y],
                    z=[z0, z0 + 50 * axe_profondeur_z],
                    mode='lines',
                    line=dict(color='darkgray', width=2, dash='dash'),
                    name=f"Inclinaison {corps['nom']}",
                    showlegend=i==0
                ))
            
            # Ajout des axes et d'une grille pour la maille de forage
            x_grid = np.arange(-200, 201, maille_x)
            y_grid = np.arange(-200, 201, maille_y)
            
            for x in x_grid:
                fig.add_trace(go.Scatter3d(
                    x=[x, x], y=[-200, 200], z=[0, 0],
                    mode='lines',
                    line=dict(color='gray', width=1, dash='dash'),
                    showlegend=False
                ))
                
            for y in y_grid:
                fig.add_trace(go.Scatter3d(
                    x=[-200, 200], y=[y, y], z=[0, 0],
                    mode='lines',
                    line=dict(color='gray', width=1, dash='dash'),
                    showlegend=False
                ))
            
            # Configuration de la mise en page
            fig.update_layout(
                scene=dict(
                    xaxis_title='X (m)',
                    yaxis_title='Y (m)',
                    zaxis_title='Z (m)',
                    aspectmode='data',
                    zaxis=dict(range=[-500, 50])  # Ajuster l'échelle de Z pour visualiser correctement sous terre
                ),
                margin=dict(l=0, r=0, b=0, t=30),
                height=700
            )
            
            st.plotly_chart(fig, use_container_width=True)
            st.caption("""
            Cette visualisation 3D simplifiée montre les corps minéralisés de type filon selon leur orientation et dimensions.
            - La surface verte représente le niveau du sol (z=0)
            - La ligne noire montre la direction principale du filon (azimuth)
            - La ligne pointillée grise indique la direction de plongement (inclinaison)
            - L'épaisseur est perpendiculaire au plan du filon
            - La puissance est le plus grand allongement dans le plan du filon
            - La profondeur est l'extension en profondeur le long de l'inclinaison
            """)

# Page de planification de forage
elif selected == "Planification de Forage":
    st.markdown('<h1 class="main-header">Planification de Campagne de Forage</h1>', unsafe_allow_html=True)
    
    if len(st.session_state.current_scenario["corps_mineralises"]) == 0:
        st.warning("Aucun corps minéralisé défini. Veuillez d'abord créer des corps minéralisés dans l'onglet 'Estimation de Ressources'.")
    else:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Configuration de la campagne de forage")
        
        col1, col2 = st.columns(2)
        
        with col1:
            type_forage = st.selectbox(
                "Type de forage",
                ["Carottage diamanté (DDH)", "Circulation inverse (RC)"]
            )
            
            maille_initiale_x = st.number_input("Maille initiale - Espacement X (m)", min_value=10.0, max_value=500.0, value=100.0, step=10.0)
            maille_initiale_y = st.number_input("Maille initiale - Espacement Y (m)", min_value=10.0, max_value=500.0, value=100.0, step=10.0)
            
            maille_detail_x = st.number_input("Maille détaillée - Espacement X (m)", min_value=5.0, max_value=250.0, value=50.0, step=5.0)
            maille_detail_y = st.number_input("Maille détaillée - Espacement Y (m)", min_value=5.0, max_value=250.0, value=50.0, step=5.0)
        
        with col2:
            cout_metre = st.number_input("Coût par mètre foré (€)", min_value=10, max_value=1000, value=150, step=10)
            cout_mobilisation = st.number_input("Coût de mobilisation (€)", min_value=0, max_value=500000, value=50000, step=5000)
            cout_analyses = st.number_input("Coût des analyses par échantillon (€)", min_value=1, max_value=500, value=30, step=5)
            
            longueur_echantillon = st.number_input("Longueur moyenne des échantillons (m)", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
        
        # Nouveaux paramètres de forage personnalisables
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Paramètres des forages")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            azimuth_forage = st.number_input("Azimuth des forages (°)", min_value=0, max_value=360, value=270, step=5,
                                           help="Direction des forages, 0° = Nord, 90° = Est, etc.")
        with col2:
            inclinaison_forage = st.number_input("Inclinaison des forages (°)", min_value=0, max_value=90, value=60, step=5,
                                              help="Angle par rapport à la verticale, 0° = vertical, 90° = horizontal")
        with col3:
            profondeur_forage_max = st.number_input("Profondeur max. des forages (m)", min_value=50, max_value=2000, value=300, step=50,
                                                 help="Profondeur maximale des forages")
            
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Sélection des corps à forer
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Corps minéralisés à forer")
        
        corps_a_forer = st.multiselect(
            "Sélectionner les corps minéralisés pour la campagne de forage",
            options=[corps["nom"] for corps in st.session_state.current_scenario["corps_mineralises"]],
            default=[corps["nom"] for corps in st.session_state.current_scenario["corps_mineralises"]]
        )
        
        if not corps_a_forer:
            st.warning("Veuillez sélectionner au moins un corps minéralisé.")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Calcul du plan de forage
        if corps_a_forer:
            st.markdown('<h2 class="sub-header">Plan de forage</h2>', unsafe_allow_html=True)
            
            # Filtrer les corps minéralisés sélectionnés
            corps_selectionnes = [corps for corps in st.session_state.current_scenario["corps_mineralises"] 
                                if corps["nom"] in corps_a_forer]
            
            # Calcul pour chaque corps
            resultats_forage = []
            total_metres_initial = 0
            total_metres_detaille = 0
            total_forages_initial = 0
            total_forages_detaille = 0
            
            for corps in corps_selectionnes:
                # Nombre de forages initiaux
                nb_forages_x_initial = max(2, np.ceil(corps["puissance"] / maille_initiale_x))
                nb_forages_y_initial = max(2, np.ceil(corps["profondeur"] / maille_initiale_y))
                nb_forages_initial = nb_forages_x_initial * nb_forages_y_initial
                
                # Nombre de forages détaillés (maille resserrée)
                nb_forages_x_detail = max(4, np.ceil(corps["puissance"] / maille_detail_x))
                nb_forages_y_detail = max(4, np.ceil(corps["profondeur"] / maille_detail_y))
                nb_forages_detail = nb_forages_x_detail * nb_forages_y_detail - nb_forages_initial
                
                # Utiliser la profondeur maximale spécifiée pour tous les forages
                profondeur_forage = profondeur_forage_max
                
                # Métrage total
                metres_initial = nb_forages_initial * profondeur_forage
                metres_detail = nb_forages_detail * profondeur_forage
                
                # Nombre d'échantillons
                nb_echantillons_initial = np.ceil(metres_initial / longueur_echantillon)
                nb_echantillons_detail = np.ceil(metres_detail / longueur_echantillon)
                
                # Coûts
                cout_initial = metres_initial * cout_metre + nb_echantillons_initial * cout_analyses
                cout_detail = metres_detail * cout_metre + nb_echantillons_detail * cout_analyses
                
                resultats_forage.append({
                    "nom": corps["nom"],
                    "nb_forages_initial": nb_forages_initial,
                    "nb_forages_detail": nb_forages_detail,
                    "metres_initial": metres_initial,
                    "metres_detail": metres_detail,
                    "cout_initial": cout_initial,
                    "cout_detail": cout_detail,
                    "nb_echantillons_initial": nb_echantillons_initial,
                    "nb_echantillons_detail": nb_echantillons_detail,
                    "profondeur_forage": profondeur_forage
                })
                
                total_metres_initial += metres_initial
                total_metres_detaille += metres_detail
                total_forages_initial += nb_forages_initial
                total_forages_detaille += nb_forages_detail
            
            # Affichage des résultats
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.subheader("Plan de forage initial")
                
                df_initial = pd.DataFrame([{
                    "Corps": res["nom"],
                    "Nombre de forages": f"{res['nb_forages_initial']:.0f}",
                    "Métrage (m)": f"{res['metres_initial']:,.0f}",
                    "Échantillons": f"{res['nb_echantillons_initial']:,.0f}",
                    "Coût (€)": f"{res['cout_initial']:,.0f}"
                } for res in resultats_forage])
                
                st.table(df_initial)
                
                st.markdown(f"""
                <div class="highlight">
                <p><b>Total phase initiale:</b></p>
                <ul>
                    <li>Nombre de forages: {total_forages_initial:.0f}</li>
                    <li>Métrage total: {total_metres_initial:,.0f} m</li>
                    <li>Coût forage: {total_metres_initial * cout_metre:,.0f} €</li>
                    <li>Coût analyses: {sum(res['nb_echantillons_initial'] * cout_analyses for res in resultats_forage):,.0f} €</li>
                    <li>Coût total (incl. mobilisation): {cout_mobilisation + total_metres_initial * cout_metre + sum(res['nb_echantillons_initial'] * cout_analyses for res in resultats_forage):,.0f} €</li>
                </ul>
                </div>
                """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.subheader("Plan de forage détaillé")
                
                df_detail = pd.DataFrame([{
                    "Corps": res["nom"],
                    "Nombre de forages": f"{res['nb_forages_detail']:.0f}",
                    "Métrage (m)": f"{res['metres_detail']:,.0f}",
                    "Échantillons": f"{res['nb_echantillons_detail']:,.0f}",
                    "Coût (€)": f"{res['cout_detail']:,.0f}"
                } for res in resultats_forage])
                
                st.table(df_detail)
                
                st.markdown(f"""
                <div class="highlight">
                <p><b>Total phase détaillée:</b></p>
                <ul>
                    <li>Nombre de forages: {total_forages_detaille:.0f}</li>
                    <li>Métrage total: {total_metres_detaille:,.0f} m</li>
                    <li>Coût forage: {total_metres_detaille * cout_metre:,.0f} €</li>
                    <li>Coût analyses: {sum(res['nb_echantillons_detail'] * cout_analyses for res in resultats_forage):,.0f} €</li>
                    <li>Coût total (excl. mobilisation): {total_metres_detaille * cout_metre + sum(res['nb_echantillons_detail'] * cout_analyses for res in resultats_forage):,.0f} €</li>
                </ul>
                </div>
                """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Visualisation du plan de forage
            st.markdown('<h2 class="sub-header">Visualisation du plan de forage</h2>', unsafe_allow_html=True)
            
            # Créer une visualisation 3D du plan de forage
            fig = go.Figure()
            
            # Ajout du plan de surface (z=0)
            x_surface = np.linspace(-300, 300, 2)
            y_surface = np.linspace(-300, 300, 2)
            X_surface, Y_surface = np.meshgrid(x_surface, y_surface)
            Z_surface = np.zeros_like(X_surface)
            
            fig.add_trace(go.Surface(
                x=X_surface, y=Y_surface, z=Z_surface,
                colorscale=[[0, 'green'], [1, 'green']],
                showscale=False,
                opacity=0.3,
                name="Surface du sol"
            ))
            
            for corps_idx, corps in enumerate(corps_selectionnes):
                # Ajout du corps minéralisé en utilisant la fonction de création de filon 3D
                fig.add_trace(create_filon_3d(corps, corps_idx, opacity=0.5))
                
                # Paramètres du corps pour les forages
                azimuth_rad = np.radians(corps["azimuth"])
                inclinaison_rad = np.radians(corps["inclinaison"])
                
                # Point central du corps
                x0, y0 = 0, 0
                z0 = corps["elevation_toit"] - corps["epaisseur"] * np.sin(inclinaison_rad) / 2
                
                # Vecteurs unitaires pour les axes du filon
                # Axe principal (direction d'allongement - puissance)
                axe_puissance_x = np.sin(azimuth_rad)
                axe_puissance_y = np.cos(azimuth_rad)
                axe_puissance_z = 0
                
                # Axe de profondeur (suivant l'inclinaison)
                axe_profondeur_x = np.sin(azimuth_rad + np.pi/2) * np.cos(inclinaison_rad)
                axe_profondeur_y = np.cos(azimuth_rad + np.pi/2) * np.cos(inclinaison_rad)
                axe_profondeur_z = -np.sin(inclinaison_rad)  # Négatif car on va vers le bas
                
                # Ajout d'une ligne suivant l'axe de puissance (direction)
                fig.add_trace(go.Scatter3d(
                    x=[x0 - corps["puissance"]/2 * axe_puissance_x, x0 + corps["puissance"]/2 * axe_puissance_x],
                    y=[y0 - corps["puissance"]/2 * axe_puissance_y, y0 + corps["puissance"]/2 * axe_puissance_y],
                    z=[z0, z0],
                    mode='lines',
                    line=dict(color='black', width=3),
                    name=f"Direction {corps['nom']}",
                    showlegend=corps_idx==0
                ))
                
                # Paramètres des forages
                azimuth_forage_rad = np.radians(azimuth_forage)
                inclinaison_forage_rad = np.radians(inclinaison_forage)
                
                # Génération de grilles de forages pour chaque corps minéralisé
                # Phase initiale
                nb_forages_x = max(2, np.ceil(corps["puissance"] / maille_initiale_x))
                nb_forages_y = max(2, np.ceil(corps["profondeur"] / maille_initiale_y))
                
                # Calculer les positions des forages sur une grille qui couvre le filon
                # Créer une grille en coordonnées locales du filon, puis la transformer en coordonnées globales
                
                # Définir les limites de la grille en coordonnées locales du filon
                puissance_min = -corps["puissance"] / 2
                puissance_max = corps["puissance"] / 2
                profondeur_min = -corps["profondeur"] / 2
                profondeur_max = corps["profondeur"] / 2
                
                # Calculer l'espacement des forages en coordonnées locales du filon
                step_puissance = corps["puissance"] / nb_forages_x
                step_profondeur = corps["profondeur"] / nb_forages_y
                
                # Générer les forages initiaux sur cette grille
                for ix in range(int(nb_forages_x)):
                    for iy in range(int(nb_forages_y)):
                        # Position sur la grille locale du filon
                        p = puissance_min + (ix + 0.5) * step_puissance
                        d = profondeur_min + (iy + 0.5) * step_profondeur
                        
                        # Transformer en coordonnées globales
                        x_forage = x0 + p * axe_puissance_x + d * axe_profondeur_x
                        y_forage = y0 + p * axe_puissance_y + d * axe_profondeur_y
                        z_forage = 0  # Départ à la surface
                        
                        # Vecteur de direction du forage
                        dx_forage = np.sin(azimuth_forage_rad) * np.cos(inclinaison_forage_rad)
                        dy_forage = np.cos(azimuth_forage_rad) * np.cos(inclinaison_forage_rad)
                        dz_forage = -np.sin(inclinaison_forage_rad)  # Négatif car on fore vers le bas
                        
                        # Point final du forage avec profondeur maximale fixe
                        x_end = x_forage + dx_forage * profondeur_forage_max
                        y_end = y_forage + dy_forage * profondeur_forage_max
                        z_end = z_forage + dz_forage * profondeur_forage_max
                        
                        # Ajouter le forage à la figure
                        fig.add_trace(go.Scatter3d(
                            x=[x_forage, x_end],
                            y=[y_forage, y_end],
                            z=[z_forage, z_end],
                            mode='lines',
                            line=dict(color='red', width=2),
                            name=f"Forage initial",
                            showlegend=ix==0 and iy==0 and corps_idx==0,
                            hovertemplate=f"Forage initial<br>Corps: {corps['nom']}<br>Profondeur: {profondeur_forage_max:.1f}m<extra></extra>"
                        ))
                        
                        # Ajouter un point à la surface pour marquer l'emplacement du forage
                        fig.add_trace(go.Scatter3d(
                            x=[x_forage],
                            y=[y_forage],
                            z=[z_forage],
                            mode='markers',
                            marker=dict(color='red', size=5),
                            name=f"Collar forage initial",
                            showlegend=ix==0 and iy==0 and corps_idx==0,
                            hovertemplate=f"Collar forage initial<br>Corps: {corps['nom']}<extra></extra>"
                        ))
                
                # Ajouter quelques forages de la phase détaillée (pour ne pas surcharger la visualisation)
                nb_forages_x_detail = max(4, np.ceil(corps["puissance"] / maille_detail_x))
                nb_forages_y_detail = max(4, np.ceil(corps["profondeur"] / maille_detail_y))
                
                # Calculer l'espacement des forages détaillés
                step_puissance_detail = corps["puissance"] / nb_forages_x_detail
                step_profondeur_detail = corps["profondeur"] / nb_forages_y_detail
                
                # Limiter le nombre de forages détaillés à afficher pour plus de clarté
                max_display = 15
                step_x = max(1, int(nb_forages_x_detail / np.sqrt(max_display)))
                step_y = max(1, int(nb_forages_y_detail / np.sqrt(max_display)))
                
                for ix in range(0, int(nb_forages_x_detail), step_x):
                    for iy in range(0, int(nb_forages_y_detail), step_y):
                        # Vérifier si ce n'est pas un forage déjà couvert par la phase initiale
                        if ix % int(nb_forages_x_detail / nb_forages_x) == 0 and iy % int(nb_forages_y_detail / nb_forages_y) == 0:
                            continue
                            
                        # Position sur la grille locale du filon
                        p = puissance_min + (ix + 0.5) * step_puissance_detail
                        d = profondeur_min + (iy + 0.5) * step_profondeur_detail
                        
                        # Transformer en coordonnées globales
                        x_forage = x0 + p * axe_puissance_x + d * axe_profondeur_x
                        y_forage = y0 + p * axe_puissance_y + d * axe_profondeur_y
                        z_forage = 0  # Départ à la surface
                        
                        # Vecteur de direction du forage
                        dx_forage = np.sin(azimuth_forage_rad) * np.cos(inclinaison_forage_rad)
                        dy_forage = np.cos(azimuth_forage_rad) * np.cos(inclinaison_forage_rad)
                        dz_forage = -np.sin(inclinaison_forage_rad)  # Négatif car on fore vers le bas
                        
                        # Point final du forage avec profondeur maximale fixe
                        x_end = x_forage + dx_forage * profondeur_forage_max
                        y_end = y_forage + dy_forage * profondeur_forage_max
                        z_end = z_forage + dz_forage * profondeur_forage_max
                        
                        # Ajouter le forage à la figure
                        fig.add_trace(go.Scatter3d(
                            x=[x_forage, x_end],
                            y=[y_forage, y_end],
                            z=[z_forage, z_end],
                            mode='lines',
                            line=dict(color='blue', width=2, dash='dash'),
                            name=f"Forage détaillé",
                            showlegend=ix==0 and iy==0 and corps_idx==0,
                            hovertemplate=f"Forage détaillé<br>Corps: {corps['nom']}<br>Profondeur: {profondeur_forage_max:.1f}m<extra></extra>"
                        ))
                        
                        # Ajouter un point à la surface pour marquer l'emplacement du forage
                        fig.add_trace(go.Scatter3d(
                            x=[x_forage],
                            y=[y_forage],
                            z=[z_forage],
                            mode='markers',
                            marker=dict(color='blue', size=5),
                            name=f"Collar forage détaillé",
                            showlegend=ix==0 and iy==0 and corps_idx==0,
                            hovertemplate=f"Collar forage détaillé<br>Corps: {corps['nom']}<extra></extra>"
                        ))
            
            # Configuration de la mise en page
            fig.update_layout(
                scene=dict(
                    xaxis_title='X (m)',
                    yaxis_title='Y (m)',
                    zaxis_title='Z (m)',
                    aspectmode='data',
                    zaxis=dict(range=[-profondeur_forage_max, 50])  # Ajuster l'échelle de Z pour visualiser correctement sous terre
                ),
                margin=dict(l=0, r=0, b=0, t=30),
                height=700,
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=0.01
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
            st.caption(f"""
            Cette visualisation 3D montre le plan de forage proposé pour les corps minéralisés de type filon.
            Les forages initiaux (rouges) sont complétés par des forages détaillés (bleus) en maille resserrée.
            Tous les forages ont un azimut de {azimuth_forage}°, une inclinaison de {inclinaison_forage}° 
            par rapport à la verticale, et une profondeur uniformément fixée à {profondeur_forage_max}m.
            """)
            
            # Résumé du budget de forage
            st.markdown('<h2 class="sub-header">Budget total de la campagne de forage</h2>', unsafe_allow_html=True)
            
            cout_total = (cout_mobilisation + 
                         total_metres_initial * cout_metre + 
                         sum(res['nb_echantillons_initial'] * cout_analyses for res in resultats_forage) +
                         total_metres_detaille * cout_metre + 
                         sum(res['nb_echantillons_detail'] * cout_analyses for res in resultats_forage))
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Forages", f"{total_forages_initial + total_forages_detaille:.0f}")
                st.metric("Type de Forage", type_forage)
            
            with col2:
                st.metric("Métrage Total", f"{total_metres_initial + total_metres_detaille:,.0f} m")
                st.metric("Coût par Mètre", f"{cout_metre} €/m")
            
            with col3:
                st.metric("Budget Total", f"{cout_total:,.0f} €")
                st.metric("Densité de Forage", f"{(total_forages_initial + total_forages_detaille) / sum(corps['puissance'] * corps['profondeur'] / 10000 for corps in corps_selectionnes):,.1f} forages/ha")
            
            # Échéancier simplifié
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Échéancier prévisionnel")
            
            # Hypothèses
            metres_par_jour = st.slider("Productivité (mètres par jour)", min_value=20, max_value=300, value=100, step=10)
            jours_mobilisation = st.slider("Jours de mobilisation/préparation", min_value=1, max_value=60, value=15, step=1)
            
            # Calcul des durées
            jours_phase1 = np.ceil(total_metres_initial / metres_par_jour)
            jours_phase2 = np.ceil(total_metres_detaille / metres_par_jour)
            
            # Dates approximatives
            import datetime as dt
            date_debut = st.date_input("Date de début du projet", dt.date.today())
            date_fin_phase1 = date_debut + dt.timedelta(days=jours_mobilisation + jours_phase1)
            date_fin_phase2 = date_fin_phase1 + dt.timedelta(days=jours_phase2)
            
            echeancier_df = pd.DataFrame({
                'Étape': ['Mobilisation et préparation', 'Phase 1 - Forages initiaux', 'Phase 2 - Forages détaillés', 'Total'],
                'Durée (jours)': [jours_mobilisation, jours_phase1, jours_phase2, jours_mobilisation + jours_phase1 + jours_phase2],
                'Date de début': [date_debut, date_debut + dt.timedelta(days=jours_mobilisation), date_fin_phase1, date_debut],
                'Date de fin': [date_debut + dt.timedelta(days=jours_mobilisation), date_fin_phase1, date_fin_phase2, date_fin_phase2],
                'Budget (€)': [cout_mobilisation, 
                             total_metres_initial * cout_metre + sum(res['nb_echantillons_initial'] * cout_analyses for res in resultats_forage),
                             total_metres_detaille * cout_metre + sum(res['nb_echantillons_detail'] * cout_analyses for res in resultats_forage),
                             cout_total]
            })
            
            echeancier_df['Budget (€)'] = echeancier_df['Budget (€)'].map('{:,.0f}'.format)
            
            st.table(echeancier_df)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Exportation du plan de forage
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Exportation du plan de forage")
            
            # Préparation des données pour l'export
            export_data = {
                "scenario": st.session_state.current_scenario["nom"],
                "date_creation": datetime.now().strftime("%Y-%m-%d"),
                "parametres_forage": {
                    "type_forage": type_forage,
                    "maille_initiale": {"x": maille_initiale_x, "y": maille_initiale_y},
                    "maille_detaillee": {"x": maille_detail_x, "y": maille_detail_y},
                    "orientation_forage": {"azimuth": azimuth_forage, "inclinaison": inclinaison_forage},
                    "profondeur_max": profondeur_forage_max,
                    "couts": {
                        "metre": cout_metre,
                        "mobilisation": cout_mobilisation,
                        "analyses": cout_analyses
                    }
                },
                "corps_mineralises": corps_selectionnes,
                "resultats_forage": resultats_forage,
                "budget_total": cout_total,
                "echeancier": {
                    "date_debut": date_debut.strftime("%Y-%m-%d"),
                    "date_fin": date_fin_phase2.strftime("%Y-%m-%d"),
                    "duree_totale": int(jours_mobilisation + jours_phase1 + jours_phase2)
                }
            }
            
            # Export au format JSON
            json_str = json.dumps(export_data, default=str, indent=4)
            json_bytes = json_str.encode()
            
            # Bouton de téléchargement
            st.download_button(
                label="Télécharger le plan de forage (JSON)",
                data=json_bytes,
                file_name=f"plan_forage_{st.session_state.current_scenario['nom']}_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Export au format Excel (simulé avec CSV)
                resume_df = pd.DataFrame({
                    'Métrique': ['Scénario', 'Date de création', 'Nombre de corps minéralisés', 
                              'Type de forage', 'Azimuth forage', 'Inclinaison forage',
                              'Forages initiaux', 'Forages détaillés',
                              'Métrage total', 'Budget total', 'Durée estimée'],
                    'Valeur': [st.session_state.current_scenario["nom"], datetime.now().strftime("%Y-%m-%d"),
                             len(corps_selectionnes), type_forage, 
                             f"{azimuth_forage}°", f"{inclinaison_forage}°",
                             f"{total_forages_initial:.0f}", f"{total_forages_detaille:.0f}",
                             f"{total_metres_initial + total_metres_detaille:,.0f} m",
                             f"{cout_total:,.0f} €",
                             f"{jours_mobilisation + jours_phase1 + jours_phase2:.0f} jours"]
                })
                
                csv = resume_df.to_csv(index=False).encode()
                
                st.download_button(
                    label="Télécharger le résumé (CSV)",
                    data=csv,
                    file_name=f"resume_forage_{st.session_state.current_scenario['nom']}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            
            with col2:
                # Sauvegarder dans les scénarios
                if st.button("Sauvegarder ce plan dans le scénario actuel"):
                    # Ajouter les informations de forage au scénario
                    st.session_state.current_scenario["plan_forage"] = {
                        "date_creation": datetime.now().strftime("%Y-%m-%d"),
                        "type_forage": type_forage,
                        "maille_initiale_x": maille_initiale_x,
                        "maille_initiale_y": maille_initiale_y,
                        "maille_detail_x": maille_detail_x,
                        "maille_detail_y": maille_detail_y,
                        "azimuth_forage": azimuth_forage,
                        "inclinaison_forage": inclinaison_forage,
                        "profondeur_forage_max": profondeur_forage_max,
                        "cout_metre": cout_metre,
                        "cout_mobilisation": cout_mobilisation,
                        "cout_analyses": cout_analyses,
                        "budget_total": cout_total,
                        "duree_totale": jours_mobilisation + jours_phase1 + jours_phase2,
                        "resultats_forage": resultats_forage
                    }
                    
                    # Mettre à jour le scénario s'il existe déjà, sinon l'ajouter
                    scenario_ids = [s["id"] for s in st.session_state.scenarios]
                    if st.session_state.current_scenario["id"] in scenario_ids:
                        idx = scenario_ids.index(st.session_state.current_scenario["id"])
                        st.session_state.scenarios[idx] = st.session_state.current_scenario
                    else:
                        st.session_state.scenarios.append(st.session_state.current_scenario)
                    
                    st.success("Plan de forage sauvegardé dans le scénario!")
            
            st.markdown('</div>', unsafe_allow_html=True)

# Page de gestion des scénarios
elif selected == "Scénarios":
    st.markdown('<h1 class="main-header">Gestion des Scénarios</h1>', unsafe_allow_html=True)
    
    # Onglets pour créer ou gérer les scénarios
    tabs = st.tabs(["Créer un scénario", "Gérer les scénarios"])
    
    with tabs[0]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Créer un nouveau scénario")
        
        nouveau_nom = st.text_input("Nom du scénario", "Nouveau scénario")
        description = st.text_area("Description", "Description du scénario d'exploration")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            localisation = st.text_input("Localisation", "Site minier")
        
        with col2:
            substance_principale = st.selectbox(
                "Substance principale",
                ["Or", "Argent", "Cuivre", "Zinc", "Plomb", "Nickel", "Fer", "Autre"]
            )
        
        with col3:
            unite_mesure = st.selectbox(
                "Unité de mesure principale",
                ["g/t (or, argent)", "% (métaux de base)"]
            )
        
        if st.button("Créer ce scénario"):
            nouveau_scenario = {
                "id": str(uuid.uuid4()),
                "nom": nouveau_nom,
                "description": description,
                "localisation": localisation,
                "substance_principale": substance_principale,
                "unite_mesure": unite_mesure,
                "date_creation": datetime.now().strftime("%Y-%m-%d"),
                "corps_mineralises": []
            }
            
            st.session_state.scenarios.append(nouveau_scenario)
            st.session_state.current_scenario = nouveau_scenario
            
            st.success(f"Scénario '{nouveau_nom}' créé avec succès!")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tabs[1]:
        if len(st.session_state.scenarios) > 0:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Scénarios existants")
            
            for i, scenario in enumerate(st.session_state.scenarios):
                with st.expander(f"{scenario['nom']} - {scenario['date_creation']}"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"**Description**: {scenario.get('description', 'Aucune description')}")
                        st.markdown(f"**Localisation**: {scenario.get('localisation', 'Non spécifiée')}")
                        st.markdown(f"**Substance principale**: {scenario.get('substance_principale', 'Non spécifiée')}")
                        st.markdown(f"**Corps minéralisés**: {len(scenario['corps_mineralises'])}")
                        
                        if 'plan_forage' in scenario:
                            st.markdown("---")
                            st.markdown("**Plan de forage:**")
                            st.markdown(f"• Type de forage: {scenario['plan_forage']['type_forage']}")
                            st.markdown(f"• Budget total: {scenario['plan_forage']['budget_total']:,.0f} €")
                            st.markdown(f"• Durée estimée: {scenario['plan_forage']['duree_totale']:.0f} jours")
                    
                    with col2:
                        if st.button("Charger", key=f"load_{i}"):
                            st.session_state.current_scenario = scenario.copy()
                            st.success(f"Scénario '{scenario['nom']}' chargé!")
                            st.rerun()
                        
                        if st.button("Supprimer", key=f"delete_{i}"):
                            if st.session_state.current_scenario["id"] == scenario["id"]:
                                st.session_state.current_scenario = {
                                    "id": str(uuid.uuid4()),
                                    "nom": "Nouveau scénario",
                                    "date_creation": datetime.now().strftime("%Y-%m-%d"),
                                    "corps_mineralises": []
                                }
                            
                            st.session_state.scenarios.pop(i)
                            st.success(f"Scénario '{scenario['nom']}' supprimé!")
                            st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Exportation/importation des scénarios
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Exporter/Importer des scénarios")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Exporter tous les scénarios"):
                    json_str = json.dumps(st.session_state.scenarios, default=str, indent=4)
                    json_bytes = json_str.encode()
                    
                    st.download_button(
                        label="Télécharger les données (JSON)",
                        data=json_bytes,
                        file_name=f"scenarios_mineralest_{datetime.now().strftime('%Y%m%d')}.json",
                        mime="application/json"
                    )
            
            with col2:
                uploaded_file = st.file_uploader("Importer des scénarios", type=["json"])
                if uploaded_file is not None:
                    try:
                        imported_data = json.loads(uploaded_file.read())
                        if isinstance(imported_data, list):
                            # Ajouter les scénarios importés à ceux existants
                            st.session_state.scenarios.extend(imported_data)
                            st.success(f"{len(imported_data)} scénarios importés avec succès!")
                        else:
                            st.error("Format de fichier incorrect. Veuillez importer un fichier JSON contenant une liste de scénarios.")
                    except Exception as e:
                        st.error(f"Erreur lors de l'importation: {str(e)}")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Aucun scénario créé. Utilisez l'onglet 'Créer un scénario' pour commencer.")

# Page du guide utilisateur
elif selected == "Guide Utilisateur":
    st.markdown('<h1 class="main-header">Guide Utilisateur</h1>', unsafe_allow_html=True)
    
    # Table des matières
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Table des matières")
    st.markdown("""
    1. [Introduction](#introduction)
    2. [Création d'un scénario](#création-dun-scénario)
    3. [Définition des corps minéralisés](#définition-des-corps-minéralisés)
    4. [Estimation de ressources](#estimation-de-ressources)
    5. [Planification de forage](#planification-de-forage)
    6. [Gestion des scénarios](#gestion-des-scénarios)
    7. [Conseils et meilleures pratiques](#conseils-et-meilleures-pratiques)
    8. [FAQ](#faq)
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Section Introduction
    st.markdown('<h2 id="introduction" class="sub-header">1. Introduction</h2>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("""
    **Preliminary Explo Target Estimation** est un outil conçu pour aider les géologues et les professionnels de l'exploration minière à estimer rapidement les ressources minérales pendant les phases initiales d'exploration et à planifier efficacement les campagnes de forage.
    
    Cette application vous permet de:
    
    - Définir des corps minéralisés avec leurs caractéristiques géométriques et leur teneur
    - Estimer les ressources minérales en fonction de la maille de forage
    - Planifier des campagnes de forage initiales et détaillées
    - Évaluer le budget nécessaire pour les phases de forage
    - Visualiser les corps minéralisés et le plan de forage en 3D
    - Gérer différents scénarios pour comparer des approches alternatives
    
    L'application est particulièrement utile pour les phases d'exploration où les données sont limitées et où une estimation rapide est nécessaire pour prendre des décisions sur la poursuite des travaux d'exploration.
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Section Création d'un scénario
    st.markdown('<h2 id="création-dun-scénario" class="sub-header">2. Création d\'un scénario</h2>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("""
    Un scénario est un ensemble de corps minéralisés et de paramètres d'exploration que vous souhaitez étudier. Pour créer un nouveau scénario:
    
    1. Accédez à l'onglet **Scénarios** dans le menu principal
    2. Sélectionnez l'onglet **Créer un scénario**
    3. Remplissez les informations de base:
       - Nom du scénario
       - Description (optionnelle)
       - Localisation
       - Substance principale
       - Unité de mesure
    4. Cliquez sur **Créer ce scénario**
    
    Une fois le scénario créé, vous pouvez y ajouter des corps minéralisés dans l'onglet **Estimation de Ressources**.
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Section Définition des corps minéralisés
    st.markdown('<h2 id="définition-des-corps-minéralisés" class="sub-header">3. Définition des corps minéralisés</h2>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("""
    Les corps minéralisés sont modélisés comme des filons inclinés. Pour définir un corps minéralisé:
    
    1. Accédez à l'onglet **Estimation de Ressources**
    2. Dans la section **Ajouter un corps minéralisé**, renseignez les paramètres suivants:
    
       - **Nom du corps minéralisé**: Un identifiant unique
       - **Puissance (m)**: Plus grand allongement du filon dans son plan
       - **Épaisseur (m)**: Largeur perpendiculaire au plan du filon (ce que traverserait un forage)
       - **Profondeur (m)**: Extension en profondeur le long de l'inclinaison
       - **Teneur moyenne**: Teneur en métal/minéral
       - **Unité de teneur**: g/t pour l'or et l'argent, % pour les métaux de base
       - **Densité (t/m³)**: Densité du minerai
       - **Azimuth (°)**: Direction principale du filon (0° = Nord, 90° = Est)
       - **Inclinaison (°)**: Angle par rapport à l'horizontale
       - **Élévation du toit (m)**: Altitude du point le plus haut du corps minéralisé (valeur négative pour être sous terre)
    
    3. Cliquez sur **Ajouter ce corps minéralisé**
    
    Vous pouvez ajouter plusieurs corps minéralisés à un même scénario pour représenter différentes zones d'intérêt ou différents filons.
    """)
    
    # Exemple d'illustration pour les paramètres géométriques d'un filon
    st.markdown("### Paramètres géométriques des corps minéralisés")
    st.image("https://via.placeholder.com/800x400.png?text=Illustration+des+parametres+d'un+filon", 
            caption="Illustration des paramètres géométriques d'un corps minéralisé de type filon")
    st.markdown("""
    Dans cette modélisation:
    - **Puissance**: représente le plus grand allongement du filon dans sa direction principale
    - **Épaisseur**: représente la largeur perpendiculaire au plan du filon
    - **Profondeur**: représente l'extension du filon le long de son inclinaison
    - **Azimuth**: direction principale du filon (angle par rapport au Nord)
    - **Inclinaison**: pendage du filon par rapport à l'horizontale
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Section Estimation de ressources
    st.markdown('<h2 id="estimation-de-ressources" class="sub-header">4. Estimation de ressources</h2>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("""
    L'estimation des ressources est basée sur le volume des corps minéralisés, leur teneur et la maille de forage:
    
    1. Dans l'onglet **Estimation de Ressources**, après avoir défini au moins un corps minéralisé
    2. Spécifiez les paramètres de la maille de forage:
       - **Espacement en X (m)**: Distance entre les forages dans la direction X
       - **Espacement en Y (m)**: Distance entre les forages dans la direction Y
    
    3. Configurez les paramètres de classification:
       - **Maille max. pour ressources mesurées**
       - **Maille max. pour ressources indiquées**
       - **Facteurs de confiance** pour chaque catégorie
    
    4. L'application calculera automatiquement:
       - Le volume de chaque corps minéralisé
       - Le tonnage brut et ajusté (selon le facteur de confiance)
       - La quantité de métal/minéral
       - La classification des ressources (mesurées, indiquées, inférées)
    
    La classification des ressources est déterminée par la maille de forage selon les valeurs que vous avez définies.
    """)
    
    st.markdown("### Formules utilisées dans l'estimation")
    st.markdown("""
    - **Volume (m³)** = Puissance (m) × Épaisseur (m) × Profondeur (m)
    - **Tonnage brut (t)** = Volume (m³) × Densité (t/m³)
    - **Tonnage ajusté (t)** = Tonnage brut (t) × Facteur de confiance
    
    Pour les métaux précieux (or, argent):
    - **Quantité de métal (oz)** = Tonnage ajusté (t) × Teneur (g/t) ÷ 31.1035
    
    Pour les métaux de base:
    - **Quantité de métal (t)** = Tonnage ajusté (t) × Teneur (%) ÷ 100
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Section Planification de forage
    st.markdown('<h2 id="planification-de-forage" class="sub-header">5. Planification de forage</h2>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("""
    La planification de forage vous permet de concevoir une campagne en deux phases et d'estimer son coût:
    
    1. Accédez à l'onglet **Planification de Forage**
    2. Configurez les paramètres de la campagne:
       - **Type de forage**: Carottage diamanté (DDH) ou Circulation inverse (RC)
       - **Maille initiale**: Espacement des forages pour la phase initiale
       - **Maille détaillée**: Espacement resserré pour la phase détaillée
       - **Coûts**: Coût par mètre foré, mobilisation, analyses
       - **Paramètres des échantillons**: Longueur moyenne des échantillons
       
    3. Configurez l'orientation des forages:
       - **Azimuth des forages**: Direction des forages
       - **Inclinaison des forages**: Angle par rapport à la verticale
       - **Profondeur max. des forages**: Longueur maximale des forages
    
    4. Sélectionnez les corps minéralisés à inclure dans la campagne
    
    L'application générera:
    - Un plan de forage avec le nombre de forages et le métrage pour chaque phase
    - Une estimation détaillée des coûts
    - Une visualisation 3D du plan de forage
    - Un échéancier prévisionnel
    
    Les forages sont planifiés pour traverser les corps minéralisés de type filon de façon optimale, en tenant compte de leur orientation (azimuth et inclinaison).
    """)
    
    st.markdown("### Stratégie de forage recommandée")
    st.markdown("""
    1. **Phase initiale**: Utiliser une maille large (100-200m) pour identifier et délimiter les filons
    2. **Phase détaillée**: Resserrer la maille (25-50m) dans les zones d'intérêt pour améliorer la confiance dans l'estimation
    
    Pour les filons inclinés, il est souvent optimal de:
    - Orienter les forages perpendiculairement au plan du filon quand c'est possible
    - Prévoir des forages suffisamment profonds pour traverser complètement le filon à son extension maximale
    - Utiliser une maille plus resserrée le long de la direction de la puissance, car c'est souvent l'axe de plus grande variabilité
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Section Gestion des scénarios
    st.markdown('<h2 id="gestion-des-scénarios" class="sub-header">6. Gestion des scénarios</h2>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("""
    L'onglet **Scénarios** vous permet de gérer vos différents scénarios d'exploration:
    
    - **Créer** de nouveaux scénarios
    - **Charger** un scénario existant pour le modifier ou l'utiliser
    - **Supprimer** les scénarios obsolètes
    - **Exporter** vos scénarios pour les sauvegarder ou les partager
    - **Importer** des scénarios créés par d'autres utilisateurs
    
    Utiliser plusieurs scénarios vous permet de:
    - Comparer différentes hypothèses géologiques
    - Évaluer l'impact de différentes mailles de forage
    - Tester différentes stratégies d'exploration
    - Préparer des budgets alternatifs
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Section Conseils et meilleures pratiques
    st.markdown('<h2 id="conseils-et-meilleures-pratiques" class="sub-header">7. Conseils et meilleures pratiques</h2>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("""
    ### Pour l'estimation des ressources:
    
    - Utilisez des paramètres conservateurs pour la teneur et les dimensions des filons
    - Tenez compte de la continuité géologique dans la définition des corps
    - Divisez les zones complexes en plusieurs filons simples
    - Vérifiez que la densité utilisée correspond bien au type de mineralisation
    
    ### Pour la planification de forage:
    
    - Adaptez l'espacement de la maille à la complexité géologique et à la continuité du filon
    - Orientez les forages perpendiculairement aux corps pour minimiser la longueur nécessaire
    - Pour les filons à fort pendage, préférez des forages inclinés
    - Tenez compte de la topographie du site pour les collars des forages
    
    ### Pour les filons minéralisés:
    
    - Les filons épais (>10m) peuvent nécessiter plusieurs forages à différentes profondeurs
    - Les filons à teneur variable peuvent demander une maille plus serrée
    - Considérez les structures géologiques qui peuvent décaler ou interrompre les filons
    - Pour les gisements filoniens multiples, planifiez les forages pour tester plusieurs filons avec un même forage quand c'est possible
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Section FAQ
    st.markdown('<h2 id="faq" class="sub-header">8. FAQ</h2>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    faq_items = [
        ("Comment définir correctement les paramètres d'un filon?", 
         """Pour un filon:
         - La **puissance** est le plus grand allongement dans la direction principale du filon
         - L'**épaisseur** est la largeur perpendiculaire au plan du filon
         - La **profondeur** est l'extension le long de l'inclinaison du filon
         - L'**inclinaison** est l'angle du filon par rapport à l'horizontale (pendage)
         - L'**azimuth** est la direction principale du filon (angle par rapport au Nord)"""),
        
        ("Quelle précision puis-je attendre des estimations?", 
         """Les estimations fournies sont sommaires et adaptées aux phases préliminaires d'exploration. 
         La précision dépend de la qualité des données d'entrée et de la complexité géologique. 
         Typiquement, attendez-vous à une marge d'erreur de ±30% pour les ressources inférées."""),
        
        ("Comment intégrer des données réelles de forage?", 
         """L'application actuelle n'importe pas directement les données de forage. 
         Vous devez utiliser ces données pour définir les paramètres des corps minéralisés 
         (dimensions, teneur, etc.) puis les saisir manuellement."""),
        
        ("L'application prend-elle en compte la variabilité de la teneur?", 
         """Non, l'application utilise une teneur moyenne pour chaque corps minéralisé. 
         Pour tenir compte de la variabilité, vous pouvez créer plusieurs scénarios 
         avec différentes hypothèses de teneur ou ajuster le facteur de confiance."""),
        
        ("Comment estimer la densité si je n'ai pas de mesures?", 
         """Vous pouvez utiliser des valeurs typiques selon le type de roche et de minéralisation:
         - Roches sédimentaires: 2.2-2.6 t/m³
         - Roches ignées felsiques: 2.5-2.8 t/m³
         - Roches ignées mafiques: 2.8-3.1 t/m³
         - Minéralisation sulfurée massive: 3.5-4.5 t/m³
         - Minéralisation disséminée: 2.7-3.0 t/m³"""),
        
        ("Les coûts de forage sont-ils réalistes?", 
         """Les coûts de forage varient considérablement selon la région, l'accessibilité, 
         la profondeur et les conditions du terrain. Les valeurs par défaut sont indicatives 
         et doivent être ajustées en fonction de votre contexte spécifique et des devis des prestataires."""),
        
        ("Puis-je utiliser cette application pour des rapports officiels?", 
         """Cette application est conçue comme un outil d'aide à la décision pour les phases 
         préliminaires d'exploration. Les estimations qu'elle fournit ne sont pas conformes 
         aux codes comme le JORC, NI 43-101 ou PERC, qui nécessitent des procédures plus rigoureuses 
         et la supervision d'une personne qualifiée.""")
    ]
    
    for question, answer in faq_items:
        with st.expander(question):
            st.markdown(answer)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # À propos de l'auteur
    st.markdown('<h2 class="sub-header">À propos de l\'auteur</h2>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.image("https://via.placeholder.com/200x200.png?text=Photo", width=150)
    
    with col2:
        st.markdown("### Didier Ouedraogo, P.Geo.")
        st.markdown("""
        Expert en géologie minière et exploration avec plus de 20 ans d'expérience dans le développement de méthodes d'estimation de ressources et la planification de campagnes de forage.
        
        Spécialiste de l'exploration aurifère en Afrique de l'Ouest et au Moyen Orient, Didier a travaillé sur de nombreux projets d'exploration, de la phase initiale jusqu'à l'étude de faisabilité.
        
        Cette application a été développée pour partager son expertise et aider les géologues d'exploration à optimiser leurs programmes de forage et à mieux estimer les ressources minérales potentielles dès les premières phases d'exploration.
        
        *Pour toute question ou suggestion d'amélioration, n'hésitez pas à contacter l'auteur.*
        """)
    st.markdown('</div>', unsafe_allow_html=True)

# Pied de page
st.markdown('<div class="footer">', unsafe_allow_html=True)
st.markdown(f"Preliminary Explo Target Estimation © 2025 | Développé par Didier Ouedraogo, P.Geo. | Version 1.2.0 | Dernière mise à jour: 10/04/2025", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)