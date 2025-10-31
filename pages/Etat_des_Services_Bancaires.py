# streamlit_page_name: Banque
# streamlit_page_icon: 🏦


import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import matplotlib.pyplot as plt



# -------------------------------------------------------
# CONFIGURATION DE LA PAGE
# -------------------------------------------------------
st.set_page_config(
    page_title="État des Services Bancaires",
    page_icon="🏦",
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
# CHARGEMENT DES DONNÉES BANCAIRES
# -------------------------------------------------------
@st.cache_data(ttl=300)  # Cache de 5 minutes
def load_banking_data():
    """Charge les données bancaires depuis Google Sheets"""
    url = "https://docs.google.com/spreadsheets/d/1axXyNLPZYsJis_gdxQi6XBZ_6TFvwxqH9iN-3QgABHc/export?format=csv&gid=0"
    
    try:
        df = pd.read_csv(url)
        
        # Nettoyage des données
        df['Date'] = pd.to_datetime(df['Date'])
        df['Ouvert'] = df['Ouvert'].str.strip().str.lower().map({'oui': 'Oui', 'non': 'Non'})
        
        return df
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement des données : {e}")
        return pd.DataFrame()

# Charger les données
df_banking = load_banking_data()

# -------------------------------------------------------
# HEADER
# -------------------------------------------------------
st.markdown('<div class="main-header">🏦 État des Services Bancaires </div>', 
            unsafe_allow_html=True)

if not df_banking.empty:
    # Dernière date de mise à jour
    last_update = df_banking['Date'].max().strftime("%d/%m/%Y")
    st.markdown(f'<div class="timestamp">📅 Données du : {last_update}</div>', 
                unsafe_allow_html=True)
else:
    st.error("⚠️ Aucune donnée disponible")
    st.stop()

# -------------------------------------------------------
# SIDEBAR - FILTRES
# -------------------------------------------------------
try:
    st.sidebar.image('LogoMIRiskMonitor.png')
    st.sidebar.markdown("[MEDIA INTELLIGENCE](https://www.mediaintelligence.fr/)")
except:
    st.sidebar.markdown("### 🏦 Media Intelligence")
    st.sidebar.markdown("[mediaintelligence.fr](https://www.mediaintelligence.fr/)")

st.sidebar.title("🎛️ Filtres")
st.sidebar.markdown("---")

# Filtre par date
available_dates = sorted(df_banking['Date'].dt.date.unique(), reverse=True)
selected_date = st.sidebar.selectbox(
    "📅 Sélectionner une date",
    options=available_dates,
    format_func=lambda x: x.strftime("%d/%m/%Y")
)

# Filtrer les données par date
df_filtered = df_banking[df_banking['Date'].dt.date == selected_date].copy()

st.sidebar.markdown("---")

# Filtre par ville
all_cities = ['Toutes'] + sorted(df_filtered['Ville'].unique().tolist())
selected_city = st.sidebar.selectbox(
    "🏙️ Sélectionner une ville",
    options=all_cities
)

if selected_city != 'Toutes':
    df_filtered = df_filtered[df_filtered['Ville'] == selected_city]

st.sidebar.markdown("---")

# Filtre par statut
status_filter = st.sidebar.radio(
    "🔍 Filtrer par statut",
    options=['Tous', 'Ouverts uniquement', 'Fermés uniquement']
)

if status_filter == 'Ouverts uniquement':
    df_filtered = df_filtered[df_filtered['Ouvert'] == 'Oui']
elif status_filter == 'Fermés uniquement':
    df_filtered = df_filtered[df_filtered['Ouvert'] == 'Non']

# -------------------------------------------------------
# MÉTRIQUES PRINCIPALES
# -------------------------------------------------------
st.subheader("📊 Vue d'Ensemble")

# Calcul des statistiques
total_banks = len(df_filtered)
banks_open = len(df_filtered[df_filtered['Ouvert'] == 'Oui'])
banks_closed = len(df_filtered[df_filtered['Ouvert'] == 'Non'])
opening_rate = (banks_open / total_banks * 100) if total_banks > 0 else 0

# Affichage des métriques
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Total Établissements",
        value=total_banks,
        delta=None
    )

