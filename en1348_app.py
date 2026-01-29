import streamlit as st
import pandas as pd
import numpy as np

# Material data med tillåtna spänningar f (MPa) vid olika temperaturer (°C)
# Baserat på typiska värden från EN 13480-2 tabeller (approximativa; verifiera med standarden)
materials = {
    "P235GH (Kolstål)": {
        "temps": [20, 100, 150, 200, 250, 300],
        "f_values": [150, 143, 135, 127, 117, 104]
    },
    "P265GH (Kolstål)": {
        "temps": [20, 100, 150, 200, 250, 300],
        "f_values": [170, 162, 153, 144, 133, 118]
    },
    "16Mo3 (Legerat stål)": {
        "temps": [20, 100, 200, 300, 400, 450, 500],
        "f_values": [180, 174, 160, 140, 113, 98, 80]
    },
    "13CrMo4-5 (Legerat stål)": {
        "temps": [20, 100, 200, 300, 400, 500],
        "f_values": [170, 164, 151, 132, 106, 70]
    },
    "1.4301 (Rostfritt austenitiskt)": {
        "temps": [20, 100, 200, 300, 400, 500, 550],
        "f_values": [127, 109, 96, 85, 78, 72, 70]
    },
    "1.4404 (Rostfritt austenitiskt)": {
        "temps": [20, 100, 200, 300, 400, 500, 550],
        "f_values": [133, 114, 100, 89, 81, 75, 73]
    },
    "1.4571 (Rostfritt austenitiskt)": {
        "temps": [20, 100, 200, 300, 400, 500, 550],
        "f_values": [133, 114, 100, 89, 81, 75, 73]
    },
    "Annan": {
        "temps": [20],
        "f_values": [100]  # Mata in manuellt
    }
}

st.title("EN 13480-3 – Komplett Beräkning för Rörsystem, Avstick & Rördelar")

# Allmänna parametrar
material = st.selectbox("Material (från EN 13480-2)", list(materials.keys()))
P = st.number_input("Designtryck P (MPa)", min_value=0.0, value=1.0, step=0.1)
T_design = st.number_input("Designtemperatur (°C)", min_value=-50.0, value=100.0, step=10.0)
z = st.number_input("Fogfaktor z", min_value=0.4, max_value=1.0, value=1.0, step=0.05)
c = st.number_input("Korrosions-/slitagetillägg c (mm)", min_value=0.0, value=1.0, step=0.1)

# Hämta f_design vid T_design (med extrapolation och varning)
if material == "Annan":
    f_design = st.number_input("Tillåten spänning f vid designtemp (MPa)", min_value=0.0, value=100.0)
else:
    mat_data = materials[material]
    temps = mat_data["temps"]
    f_values = mat_data["f_values"]
    if T_design < min(temps) or T_design > max(temps):
        st.warning(f"Temperatur {T_design}°C utanför tabell-range ({min(temps)}–{max(temps)}°C). Extrapolerar, men verifiera med EN 13480-2!")
    f_design = np.interp(T_design, temps, f_values, left="extrapolate", right="extrapolate")

st.write(f"**Tillåten spänning f vid {T_design}°C:** {f_design:.1f} MPa")

if f_design <= 0:
    st.error("f_design ≤ 0 – kan inte beräkna! Justera material eller temp.")
    st.stop()

# Raka rör / Header
st.subheader("Raka rör / Header")
D_o_header = st.number_input("Header yttre diameter D_o (mm)", min_value=10.0, value=168.3, step=1.0)
t_header_nom = st.number_input("Header nominell tjocklek t_nom (mm)", min_value=1.0, value=7.1, step=0.1)

e_min_header = (P * D_o_header) / (2 * f_design * z + P) + c
st.write(f"**Min tjocklek e_min (inkl. c):** {e_min_header:.2f} mm")
if e_min_header > t_header_nom:
    st.warning("Varning: e_min > t_nom – underdimensionerad!")

