import streamlit as st
import pandas as pd
import numpy as np

st.title("EN 1348 – Draghållfasthet (Tensile Adhesion Strength)")
st.write("Beräkna draghållfasthet enligt EN 1348 för cementbaserade fästmassor.")

# Välj klass enligt EN 12004
klass = st.selectbox("Fästmassa klass", ["C1", "C2", "Annan"])

if klass == "C1":
    krav_initial = 0.5
    krav_andra = 0.5
elif klass == "C2":
    krav_initial = 1.0
    krav_andra = 0.5
else:
    krav_initial = st.number_input("Krav initial (MPa)", min_value=0.0, value=1.0, step=0.1)
    krav_andra = st.number_input("Krav efter åldring/vatten/frys (MPa)", min_value=0.0, value=0.5, step=0.1)

# Yta per prov (vanligast 50×50 mm = 2500 mm²)
yta_mm2 = st.number_input("Yta per prov (mm²)", min_value=100.0, value=2500.0, step=100.0)

# Välj vilka tillstånd du vill mata in
tillstand_list = ["Initial", "Vattenlagring", "Värmeåldring", "Frys/Tö"]
valda_tillstand = st.multiselect("Välj testtillstånd", tillstand_list, default=["Initial"])

# Sammanfattningstabell som byggs upp
sammanfattning = []

for ts in valda_tillstand:
    st.subheader(ts)
    
    antal = st.number_input(f"Antal prov för {ts}", min_value=1, max_value=30, value=10, step=1, key=f"antal_{ts}")
    
    krafter = []
    for i in range(antal):
        kraft = st.number_input(f"Prov {i+1} – Kraft (N)", min_value=0.0, value=0.0, step=10.0, key=f"kraft_{ts}_{i}")
        if kraft > 0:
            krafter.append(kraft)
    
    if krafter:
        mpa_varden = [k / (yta_mm2 / 1_000_000) for k in krafter]  # N → MPa
        
        df = pd.DataFrame({
            "Prov": range(1, len(mpa_varden)+1),
            "Kraft (N)": krafter,
            "Spänning (MPa)": [round(v, 2) for v in mpa_varden]
        })
        st.dataframe(df)
        
        medel = np.mean(mpa_varden)
        std = np.std(mpa_varden, ddof=1) if len(mpa_varden) > 1 else 0
        min_varde = np.min(mpa_varden)
        
        st.write(f"**Medelvärde:** {medel:.2f} MPa")
        st.write(f"**Standardavvikelse:** {std:.2f} MPa")
        st.write(f"**Minsta värde:** {min_varde:.2f} MPa")
        
        # Bedömning
        if ts == "Initial":
            krav = krav_initial
        else:
            krav = krav_andra
        
        if medel >= krav:
            st.success(f"**Godkänt** enligt krav ({medel:.2f} ≥ {krav} MPa)")
            godkant = "Ja"
        else:
            st.error(f"**Underkänt** ({medel:.2f} < {krav} MPa)")
            godkant = "Nej"
        
        sammanfattning.append({
            "Tillstånd": ts,
            "Medel (MPa)": round(medel, 2),
            "Std (MPa)": round(std, 2),
            "Min (MPa)": round(min_varde, 2),
            "Krav (MPa)": krav,
            "Godkänt": godkant
        })

# Visa sammanfattning om det finns data
if sammanfattning:
    st.subheader("Sammanfattning – alla tillstånd")
    df_samman = pd.DataFrame(sammanfattning)
    st.dataframe(df_samman)
    
    # Ladda ner som CSV
    csv = df_samman.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Ladda ner resultat som CSV",
        data=csv,
        file_name="en1348_resultat.csv",
        mime="text/csv"
    )