with col2:
    st.metric(
        label="🟢 Ouverts",
        value=banks_open,
        delta=f"{opening_rate:.1f}%",
        delta_color="normal"
    )

with col3:
    st.metric(
        label="🔴 Fermés",
        value=banks_closed,
        delta=f"{(banks_closed/total_banks*100):.1f}%" if total_banks > 0 else "0%",
        delta_color="inverse"
    )

with col4:
    # Taux d'ouverture global
    color_status = "🟢" if opening_rate >= 70 else "🟡" if opening_rate >= 40 else "🔴"
    st.metric(
        label=f"{color_status} Taux d'ouverture",
        value=f"{opening_rate:.1f}%",
        delta=None
    )

st.markdown("---")

# -------------------------------------------------------
# STATISTIQUES PAR VILLE
# -------------------------------------------------------
if selected_city == 'Toutes':
    st.subheader("🏙️ Comparaison par Ville")
    
    # Statistiques par ville
    city_stats = df_filtered.groupby('Ville').agg({
        'Opérateurs': 'count',
        'Ouvert': lambda x: (x == 'Oui').sum()
    }).reset_index()
    
    city_stats.columns = ['Ville', 'Total', 'Ouverts']
    city_stats['Fermés'] = city_stats['Total'] - city_stats['Ouverts']
    city_stats['Taux d\'ouverture (%)'] = (city_stats['Ouverts'] / city_stats['Total'] * 100).round(1)
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        # Graphique en barres empilées
        fig_bars = go.Figure()
        
        fig_bars.add_trace(go.Bar(
            name='Ouverts',
            x=city_stats['Ville'],
            y=city_stats['Ouverts'],
            marker_color='#388e3c',
            text=city_stats['Ouverts'],
            textposition='inside'
        ))
        
        fig_bars.add_trace(go.Bar(
            name='Fermés',
            x=city_stats['Ville'],
            y=city_stats['Fermés'],
            marker_color='#d32f2f',
            text=city_stats['Fermés'],
            textposition='inside'
        ))
        
        fig_bars.update_layout(
            title="Établissements Ouverts vs Fermés par Ville",
            barmode='stack',
            xaxis_title="Ville",
            yaxis_title="Nombre d'établissements"
        )
        
        st.plotly_chart(fig_bars, use_container_width=True)
    
    with col_chart2:
        # Graphique du taux d'ouverture
        fig_rate = go.Figure(go.Bar(
            x=city_stats['Ville'],
            y=city_stats['Taux d\'ouverture (%)'],
            text=city_stats['Taux d\'ouverture (%)'].apply(lambda x: f"{x:.1f}%"),
            textposition='outside',
            marker_color=city_stats['Taux d\'ouverture (%)'].apply(
                lambda x: '#388e3c' if x >= 70 else '#f57c00' if x >= 40 else '#d32f2f'
            )
        ))
        
        fig_rate.update_layout(
            title="Taux d'Ouverture par Ville",
            xaxis_title="Ville",
            yaxis_title="Taux d'ouverture (%)",
            yaxis_range=[0, 100]
        )
        
        st.plotly_chart(fig_rate, use_container_width=True)
    
    # Tableau comparatif
    st.markdown("### 📋 Tableau Comparatif")
    st.dataframe(
        city_stats.style.background_gradient(
            subset=['Taux d\'ouverture (%)'],
            cmap='RdYlGn',
            vmin=0,
            vmax=100
        ),
        use_container_width=True
    )
    
    st.markdown("---")

# -------------------------------------------------------
# STATISTIQUES PAR QUARTIER
# -------------------------------------------------------
st.subheader("📍 Analyse par Quartier")

# Statistiques par quartier
quarter_stats = df_filtered.groupby(['Ville', 'Quartier']).agg({
    'Opérateurs': 'count',
    'Ouvert': lambda x: (x == 'Oui').sum()
}).reset_index()

quarter_stats.columns = ['Ville', 'Quartier', 'Total', 'Ouverts']
quarter_stats['Taux d\'ouverture (%)'] = (quarter_stats['Ouverts'] / quarter_stats['Total'] * 100).round(1)
quarter_stats = quarter_stats.sort_values('Taux d\'ouverture (%)', ascending=False)