# Rördelar (nytt!)
use_fitting = st.checkbox("Inkludera rördelar-beräkning?")
if use_fitting:
    st.subheader("Rördelar (Fittings)")
    fitting_typ = st.selectbox("Typ av rördel", ["Böj (elbow)", "Reducer (koncentrisk)", "Tee (branching)"])

    if fitting_typ == "Böj (elbow)":
        R_bend = st.number_input("Böjradie R (mm)", min_value=10.0, value=D_o_header * 1.5, step=10.0)
        D_o_bend = st.number_input("Böjdiameter D_o (mm)", min_value=10.0, value=D_o_header, step=1.0)
        lambda_factor = (D_o_bend * R_bend) / (t_header_nom ** 2)  # approx från 6.3.2
        e_min_bend = (P * D_o_bend * (1 + (D_o_bend / (2 * R_bend)))) / (2 * f_design * z + P) + c  # förenklad formel 6.3-1
        st.write(f"**Min tjocklek e_min för böj:** {e_min_bend:.2f} mm")
        if lambda_factor < 0.9:
            st.warning("Låg lambda – kontrollera buckling enligt 6.3.3!")

    elif fitting_typ == "Reducer (koncentrisk)":
        D_o_large = st.number_input("Stor diameter D_o (mm)", min_value=10.0, value=168.3, step=1.0)
        D_o_small = st.number_input("Liten diameter d_o (mm)", min_value=10.0, value=114.3, step=1.0)
        alpha = st.number_input("Konvinkel α (°)", min_value=0.0, max_value=30.0, value=15.0, step=1.0)
        e_min_reducer = max((P * D_o_large) / (2 * f_design * z + P), (P * D_o_small) / (2 * f_design * z + P)) + c  # max av båda ändar
        if alpha > 20:
            st.warning("Hög konvinkel – extra förstärkning kan krävas enligt 6.5.3.")
        st.write(f"**Min tjocklek e_min för reducer:** {e_min_reducer:.2f} mm")

    elif fitting_typ == "Tee (branching)":
        # Liknande avstick, men med tee-specifika faktorer
        D_o_branch = st.number_input("Branch diameter d_o (mm)", min_value=10.0, value=60.3, step=1.0)
        t_branch_nom = st.number_input("Branch nominell tjocklek (mm)", min_value=1.0, value=5.0, step=0.1)
        A_req_tee = 2.5 * t_header_nom * D_o_branch  # approx från 8.5 för tee
        st.write(f"**Required area A_req för tee:** ≈ {A_req_tee:.1f} mm²")
        # Lägg till reinforcement-logik som i avstick om du vill utöka

# Avstick / Branch (valfritt)
use_branch = st.checkbox("Inkludera avstick-beräkning?")
if use_branch:
    st.subheader("Avstick (Branch Connection)")
    branch_typ = st.selectbox("Typ av avstick", ["Rakt (90°)", "Vinklat (oblique)"])
    reinforced = st.selectbox("Förstärkt eller oförstärkt?", ["Oförstärkt (unreinforced)", "Förstärkt (reinforced med pad eller extra tjocklek)"])

    D_o_branch = st.number_input("Branch yttre diameter d_o (mm)", min_value=10.0, value=60.3, step=1.0)
    t_branch_nom = st.number_input("Branch nominell tjocklek t_nom (mm)", min_value=1.0, value=5.0, step=0.1)

    if branch_typ == "Vinklat (oblique)":
        beta = st.number_input("Vinkel β (°)", min_value=30.0, max_value=90.0, value=45.0, step=5.0)
    else:
        beta = 90.0

    d1 = D_o_branch - 2 * t_branch_nom  # approx inner d för area

    # Unreinforced check (förenklad)
    d_D_ratio = D_o_branch / D_o_header
    if reinforced == "Oförstärkt (unreinforced)":
        if d_D_ratio <= 0.5 and beta >= 45:
            st.success("**Möjligt oförstärkt** (liten ratio). Kontrollera 8.4.2.")
        else:
            st.warning("**Kräver reinforcement** (d/D > 0.5 eller vinkel <45°).")

    # Reinforced area calculation
    if reinforced == "Förstärkt (reinforced med pad eller extra tjocklek)":
        A_req = t_header_nom * d1 * (2 - np.sin(np.deg2rad(beta)))  # approx från 8.4.3
        st.write(f"**Required area A_req:** ≈ {A_req:.1f} mm²")

        excess_header = max(0, t_header_nom - e_min_header) * 2.5 * np.sqrt(D_o_header * (t_header_nom - e_min_header))
        excess_branch = max(0, t_branch_nom - e_min_header) * 2.5 * np.sqrt(D_o_branch * (t_branch_nom - e_min_header))
        pad_width = st.number_input("Pad bredd (mm)", min_value=0.0, value=50.0, step=5.0)
        pad_thick = st.number_input("Pad tjocklek (mm)", min_value=0.0, value=6.0, step=1.0)
        A_pad = pad_width * pad_thick if pad_thick > 0 else 0
        A_avail = excess_header + excess_branch + A_pad

        st.write(f"**Available area A_avail:** ≈ {A_avail:.1f} mm²")
        if A_avail >= A_req:
            st.success("**OK – tillräcklig reinforcement!**")
        else:
            st.error(f"**Otillräcklig!** Saknas {A_req - A_avail:.1f} mm².")

