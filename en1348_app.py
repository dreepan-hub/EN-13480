import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Material data
materials = {
    "P235GH (Kolstål)": {"temps": [20, 100, 150, 200, 250, 300], "f_values": [150, 143, 135, 127, 117, 104]},
    "P265GH (Kolstål)": {"temps": [20, 100, 150, 200, 250, 300], "f_values": [170, 162, 153, 144, 133, 118]},
    "16Mo3 (Legerat stål)": {"temps": [20, 100, 200, 300, 400, 450, 500], "f_values": [180, 174, 160, 140, 113, 98, 80]},
    "13CrMo4-5 (Legerat stål)": {"temps": [20, 100, 200, 300, 400, 500], "f_values": [170, 164, 151, 132, 106, 70]},
    "1.4301 (Rostfritt)": {"temps": [20, 100, 200, 300, 400, 500, 550], "f_values": [127, 109, 96, 85, 78, 72, 70]},
    "1.4404 (Rostfritt)": {"temps": [20, 100, 200, 300, 400, 500, 550], "f_values": [133, 114, 100, 89, 81, 75, 73]},
    "1.4571 (Rostfritt)": {"temps": [20, 100, 200, 300, 400, 500, 550], "f_values": [133, 114, 100, 89, 81, 75, 73]},
    "Annan": {"temps": [20], "f_values": [100]}
}

st.title("EN 13480-3 – Snabbkontroll Rör & Avstick")

# Indata
material = st.selectbox("Material", list(materials.keys()))
P = st.number_input("Designtryck P (MPa)", value=1.0, step=0.1)
T_design = st.number_input("Designtemp T (°C)", value=100.0, step=10.0)
z = st.number_input("Fogfaktor z", value=1.0, min_value=0.4, max_value=1.0, step=0.05)
c = st.number_input("Korrosionstillägg c (mm)", value=1.0, step=0.1)

# f_design
if material == "Annan":
    f_design = st.number_input("f vid T_design (MPa)", value=100.0)
else:
    mat = materials[material]
    if T_design < min(mat["temps"]) or T_design > max(mat["temps"]):
        st.warning("T utanför tabell → extrapolation")
    f_design = np.interp(T_design, mat["temps"], mat["f_values"])

st.write(f"f_design = {f_design:.1f} MPa vid {T_design}°C")

# Raka rör
st.subheader("Raka rör (§6.1)")
D_o = st.number_input("D_o (mm)", value=168.3)
t_nom = st.number_input("t_nom (mm)", value=7.1)

D_i = D_o - 2 * t_nom
ratio = D_o / D_i if D_i > 0 else 1.0

if ratio <= 1.7:
    e_min = (P * D_o) / (2 * f_design * z + P)
    formel_rak = "6.1-1"
else:
    e_min = (D_o / 2) * (1 - np.sqrt((f_design * z - P) / (f_design * z + P)))
    formel_rak = "6.1-3 (Lamé)"

e_total = e_min + c
st.write(f"Formel: {formel_rak}")
st.write(f"e_total (inkl. c): {e_total:.3f} mm")

if e_total <= t_nom:
    st.success(f"**GODKÄNT §6.1** – t_nom ≥ e_total")
else:
    st.error(f"**UNDER DIMENSIONERAD §6.1** – saknas {e_total - t_nom:.3f} mm")

# Böj (aktiveras med kryssruta)
use_boj = st.checkbox("Beräkna böj (elbow) enligt §6.2.3?")
if use_boj:
    st.subheader("Böj (§6.2.3)")
    R = st.number_input("Böjradie R (mm)", value=D_o * 1.5)
    t_boj_nom = st.number_input("Böj t_nom (mm)", value=t_nom)

    r_d = R / D_o
    if r_d <= 0.5:
        st.warning("r_d ≤ 0.5 – använder e från raka rör")
        e_int = e_ext = e_min
    else:
        e_int = e_min * (r_d - 0.25) / (r_d - 0.5)   # (6.2.3-1)
        e_ext = e_min * (r_d + 0.25) / (r_d + 0.5)   # (6.2.3-2)

    e_total_int = e_int + c
    e_total_ext = e_ext + c

    st.write(f"**r/D_o =** {r_d:.3f}")
    st.write(f"**e_int (intrados, formel 6.2.3-1):** {e_int:.3f} mm (exkl. c)")
    st.write(f"**e_ext (extrados, formel 6.2.3-2):** {e_ext:.3f} mm (exkl. c)")
    st.write(f"**Total intrados:** {e_total_int:.3f} mm")
    st.write(f"**Total extrados:** {e_total_ext:.3f} mm")

    e_max_boj = max(e_total_int, e_total_ext)
    if e_max_boj <= t_boj_nom:
        st.success(f"**Böj GODKÄNT §6.2.3** – t_nom ≥ {e_max_boj:.3f} mm")
    else:
        st.error(f"**Böj UNDER DIMENSIONERAD §6.2.3** – saknas {e_max_boj - t_boj_nom:.3f} mm")

