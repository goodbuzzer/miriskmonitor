import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# -------------------------------------------------------
# CONFIGURATION DE LA PAGE
# -------------------------------------------------------
st.set_page_config(
    page_title="Veille Sécuritaire Cameroun",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------
# CHARGEMENT DES STYLES CSS EXTERNES
# -------------------------------------------------------
@st.cache_data
def load_css(file_path="style.css"):
    """Charge le fichier CSS externe"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            css = f.read()
        return css
    except FileNotFoundError:
        st.warning(f"⚠️ Fichier CSS '{file_path}' non trouvé. Styles par défaut utilisés.")
        return ""

# Charger et appliquer les styles CSS
css_content = load_css()
if css_content:
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

# -------------------------------------------------------
# CHARGEMENT DES DONNÉES PAR DATE
# -------------------------------------------------------
@st.cache_data
def load_security_data_by_date():
    """Charge les données de sécurité organisées par date"""
    file_path = "security_data.json"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Vérifier si les données sont déjà structurées par date
        # Si la première clé est une date (format YYYY-MM-DD)
        first_key = list(data.keys())[0] if data else ""
        
        if first_key and len(first_key) == 10 and first_key[4] == '-' and first_key[7] == '-':
            # Structure déjà par date
            return data
        else:
            # Structure simple (ancien format) - créer une date unique
            today = datetime.now().strftime("%Y-%m-%d")
            return {today: data}
    
    except FileNotFoundError:
        st.error("⚠️ Fichier security_data.json non trouvé")
        return {}

@st.cache_data
def load_risk_data():
    """Charge les données de risque depuis risque.json"""
    file_path = "risque.json"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        st.warning("⚠️ Fichier risque.json non trouvé. Calcul automatique utilisé.")
        return {}

@st.cache_data
def load_geodata():
    geojson_file = "geoBoundaries-CMR-ADM1_simplified.geojson"
    try:
        return gpd.read_file(geojson_file)
    except FileNotFoundError:
        st.error("⚠️ Fichier GeoJSON non trouvé")
        return None

all_security_data = load_security_data_by_date()
risk_data = load_risk_data()
gdf = load_geodata()

# Obtenir la liste des dates disponibles
available_dates = sorted(all_security_data.keys(), reverse=True)

# -------------------------------------------------------
# FONCTIONS D'ANALYSE
# -------------------------------------------------------
def calculate_alert_level(region_data, region_name="", date_str=""):
    """Calcule le niveau d'alerte basé sur risque.json ou les indicateurs"""
    
    # Essayer d'abord de lire depuis risque.json
    if date_str and region_name and date_str in risk_data and region_name in risk_data[date_str]:
        level_fr = risk_data[date_str][region_name]
        
        # Convertir le niveau français en format standard
        if level_fr == "Élevé":
            return "Élevé", "🔴", "#d32f2f"
        elif level_fr == "Moyen":
            return "Moyen", "🟡", "#f57c00"
        elif level_fr == "Faible":
            return "Faible", "🟢", "#388e3c"
    
    # Si pas trouvé dans risque.json, utiliser l'ancien calcul
    score = 0
    situation = region_data.get('Situation générale', '').lower()
    activites = region_data.get('Activités économiques', '').lower()
    couvre_feu = region_data.get('Couvre-feu', '').lower()
    
    # Analyse de la situation
    if 'tendu' in situation or 'pillage' in situation:
        score += 3
    elif 'ghost town' in situation:
        score += 4
    elif 'ras' in situation or 'calme' in situation:
        score += 0
    else:
        score += 1
    
    # Analyse des activités économiques
    if 'fermé' in activites or 'ralenti' in activites or 'vide' in activites:
        score += 2
    elif 'variable' in activites:
        score += 1
    
    # Analyse du couvre-feu
    if 'interdiction' in couvre_feu or 'ghost town' in couvre_feu:
        score += 2
    
    # Détermination du niveau
    if score >= 5:
        return "Élevé", "🔴", "#d32f2f"
    elif score >= 2:
        return "Moyen", "🟡", "#f57c00"
    else:
        return "Faible", "🟢", "#388e3c"

def create_statistics_dataframe(data, date_str=""):
    """Crée un DataFrame pour l'analyse statistique"""
    rows = []
    for region, info in data.items():
        level, icon, color = calculate_alert_level(info, region, date_str)
        rows.append({
            'Région': region,
            'Niveau d\'alerte': level,
            'Icône': icon,
            'Situation': info.get('Situation générale', 'N/A'),
            'Activités': info.get('Activités économiques', 'N/A'),
            'Circulation': info.get('Circulation', 'N/A'),
            'Couvre-feu': info.get('Couvre-feu', 'N/A')
        })
    return pd.DataFrame(rows)

# -------------------------------------------------------
st.markdown('<div class="main-header">🛡️ Veille Sécuritaire – Cameroun Post-Scrutin Présidentiel</div>', 
            unsafe_allow_html=True)

# -------------------------------------------------------
# SIDEBAR - SÉLECTEUR DE DATE ET FILTRES
# -------------------------------------------------------
# Logo et lien (si le fichier logo existe)
try:
    st.sidebar.image('LogoMIRiskMonitor.png')
    st.sidebar.markdown("[CABINET MEDIA INTELLIGENCE](https://www.mediaintelligence.fr/)")
except:
    st.sidebar.markdown("### 🛡️ Media Intelligence")
    st.sidebar.markdown("[mediaintelligence.fr](https://www.mediaintelligence.fr/)")

st.sidebar.title("🎛️ Panneau de Contrôle")
st.sidebar.markdown("---")

# ======================================================
# 📅 SÉLECTEUR DE DATE - NOUVEAU !
# ======================================================
st.sidebar.subheader("📅 Sélection de la Date")

if available_dates:
    # Convertir les dates en objets datetime pour le sélecteur
    date_objects = [datetime.strptime(d, "%Y-%m-%d").date() for d in available_dates]
    
    # Sélecteur de date avec la date la plus récente par défaut
    selected_date_obj = st.sidebar.date_input(
        "Choisir une date",
        value=date_objects[0],  # Date la plus récente par défaut
        min_value=min(date_objects),
        max_value=max(date_objects),
        format="DD/MM/YYYY"
    )
    
    # Convertir la date sélectionnée en string au format YYYY-MM-DD
    selected_date = selected_date_obj.strftime("%Y-%m-%d")
    
    # Afficher les informations sur la date
    if selected_date in available_dates:
        st.sidebar.success(f"✅ Données disponibles")
    else:
        st.sidebar.error(f"❌ Pas de données pour cette date")
        # Trouver la date la plus proche
        closest_date = min(available_dates, key=lambda d: abs(
            datetime.strptime(d, "%Y-%m-%d") - datetime.strptime(selected_date, "%Y-%m-%d")
        ))
        st.sidebar.info(f"📍 Date la plus proche : {datetime.strptime(closest_date, '%Y-%m-%d').strftime('%d/%m/%Y')}")
        selected_date = closest_date
    
    # Afficher le nombre de jours de données disponibles
    st.sidebar.info(f"📊 {len(available_dates)} jour(s) de données disponibles")
    
    # Bouton pour voir toutes les dates
    with st.sidebar.expander("📋 Voir toutes les dates"):
        for date_str in available_dates:
            date_formatted = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
            st.write(f"• {date_formatted}")

else:
    st.sidebar.error("❌ Aucune donnée disponible")
    selected_date = datetime.now().strftime("%Y-%m-%d")

st.sidebar.markdown("---")

# Récupérer les données pour la date sélectionnée
security_data = all_security_data.get(selected_date, {})

if not security_data:
    st.error(f"⚠️ Aucune donnée disponible pour le {datetime.strptime(selected_date, '%Y-%m-%d').strftime('%d/%m/%Y')}")
    st.stop()

# Afficher la date sélectionnée dans le titre
date_display = datetime.strptime(selected_date, "%Y-%m-%d").strftime("%d/%m/%Y")
st.markdown(f'<div class="timestamp">📅 Situation au : {date_display}</div>', 
            unsafe_allow_html=True)

# -------------------------------------------------------
# SUITE DES FILTRES SIDEBAR
# -------------------------------------------------------
# Filtre par niveau d'alerte
st.sidebar.subheader("Filtrer par niveau d'alerte")
show_high = st.sidebar.checkbox("🔴 Alerte Élevée", value=True)
show_medium = st.sidebar.checkbox("🟡 Alerte Moyenne", value=True)
show_low = st.sidebar.checkbox("🟢 Alerte Faible", value=True)

st.sidebar.markdown("---")

# Sélection des régions
st.sidebar.subheader("Sélectionner les régions")
all_regions = list(security_data.keys())
selected_regions = st.sidebar.multiselect(
    "Choisir les régions à afficher",
    options=all_regions,
    default=all_regions
)

st.sidebar.markdown("---")

# Options d'affichage
st.sidebar.subheader("Options d'affichage")
show_map = st.sidebar.checkbox("Afficher la carte", value=True)
show_stats = st.sidebar.checkbox("Afficher les statistiques", value=True)
show_comparison = st.sidebar.checkbox("Comparer avec d'autres dates", value=False)
show_table = st.sidebar.checkbox("Afficher le tableau détaillé", value=True)

# -------------------------------------------------------
# MÉTRIQUES PRINCIPALES
# -------------------------------------------------------
st.subheader("📊 Vue d'Ensemble Nationale")

# Charger les Top Stories depuis le fichier JSON
with open("top_stories.json", "r", encoding="utf-8") as f:
    top_stories_data = json.load(f)

# Récupérer les Top Stories pour la date sélectionnée
top_stories = top_stories_data.get(selected_date, {})

with st.expander(f"📰 Top Stories ({date_display})", expanded=True):
    if top_stories:
        st.markdown(f"**Top Stories pour le {date_display} :**")
        st.write(top_stories)
    else:
        st.info(f"Aucune rubrique 'Top Stories' disponible pour le {date_display}.")


df_stats = create_statistics_dataframe(security_data, selected_date)

# Filtrer selon les critères
filtered_df = df_stats[df_stats['Région'].isin(selected_regions)]
if not show_high:
    filtered_df = filtered_df[filtered_df["Niveau d'alerte"] != "Élevé"]
if not show_medium:
    filtered_df = filtered_df[filtered_df["Niveau d'alerte"] != "Moyen"]
if not show_low:
    filtered_df = filtered_df[filtered_df["Niveau d'alerte"] != "Faible"]

# Calcul des métriques
total_regions = len(filtered_df)
alert_high_df = filtered_df[filtered_df["Niveau d'alerte"] == "Élevé"]
alert_medium_df = filtered_df[filtered_df["Niveau d'alerte"] == "Moyen"]
alert_low_df = filtered_df[filtered_df["Niveau d'alerte"] == "Faible"]

alert_high = len(alert_high_df)
alert_medium = len(alert_medium_df)
alert_low = len(alert_low_df)

# Affichage des métriques en colonnes
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Régions surveillées",
        value=total_regions,
        delta=None
    )

