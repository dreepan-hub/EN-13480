import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader

# Material data med tillåtna spänningar f (MPa) vid olika temperaturer (°C)
materials = {
    "P235GH (Kolstål)": {"temps": [20, 100, 150, 200, 250, 300], "f_values": [150, 143, 135, 127, 117, 104]},
    "P265GH (Kolstål)": {"temps": [20, 100, 150, 200, 250, 300], "f_values": [170, 162, 153, 144, 133, 118]},
    "16Mo3 (Legerat stål)": {"temps": [20, 100, 200, 300, 400, 450, 500], "f_values": [180, 174, 160, 140, 113, 98, 80]},
    "13CrMo4-5 (Legerat stål)": {"temps": [20, 100, 200, 300, 400, 500], "f_values": [170, 164, 151, 132, 106, 70]},
    "1.4301 (Rostfritt austenitiskt)": {"temps": [20, 100, 200, 300, 400, 500, 550], "f_values": [127, 109, 96, 85, 78, 72, 70]},
    "1.4404 (Rostfritt austenitiskt)": {"temps": [20, 100, 200, 300, 400, 500, 550], "f_values": [133, 114, 100, 89, 81, 75, 73]},
    "1.4571 (Rostfritt austenitiskt)": {"temps": [20, 100, 200, 300, 400, 500, 550], "f_values": [133, 114, 100, 89, 81, 75, 73]},
    "Annan": {"temps": [20], "f_values": [100]}
}

st.title("EN 13480-3 – Rör, Avstick & Rördelar Beräkning")

# Allmänna parametrar
material = st.selectbox("Material", list(materials.keys()))
P = st.number_input("Designtryck P (MPa)", min_value=0.0, value=1.0, step=0.1)
T_design = st.number_input("Designtemperatur T (°C)", min_value=-50.0, value=100.0, step=10.0)
z = st.number_input("Fogfaktor z", min_value=0.4, max_value=1.0, value=1.0, step=0.05)
c = st.number_input("Korrosions-/slitagetillägg c (mm)", min_value=0.0, value=1.0, step=0.1)

# Beräkna f_design
if material == "Annan":
    f_design = st.number_input("Tillåten spänning f vid T_design (MPa)", value=100.0)
else:
    mat = materials[material]
    temps = mat["temps"]
    f_vals = mat["f_values"]
    if T_design < min(temps) or T_design > max(temps):
        st.warning(f"T_design {T_design}°C utanför tabell ({min(temps)}–{max(temps)}°C) → konstant extrapolation")
    f_design = np.interp(T_design, temps, f_vals)

st.write(f"**f_design vid {T_design}°C:** {f_design:.1f} MPa")

if f_design <= 0:
    st.error("f_design ≤ 0 – kan inte beräkna!")
    st.stop()

# Raka rör (§6.1)
st.subheader("Raka rör / Header (§6.1)")
D_o = st.number_input("Yttre diameter D_o (mm)", value=168.3, step=1.0)
t_nom = st.number_input("Nominell väggtjocklek t_nom (mm)", value=7.1, step=0.1)

D_i = D_o - 2 * t_nom
ratio_do_di = D_o / D_i if D_i > 0 else 1.0
st.write(f"**D_o / D_i =** {ratio_do_di:.3f}")

if ratio_do_di <= 1.7:
    e_min = (P * D_o) / (2 * f_design * z + P)
    formel = "(6.1-1)"
else:
    e_min = (D_o / 2) * (1 - np.sqrt((f_design * z - P) / (f_design * z + P)))
    formel = "(6.1-3) Lamé"

e_total = e_min + c
st.write(f"**Formel:** {formel}")
st.write(f"**e_min (utan c):** {e_min:.3f} mm")
st.write(f"**e_total (inkl. c):** {e_total:.3f} mm")

if e_total <= t_nom:
    st.success(f"**GODKÄNT §6.1** – t_nom ({t_nom:.2f} mm) ≥ {e_total:.3f} mm")
else:
    st.error(f"**UNDER DIMENSIONERAD §6.1** – saknas {e_total - t_nom:.3f} mm")