# Graphique par quartier
fig_quarter = px.bar(
    quarter_stats,
    x='Quartier',
    y='Taux d\'ouverture (%)',
    color='Ville',
    title="Taux d'Ouverture par Quartier",
    text='Taux d\'ouverture (%)',
    color_discrete_map={'Douala': '#1f77b4', 'Yaoundé': '#2ca02c'}
)

fig_quarter.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
fig_quarter.update_layout(xaxis_tickangle=-45, yaxis_range=[0, 110])
st.plotly_chart(fig_quarter, use_container_width=True)

st.markdown("---")

# -------------------------------------------------------
# STATISTIQUES PAR OPÉRATEUR
# -------------------------------------------------------
st.subheader("🏦 Analyse par Opérateur Bancaire")

# Statistiques par opérateur
operator_stats = df_filtered.groupby('Opérateurs').agg({
    'Ouvert': lambda x: (x == 'Oui').sum(),
    'Ville': 'count'
}).reset_index()

operator_stats.columns = ['Opérateur', 'Agences Ouvertes', 'Total Agences']
operator_stats['Agences Fermées'] = operator_stats['Total Agences'] - operator_stats['Agences Ouvertes']
operator_stats['Taux d\'ouverture (%)'] = (operator_stats['Agences Ouvertes'] / operator_stats['Total Agences'] * 100).round(1)
operator_stats = operator_stats.sort_values('Taux d\'ouverture (%)', ascending=True)

# Graphique horizontal par opérateur
fig_operators = go.Figure(go.Bar(
    y=operator_stats['Opérateur'],
    x=operator_stats['Taux d\'ouverture (%)'],
    orientation='h',
    text=operator_stats['Taux d\'ouverture (%)'].apply(lambda x: f"{x:.1f}%"),
    textposition='outside',
    marker_color=operator_stats['Taux d\'ouverture (%)'].apply(
        lambda x: '#388e3c' if x >= 70 else '#f57c00' if x >= 40 else '#d32f2f'
    )
))

fig_operators.update_layout(
    title="Taux d'Ouverture par Opérateur",
    xaxis_title="Taux d'ouverture (%)",
    yaxis_title="Opérateur",
    xaxis_range=[0, 110],
    height=max(400, len(operator_stats) * 40)
)

st.plotly_chart(fig_operators, use_container_width=True)

st.markdown("---")

# -------------------------------------------------------
# ANALYSE DES HORAIRES DE FERMETURE
# -------------------------------------------------------
st.subheader("⏰ Analyse des Horaires de Fermeture")

# Banques ouvertes avec horaire
banks_with_hours = df_filtered[
    (df_filtered['Ouvert'] == 'Oui') & 
    (df_filtered['Heure de fermeture'].notna())
].copy()

if len(banks_with_hours) > 0:
    col_hour1, col_hour2 = st.columns(2)
    
    with col_hour1:
        # Distribution des horaires de fermeture
        hour_counts = banks_with_hours['Heure de fermeture'].value_counts().sort_index()
        
        fig_hours = px.pie(
            values=hour_counts.values,
            names=hour_counts.index,
            title="Distribution des Horaires de Fermeture",
            hole=0.4
        )
        
        st.plotly_chart(fig_hours, use_container_width=True)
    
    with col_hour2:
        # Horaires par ville
        hour_by_city = banks_with_hours.groupby(['Ville', 'Heure de fermeture']).size().reset_index(name='Count')
        
        fig_hours_city = px.bar(
            hour_by_city,
            x='Heure de fermeture',
            y='Count',
            color='Ville',
            title="Horaires de Fermeture par Ville",
            barmode='group',
            color_discrete_map={'Douala': '#1f77b4', 'Yaoundé': '#2ca02c'}
        )
        
        st.plotly_chart(fig_hours_city, use_container_width=True)
    
    # Tableau des horaires
    st.markdown("### 📋 Détail des Horaires par Établissement")
    hours_table = banks_with_hours[['Ville', 'Quartier', 'Opérateurs', 'Heure de fermeture']].sort_values(
        ['Ville', 'Heure de fermeture']
    )
    st.dataframe(hours_table, use_container_width=True)
else:
    st.info("ℹ️ Aucune information d'horaire de fermeture disponible pour les établissements ouverts")

st.markdown("---")