with col2:
    st.metric(
        label="🔴 Alerte Élevée",
        value=f"{alert_high} régions",
        delta=f"{(alert_high/total_regions*100):.0f}%" if total_regions > 0 else "0%",
        delta_color="inverse"
    )
    if alert_high > 0:
        st.caption(", ".join(alert_high_df["Région"].tolist()))

with col3:
    st.metric(
        label="🟡 Alerte Moyenne",
        value=f"{alert_medium} régions",
        delta=f"{(alert_medium/total_regions*100):.0f}%" if total_regions > 0 else "0%",
        delta_color="off"
    )
    if alert_medium > 0:
        st.caption(", ".join(alert_medium_df["Région"].tolist()))

with col4:
    st.metric(
        label="🟢 Alerte Faible",
        value=f"{alert_low} régions",
        delta=f"{(alert_low/total_regions*100):.0f}%" if total_regions > 0 else "0%",
        delta_color="normal"
    )
    if alert_low > 0:
        st.caption(", ".join(alert_low_df["Région"].tolist()))


with st.expander("Infos sur les niveaux d'alerte"):
    st.markdown("""
    🔴 **Élevé** : Situation critique, intervention urgente requise.  
    🟡 **Moyen** : Situation à surveiller, vigilance nécessaire.  
    🟢 **Faible** : Situation normale, pas de risque immédiat.
    """)