# Provtryckning
st.subheader("Provtryckning")
T_test = st.number_input("Testtemperatur (°C)", min_value=-50.0, value=20.0, step=10.0)

if material == "Annan":
    f_test = st.number_input("Tillåten spänning f vid testtemp (MPa)", min_value=0.0, value=150.0)
else:
    mat_data = materials[material]
    temps = mat_data["temps"]
    f_values = mat_data["f_values"]
    if T_test < min(temps) or T_test > max(temps):
        st.warning(f"Testtemp {T_test}°C utanför range – extrapolerar!")
    f_test = np.interp(T_test, temps, f_values, left="extrapolate", right="extrapolate")

st.write(f"**Tillåten spänning f vid {T_test}°C:** {f_test:.1f} MPa")

if f_design > 0:
    ratio = f_test / f_design
    P_test_1 = 1.25 * P * ratio
    P_test_2 = 1.43 * P
    P_test = max(P_test_1, P_test_2)
    st.write(f"**Provtryck P_test:** {P_test:.2f} MPa (max av {P_test_1:.2f} och {P_test_2:.2f})")

# Sammanfattning
sammanfattning = {
    "Parameter": ["Material", "Designtryck P", "Designtemp T", "f_design", "Header D_o", "Min tjocklek e_min", "Testtemp T_test", "f_test", "Provtryck P_test"],
    "Värde": [material, f"{P:.2f} MPa", f"{T_design}°C", f"{f_design:.1f} MPa", f"{D_o_header} mm", f"{e_min_header:.2f} mm", f"{T_test}°C", f"{f_test:.1f} MPa", f"{P_test:.2f} MPa"]
}

if use_fitting:
    sammanfattning["Parameter"].append("Rördel typ")
    sammanfattning["Värde"].append(fitting_typ)
    if fitting_typ == "Böj (elbow)":
        sammanfattning["Parameter"].append("Min tjocklek böj")
        sammanfattning["Värde"].append(f"{e_min_bend:.2f} mm")
    elif fitting_typ == "Reducer (koncentrisk)":
        sammanfattning["Parameter"].append("Min tjocklek reducer")
        sammanfattning["Värde"].append(f"{e_min_reducer:.2f} mm")

if use_branch:
    sammanfattning["Parameter"].extend(["Branch d_o", "Branch typ", "Vinkel β", "Reinforcement", "A_req (approx)", "A_avail (approx)"])
    sammanfattning["Värde"].extend([f"{D_o_branch} mm", branch_typ, f"{beta}°", reinforced, f"{A_req if 'A_req' in locals() else '-'} mm²", f"{A_avail if 'A_avail' in locals() else '-'} mm²"])

df = pd.DataFrame(sammanfattning)
st.subheader("Sammanfattning")
st.dataframe(df)

csv = df.to_csv(index=False).encode('utf-8')
st.download_button("Ladda ner som CSV", csv, "en13480_resultat.csv", "text/csv")