# -------------------------------------------------------
# TABLEAU DÉTAILLÉ INTERACTIF
# -------------------------------------------------------
st.subheader("📋 Liste Complète des Établissements")

# Préparer le tableau
display_cols = ['Ville', 'Quartier', 'Opérateurs', 'Ouvert', 'Heure de fermeture']
table_df = df_filtered[display_cols].copy()

# Ajouter des icônes pour le statut
table_df['Statut'] = table_df['Ouvert'].apply(lambda x: '🟢 Ouvert' if x == 'Oui' else '🔴 Fermé')
table_df = table_df.drop('Ouvert', axis=1)

# Réorganiser les colonnes
table_df = table_df[['Statut', 'Ville', 'Quartier', 'Opérateurs', 'Heure de fermeture']]

# Fonction de coloration
def color_status(row):
    if '🟢' in str(row['Statut']):
        return ['background-color: #e8f5e9'] * len(row)
    else:
        return ['background-color: #ffebee'] * len(row)

styled_table = table_df.style.apply(color_status, axis=1)
st.dataframe(styled_table, use_container_width=True, height=400)

# Bouton d'export
csv = table_df.to_csv(index=False, encoding='utf-8-sig')
st.download_button(
    label=f"📥 Télécharger la liste ({selected_date.strftime('%d/%m/%Y')})",
    data=csv,
    file_name=f'services_bancaires_{selected_date.strftime("%Y%m%d")}.csv',
    mime='text/csv',
)

# -------------------------------------------------------
# RÉSUMÉ ET ALERTES
# -------------------------------------------------------
st.markdown("---")
st.subheader("📊 Résumé et Recommandations")

col_summary1, col_summary2 = st.columns(2)

with col_summary1:
    st.markdown("### 🎯 Points Clés")
    
    if opening_rate >= 70:
        st.success(f"✅ **Situation favorable** : {opening_rate:.1f}% des établissements sont ouverts")
    elif opening_rate >= 40:
        st.warning(f"⚠️ **Situation moyenne** : {opening_rate:.1f}% des établissements sont ouverts")
    else:
        st.error(f"🚨 **Situation critique** : Seulement {opening_rate:.1f}% des établissements sont ouverts")
    
    # Meilleur quartier
    if len(quarter_stats) > 0:
        best_quarter = quarter_stats.iloc[0]
        st.info(f"🏆 **Meilleur quartier** : {best_quarter['Quartier']} ({best_quarter['Ville']}) - {best_quarter['Taux d\'ouverture (%)']:.1f}% d'ouverture")
    
    # Opérateur le plus ouvert
    if len(operator_stats) > 0:
        best_operator = operator_stats.sort_values('Taux d\'ouverture (%)', ascending=False).iloc[0]
        if best_operator['Taux d\'ouverture (%)'] == 100:
            st.success(f"🏦 **{best_operator['Opérateur']}** : Toutes les agences ouvertes ({int(best_operator['Agences Ouvertes'])})")

with col_summary2:
    st.markdown("### ⚠️ Zones à Problème")
    
    # Quartiers avec taux d'ouverture faible
    low_quarters = quarter_stats[quarter_stats['Taux d\'ouverture (%)'] < 50]
    
    if len(low_quarters) > 0:
        st.error(f"🔴 {len(low_quarters)} quartier(s) avec moins de 50% d'ouverture")
        for _, q in low_quarters.head(3).iterrows():
            st.markdown(f"• **{q['Quartier']}** ({q['Ville']}) : {q['Taux d\'ouverture (%)']:.1f}%")
    else:
        st.success("✅ Aucun quartier critique identifié")
    
    # Opérateurs complètement fermés
    closed_operators = operator_stats[operator_stats['Taux d\'ouverture (%)'] == 0]
    if len(closed_operators) > 0:
        st.warning(f"⚠️ {len(closed_operators)} opérateur(s) complètement fermé(s)")
        for _, op in closed_operators.iterrows():
            st.markdown(f"• {op['Opérateur']}")

# -------------------------------------------------------
# FOOTER
# -------------------------------------------------------
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p>🏦 Monitoring des Services Bancaires - Yaoundé & Douala</p>
    <p style='font-size: 0.9rem;'>Données en temps réel depuis Google Sheets | Media Intelligence 2025</p>
</div>
""", unsafe_allow_html=True)