st.markdown("---")

# -------------------------------------------------------
# COMPARAISON ENTRE DATES (NOUVEAU)
# -------------------------------------------------------
if show_comparison and len(available_dates) > 1:
    st.subheader("📊 Évolution Temporelle")
    
    # Sélection des dates à comparer
    st.markdown("**Comparer avec :**")
    comparison_dates = st.multiselect(
        "Sélectionner d'autres dates",
        options=[d for d in available_dates if d != selected_date],
        default=[available_dates[min(1, len(available_dates)-1)]]  # Deuxième date par défaut
    )
    
    if comparison_dates:
        # Créer un DataFrame pour la comparaison
        comparison_data = []
        
        # Ajouter la date actuelle
        for region in selected_regions:
            if region in security_data:
                level, _, _ = calculate_alert_level(security_data[region], region, selected_date)
                comparison_data.append({
                    'Date': datetime.strptime(selected_date, "%Y-%m-%d").strftime("%d/%m/%Y"),
                    'Région': region,
                    'Niveau': level
                })
        
        # Ajouter les dates de comparaison
        for comp_date in comparison_dates:
            comp_data = all_security_data.get(comp_date, {})
            for region in selected_regions:
                if region in comp_data:
                    level, _, _ = calculate_alert_level(comp_data[region], region, comp_date)
                    comparison_data.append({
                        'Date': datetime.strptime(comp_date, "%Y-%m-%d").strftime("%d/%m/%Y"),
                        'Région': region,
                        'Niveau': level
                    })
        
        comparison_df = pd.DataFrame(comparison_data)
        
        # Graphique de comparaison
        fig_comparison = px.bar(
            comparison_df,
            x="Région",
            y="Niveau",
            color="Date",
            barmode="group",
            title="Comparaison des Niveaux d'Alerte entre Dates",
            category_orders={"Niveau": ["Faible", "Moyen", "Élevé"]}
        )
        st.plotly_chart(fig_comparison, width='stretch')
    
    st.markdown("---")