# Avstick
use_branch = st.checkbox("Beräkna avstick (§8.4.3)?")
if use_branch:
    st.subheader("Avstick (§8.4.3)")
    is_oblique = st.checkbox("Vinklad (oblique)?")
    beta_deg = st.number_input("Vinkel φ/β från normalen (°)", 0.0, 45.0, 0.0) if is_oblique else 0.0
    beta_rad = np.deg2rad(beta_deg)

    d_o = st.number_input("d_o (mm)", value=60.3)
    t_b_nom = st.number_input("Branch t_nom (mm)", value=5.0)

    d_i = d_o - 2 * t_b_nom
    d_eff = d_i / np.cos(beta_rad) if is_oblique and np.cos(beta_rad) != 0 else d_i

    A_p_req = d_eff * t_nom * (2 - np.sin(np.deg2rad(90 - beta_deg)))  # approx (8.4.3-3 + vinkel)

    ls = 2.5 * np.sqrt(D_o * max(t_nom - e_total, 0))  # approx (8.4.1-2)

    excess_shell = max(0, t_nom - e_total) * min(ls, 2.5 * d_o)
    excess_branch = max(0, t_b_nom - e_total) * min(ls, 2.5 * d_o)

    A_f_pl = 0
    if st.checkbox("Reinforcing pad?"):
        l_pl = st.number_input("l_pl (mm)", value=50.0)
        e_pl = st.number_input("e_pl (mm)", value=6.0)
        l_pl = min(l_pl, ls)  # (8.4.3-4)
        e_pl = min(e_pl, t_nom)  # (8.4.3-5)
        A_f_pl = l_pl * e_pl

    A_f_total = excess_shell + excess_branch + A_f_pl

    st.write("**Formler:**")
    st.write("- A_p_req ≈ d_eff * t_nom * (2 - sin(90-β)) (baserat på 8.4.3-3 + vinkeljustering)")
    st.write("- ls ≈ 2.5 √(D_o * excess_t) (från 8.4.1-2)")
    st.write("- A_f s & A_f b från excess tjocklek inom ls")
    st.write("- Pad begränsad enligt (8.4.3-4) och (8.4.3-5)")

    st.write(f"**A_p_req:** {A_p_req:.1f} mm²")
    st.write(f"**A_f total:** {A_f_total:.1f} mm²")

    if A_f_total >= A_p_req:
        st.success("**OK enligt §8.4.3 (8.4.3-6 uppfyllt)**")
    else:
        st.error(f"**Otillräcklig** – saknas {A_p_req - A_f_total:.1f} mm². Kolla (8.4.3-6/7)")

# Provtryck
st.subheader("Provtryckning")
T_test = st.number_input("Testtemp (°C)", value=20.0)
f_test = np.interp(T_test, materials[material]["temps"], materials[material]["f_values"]) if material != "Annan" else st.number_input("f_test (MPa)", value=150.0)
P_test = max(1.25 * P * (f_test / f_design), 1.43 * P)
st.write(f"**P_test:** {P_test:.2f} MPa")

# Sammanfattning (utökad)
results = [
    ["Material", material],
    ["P (MPa)", f"{P:.2f}"],
    ["T_design (°C)", T_design],
    ["f_design (MPa)", f"{f_design:.1f}"],
    ["D_o (mm)", D_o],
    ["t_nom raka (mm)", f"{t_nom:.2f}"],
    ["e_total raka (mm)", f"{e_total:.3f}"],
    ["Status raka rör §6.1", "Godkänt" if e_total <= t_nom else "Under dimensionerad"]
]

if use_boj:
    results.extend([
        ["Böj – e_int (exkl c)", f"{e_int:.3f}"],
        ["Böj – e_ext (exkl c)", f"{e_ext:.3f}"],
        ["Böj t_nom", f"{t_boj_nom:.2f}"],
        ["Status böj §6.2.3", "Godkänt" if max(e_total_int, e_total_ext) <= t_boj_nom else "Under dimensionerad"]
    ])

if use_branch:
    results.extend([
        ["Avstick d_o (mm)", d_o],
        ["A_p_req (mm²)", f"{A_p_req:.1f}"],
        ["A_f total (mm²)", f"{A_f_total:.1f}"],
        ["Status avstick §8.4.3", "OK" if A_f_total >= A_p_req else "Otillräcklig"]
    ])

results.extend([
    ["Provtryck P_test (MPa)", f"{P_test:.2f}"],
    ["Formler raka", formel_rak],
    ["Formler böj (om aktiverad)", "6.2.3-1 & 6.2.3-2"],
    ["Formler avstick", "8.4.3-3/4/5/6/8"]
])

df_summary = pd.DataFrame(results, columns=["Parameter", "Värde"])
st.subheader("Sammanfattning")
st.dataframe(df_summary)

# PDF – bara text
if st.button("Ladda ner PDF-rapport"):
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=letter)
    width, height = letter
    c.drawString(100, height - 50, "EN 13480-3 Snabbkontroll Rapport")
    y = height - 100
    for _, row in df_summary.iterrows():
        c.drawString(100, y, f"{row['Parameter']}: {row['Värde']}")
        y -= 20
        if y < 50:
            c.showPage()
            y = height - 50
    c.save()
    pdf_buffer.seek(0)
    st.download_button("Ladda ner PDF", pdf_buffer, "en13480_kontroll.pdf", "application/pdf")