# Avstick (§8.4.3 – pad och oblique)
use_branch = st.checkbox("Beräkna avstick / branch?")
if use_branch:
    st.subheader("Avstick (§8.4.3)")
    is_oblique = st.checkbox("Oblique (vinklad) branch?")
    beta_deg = st.number_input("Vinkel φ/β från normalen (°)", 0.0, 45.0, 0.0) if is_oblique else 0.0
    beta_rad = np.deg2rad(beta_deg)

    d_o = st.number_input("Branch yttre diameter d_o (mm)", value=60.3)
    t_b_nom = st.number_input("Branch tjocklek t_b nom (mm)", value=5.0)

    d_i = d_o - 2 * t_b_nom
    d_eff = d_i / np.cos(beta_rad) if is_oblique and np.cos(beta_rad) != 0 else d_i  # (8.4.3-8)

    # Required area A_p (baserat på approx från 8.4.3-3 och vinkeljustering)
    A_p_req = d_eff * t_nom * (2 - np.sin(np.deg2rad(90 - beta_deg)))  # anpassat för vinkel

    # Limit length ls approx (från 8.4.1-2)
    ls = 2.5 * np.sqrt(D_o * max(t_nom - e_total, 0))

    # Excess areas
    excess_shell = max(0, t_nom - e_total) * min(ls, 2.5 * d_o)  # A_f s
    excess_branch = max(0, t_b_nom - e_total) * min(ls, 2.5 * d_o)  # A_f b

    # Pad
    use_pad = st.checkbox("Använd reinforcing pad?")
    A_f_pl = 0
    if use_pad:
        l_pl = st.number_input("Pad längd/bredd l_pl (mm)", 0.0, value=50.0)
        e_pl = st.number_input("Pad tjocklek e_pl (mm)", 0.0, value=6.0)
        if l_pl > ls:
            st.warning(f"l_pl > ls – begränsas till {ls:.1f} mm enligt (8.4.3-4)")
            l_pl = min(l_pl, ls)
        if e_pl > t_nom:
            st.warning(f"e_pl > e_s – begränsas till {t_nom:.2f} mm enligt (8.4.3-5)")
            e_pl = min(e_pl, t_nom)
        A_f_pl = l_pl * e_pl

    A_f_total = excess_shell + excess_branch + A_f_pl

    st.write(f"**Required area A_p:** ≈ {A_p_req:.1f} mm²")
    st.write(f"**Available area A_f total:** ≈ {A_f_total:.1f} mm²")

    if A_f_total >= A_p_req:
        st.success("**Reinforcement OK enligt §8.4.3 (8.4.3-6 uppfyllt)**")
    else:
        st.error(f"**Otillräcklig – saknas {A_p_req - A_f_total:.1f} mm². Se (8.4.3-6/7)**")

# Provtryckning
st.subheader("Provtryckning")
T_test = st.number_input("Testtemperatur (°C)", value=20.0)
if material == "Annan":
    f_test = st.number_input("f vid testtemp (MPa)", value=150.0)
else:
    f_test = np.interp(T_test, materials[material]["temps"], materials[material]["f_values"])
P_test = max(1.25 * P * (f_test / f_design), 1.43 * P)
st.write(f"**Provtryck P_test:** {P_test:.2f} MPa")

# Sammanfattning
data = {
    "Parameter": ["Material", "P (MPa)", "T_design (°C)", "f_design (MPa)", "D_o (mm)", "t_nom (mm)", "e_total (mm)", "Rörstatus §6.1", "Provtryck (MPa)"],
    "Värde": [material, f"{P:.2f}", f"{T_design}", f"{f_design:.1f}", f"{D_o}", f"{t_nom:.2f}", f"{e_total:.3f}",
              "Godkänt" if e_total <= t_nom else "Under dimensionerad", f"{P_test:.2f}"]
}
df = pd.DataFrame(data)
st.subheader("Sammanfattning")
st.dataframe(df)

# Diagram-funktion
def create_diagram():
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.add_patch(plt.Rectangle((0,0), D_o, t_nom, fill=None, edgecolor='b', lw=2))
    ax.text(D_o/2, -10, f'OD = {D_o} mm', ha='center')
    ax.text(D_o+10, t_nom/2, f't = {t_nom} mm', va='center')
    ax.axis('equal')
    ax.axis('off')
    buf = BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf

# PDF
if st.button("Ladda ner PDF-rapport"):
    pdf_buf = BytesIO()
    c = canvas.Canvas(pdf_buf, pagesize=letter)
    w, h = letter
    c.drawString(100, h-50, "EN 13480-3 Rapport")
    y = h - 100
    for _, row in df.iterrows():
        c.drawString(100, y, f"{row['Parameter']}: {row['Värde']}")
        y -= 20
    c.drawString(100, y-30, "Rördiagram:")
    img_buf = create_diagram()
    img = ImageReader(img_buf)
    c.drawImage(img, 100, y-250, width=300, height=200, preserveAspectRatio=True)
    c.save()
    pdf_buf.seek(0)
    st.download_button("Ladda ner PDF", pdf_buf, "en13480_rapport.pdf", "application/pdf")