# -------------------------------------------------------
# GRAPHIQUES STATISTIQUES
# -------------------------------------------------------
if show_stats:
    st.subheader("📈 Analyse Statistique")
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        # Graphique de répartition des niveaux d'alerte
        alert_counts = filtered_df["Niveau d'alerte"].value_counts()
        fig_pie = px.pie(
            values=alert_counts.values,
            names=alert_counts.index,
            title="Répartition des Niveaux d'Alerte",
            color=alert_counts.index,
            color_discrete_map={
                "Élevé": "#d32f2f",
                "Moyen": "#f57c00",
                "Faible": "#388e3c"
            }
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, width='stretch')
    
    with col_chart2:
        # Graphe d'évolution du risque par région (d'après risque.json)
        if not risk_data:
            st.info("⚠️ Pas de données dans risque.json pour afficher l'évolution.")
        else:
            rows = []
            # Trier les dates chronologiquement
            sorted_dates = sorted(risk_data.keys())
            score_map = {"Faible": 1, "Moyen": 2, "Élevé": 3}

            # Afficher uniquement ces régions (si elles existent)
            target_regions = ["Far North", "Littoral", "Centre", "North", "West"]
            # Respecter la sélection utilisateur si possible, sinon tomber back sur les régions présentes dans risque.json
            regions_to_plot = [r for r in target_regions if r in selected_regions]
            if not regions_to_plot:
                regions_to_plot = [r for r in target_regions if any(r in risk_data.get(d, {}) for d in sorted_dates)]

            for date_str in sorted_dates:
                for region in regions_to_plot:
                    level = risk_data.get(date_str, {}).get(region)
                    if level:
                        try:
                            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                        except Exception:
                            date_obj = date_str
                        rows.append({
                            "Date": date_obj,
                            "Région": region,
                            "Niveau": level,
                            "Score": score_map.get(level, None)
                        })

            if len(rows) == 0:
                st.info("ℹ️ Aucune donnée d'évolution pour les régions sélectionnées.")
            else:
                evo_df = pd.DataFrame(rows)
                evo_df = evo_df.sort_values("Date")

                fig_evo = px.line(
                    evo_df,
                    x="Date",
                    y="Score",
                    color="Région",
                    line_shape="spline",
                    markers=True,
                    title="Évolution du niveau de risque par région (sélection restreinte)",
                    hover_data=["Niveau"]
                )

                # Afficher labels lisibles pour l'axe Y
                fig_evo.update_yaxes(
                    tickmode="array",
                    tickvals=[1, 2, 3],
                    ticktext=["Faible", "Moyen", "Élevé"],
                    range=[0.8, 3.2]
                )

                fig_evo.update_layout(hovermode="x unified", legend_title_text="Région")
                st.plotly_chart(fig_evo, width='stretch')
    
    # Analyse des couvre-feux
    st.subheader("🌙 Analyse des Couvre-feux")
    couvre_feu_active = filtered_df[filtered_df['Couvre-feu'].str.lower() != 'ras']
    
    if len(couvre_feu_active) > 0:
        st.info(f"⚠️ {len(couvre_feu_active)} région(s) avec restrictions de circulation nocturne")
        
        for _, row in couvre_feu_active.iterrows():
            st.markdown(f"**{row['Région']}** : {row['Couvre-feu']}")
    else:
        st.success("✅ Aucune restriction de circulation nocturne en vigueur")
    
    st.markdown("---")

# -------------------------------------------------------
# CARTE INTERACTIVE
# -------------------------------------------------------
if show_map and gdf is not None:
    st.subheader("🗺️ Carte Interactive de la Situation Sécuritaire")
    
    st.markdown(f"""
    <div class="info-box">
    <b>Instructions :</b> Survolez ou cliquez sur une région pour voir les détails de la situation sécuritaire au {date_display}.
    Les couleurs indiquent le niveau d'alerte : Rouge (Élevé), Orange (Moyen), Vert (Faible)
    </div>
    """, unsafe_allow_html=True)
    
    # Fonction pour créer le tooltip enrichi
    def build_enhanced_tooltip(region):
        d = security_data.get(region, {})
        level, icon, color = calculate_alert_level(d, region, selected_date)
        
        return (
            f"<div style='font-family: Arial; min-width: 250px;'>"
            f"<h4 style='margin:0; color:{color};'>{icon} {region}</h4>"
            f"<p style='margin:5px 0; font-size:0.9em; color:#666;'>{date_display}</p>"
            f"<hr style='margin: 5px 0;'>"
            f"<b>Niveau d'alerte :</b> <span style='color:{color};'>{level}</span><br><br>"
            f"<b>🏛️ Situation générale :</b><br>{d.get('Situation générale', 'N/A')}<br><br>"
            f"<b>💼 Activités économiques :</b><br>{d.get('Activités économiques', 'N/A')}<br><br>"
            f"<b>🚗 Circulation :</b><br>{d.get('Circulation', 'N/A')}<br><br>"
            f"<b>🌙 Couvre-feu :</b><br>{d.get('Couvre-feu', 'N/A')}"
            f"</div>"
        )
    
    # Fonction pour déterminer la couleur de la région
    def get_region_color(region):
        d = security_data.get(region, {})
        level, _, color = calculate_alert_level(d, region, selected_date)
        return color
    
    gdf["tooltip"] = gdf["shapeName"].apply(build_enhanced_tooltip)
    gdf["alert_color"] = gdf["shapeName"].apply(get_region_color)
    
    # Filtrer le GeoDataFrame selon les sélections
    gdf_filtered = gdf[gdf["shapeName"].isin(selected_regions)]
    
    # Création de la carte
    m = folium.Map(
        location=[7, 12],
        zoom_start=6,
        tiles='CartoDB positron',
        name='CartoDB Positron'
    )
    
    # Ajout des autres couches (optionnelles)
    folium.TileLayer('CartoDB dark_matter', name='CartoDB Dark').add_to(m)
    folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(m)
    
    # Ajout des régions avec couleurs dynamiques
    for idx, row in gdf_filtered.iterrows():
        folium.GeoJson(
            row['geometry'],
            style_function=lambda x, color=row['alert_color']: {
                "fillColor": color,
                "color": "black",
                "weight": 2,
                "fillOpacity": 0.5
            },
            highlight_function=lambda x: {
                "weight": 4,
                "color": "blue",
                "fillOpacity": 0.7
            },
            tooltip=folium.Tooltip(row['tooltip'], sticky=True)
        ).add_to(m)

    
    # Ajout d'une légende
    legend_html = f'''
    <div style="position: fixed; 
                bottom: 50px; right: 50px; width: 200px; height: 140px; 
                background-color: white; z-index:9999; font-size:14px;
                border:2px solid grey; border-radius: 5px; padding: 10px">
    <p style="margin:0; font-weight:bold;">Niveau d'alerte</p>
    <p style="margin:3px 0; font-size:11px; color:#666;">{date_display}</p>
    <p style="margin:5px 0;"><span style="color:#d32f2f;">⬤</span> Élevé</p>
    <p style="margin:5px 0;"><span style="color:#f57c00;">⬤</span> Moyen</p>
    <p style="margin:5px 0;"><span style="color:#388e3c;">⬤</span> Faible</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Ajout du contrôle de couches
    folium.LayerControl().add_to(m)
    
    # Affichage de la carte
    st_folium(m, height=600, width=None, returned_objects=[])
    
    st.markdown("---")

# -------------------------------------------------------
# TABLEAU DÉTAILLÉ
# -------------------------------------------------------
if show_table:
    st.subheader("📋 Tableau Détaillé par Région")
    
    # Préparation du DataFrame pour l'affichage
    display_df = filtered_df.copy()
    display_df = display_df[['Icône', 'Région', "Niveau d'alerte", 'Situation', 'Activités', 'Circulation', 'Couvre-feu']]
    
    # Fonction pour colorer les lignes selon le niveau d'alerte
    def highlight_alert(row):
        if row["Niveau d'alerte"] == "Élevé":
            return ['background-color: #ffebee'] * len(row)
        elif row["Niveau d'alerte"] == "Moyen":
            return ['background-color: #fff3e0'] * len(row)
        else:
            return ['background-color: #e8f5e9'] * len(row)
    
    styled_df = display_df.style.apply(highlight_alert, axis=1)
    st.dataframe(styled_df, width='stretch', height=400)
    
    # Bouton d'export
    csv = display_df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label=f"📥 Télécharger les données ({date_display})",
        data=csv,
        file_name=f'veille_securitaire_{selected_date}.csv',
        mime='text/csv',
    )

# -------------------------------------------------------
# ALERTES PRIORITAIRES
# -------------------------------------------------------
st.markdown("---")
st.subheader("⚠️ Alertes Prioritaires")

high_alerts = filtered_df[filtered_df["Niveau d'alerte"] == "Élevé"]

if len(high_alerts) > 0:
    st.error(f"🚨 {len(high_alerts)} région(s) en alerte élevée le {date_display}")
    
    for _, alert in high_alerts.iterrows():
        with st.expander(f"🔴 {alert['Région']} - ALERTE ÉLEVÉE"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**Situation :** {alert['Situation']}")
                st.markdown(f"**Activités économiques :** {alert['Activités']}")
            
            with col2:
                st.markdown(f"**Circulation :** {alert['Circulation']}")
                st.markdown(f"**Couvre-feu :** {alert['Couvre-feu']}")
else:
    st.success(f"✅ Aucune région en alerte élevée le {date_display}")

# -------------------------------------------------------
# FOOTER
# -------------------------------------------------------
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p>🛡️ Système de Veille Sécuritaire - Cameroun</p>
    <p style='font-size: 0.9rem;'>Données actualisées en temps réel | Media Intelligence 2025</p>
</div>
""", unsafe_allow_html=True)

