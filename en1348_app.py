import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader

# Materialdata (tillåtna spänningar f i MPa vid olika temperaturer °C)
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
        "f_values": [100]
    }
}

st.title("EN 13480-3 – Rör, Avstick & Rördelar Beräkning")

# Allmänna indata
material = st.selectbox("Material", list(materials.keys()))
P = st.number_input("Designtryck P (MPa)", min_value=0.0, value=1.0, step=0.1)
T_design = st.number_input("Designtemperatur T (°C)", min_value=-50.0, value=100.0, step=10.0)
z = st.number_input("Fogfaktor z", min_value=0.4, max_value=1.0, value=1.0, step=0.05)
c = st.number_input("Korrosions-/slitagetillägg c (mm)", min_value=0.0, value=1.0, step=0.1)

# Beräkna f_design med interpolation + varning
if material == "Annan":
    f_design = st.number_input("Tillåten spänning f vid T_design (MPa)", min_value=0.0, value=100.0)
else:
    mat = materials[material]
    temps = mat["temps"]
    f_vals = mat["f_values"]
    if T_design < min(temps) or T_design > max(temps):
        st.warning(f"T_design {T_design}°C utanför tabell ({min(temps)}–{max(temps)}°C) → konstant extrapolation")
    f_design = np.interp(T_design, temps, f_vals)

st.write(f"**Tillåten spänning f vid {T_design}°C:** {f_design:.1f} MPa")

if f_design <= 0:
    st.error("f ≤ 0 – kan inte beräkna. Justera material/temp.")
    st.stop()

# Raka rör – korrekt enligt §6.1
st.subheader("Raka rör / Header (EN 13480-3 §6.1)")
D_o = st.number_input("Yttre diameter D_o (mm)", min_value=10.0, value=168.3, step=1.0)
t_nom = st.number_input("Nominell väggtjocklek t_nom (mm)", min_value=1.0, value=7.1, step=0.1)

D_i = D_o - 2 * t_nom
ratio = D_o / D_i if D_i > 0 else 1.0
st.write(f"**D_o / D_i =** {ratio:.3f}")

if ratio <= 1.7:
    e_min = (P * D_o) / (2 * f_design * z + P)
    formel = "(6.1-1)"
else:
    e_min = (D_o / 2) * (1 - np.sqrt((f_design * z - P) / (f_design * z + P)))
    formel = "(6.1-3) Lamé"

e_total = e_min + c
st.write(f"**Formel använd:** {formel}")
st.write(f"**Minsta erforderlig tjocklek e (utan c):** {e_min:.3f} mm")
st.write(f"**Total erforderlig tjocklek (inkl. c):** {e_total:.3f} mm")

if e_total <= t_nom:
    st.success(f"**GODKÄNT enligt §6.1** – t_nom ({t_nom:.2f} mm) ≥ {e_total:.3f} mm")
else:
    st.error(f"**UNDER DIMENSIONERAD enligt §6.1** – saknas {e_total - t_nom:.3f} mm")

# Avstick (behåller den befintliga logiken med feedback)
use_branch = st.checkbox("Beräkna avstick?")
if use_branch:
    st.subheader("Avstick (Branch)")
    branch_type = st.selectbox("Typ", ["Rakt (90°)", "Vinklat"])
    reinforced = st.selectbox("Förstärkning", ["Oförstärkt", "Förstärkt (pad/extra tjocklek)"])

    d_o = st.number_input("Branch yttre diameter d_o (mm)", min_value=10.0, value=60.3)
    t_branch_nom = st.number_input("Branch tjocklek t_nom (mm)", min_value=1.0, value=5.0)

    beta = 90.0 if branch_type == "Rakt (90°)" else st.number_input("Vinkel β (°)", 30, 90, 45)

    d1 = d_o - 2 * t_branch_nom
    d_D_ratio = d_o / D_o

    if reinforced == "Oförstärkt":
        if d_D_ratio <= 0.5 and beta >= 45:
            st.success("**Oförstärkt möjligt** (liten ratio + vinkel) – kontrollera §8.4.2")
        else:
            st.warning("**Kräver förstärkning** (d/D > 0.5 eller vinkel <45°)")
    else:
        A_req = t_nom * d1 * (2 - np.sin(np.deg2rad(beta)))
        excess_h = max(0, t_nom - e_total) * 2.5 * np.sqrt(D_o * (t_nom - e_total))
        excess_b = max(0, t_branch_nom - e_total) * 2.5 * np.sqrt(d_o * (t_branch_nom - e_total))
        pad_w = st.number_input("Pad bredd (mm)", 0.0, value=50.0)
        pad_t = st.number_input("Pad tjocklek (mm)", 0.0, value=6.0)
        A_pad = pad_w * pad_t if pad_t > 0 else 0
        A_avail = excess_h + excess_b + A_pad

        st.write(f"**A_req ≈** {A_req:.1f} mm²")
        st.write(f"**A_avail ≈** {A_avail:.1f} mm²")
        if A_avail >= A_req:
            st.success("**Avstick OK – tillräcklig förstärkning**")
        else:
            st.error(f"**Otillräcklig förstärkning** – saknas {A_req - A_avail:.1f} mm²")

# Provtryck (enkelt)
st.subheader("Provtryckning")
T_test = st.number_input("Testtemperatur (°C)", value=20.0)
f_test = np.interp(T_test, mat["temps"], mat["f_values"]) if material != "Annan" else st.number_input("f vid testtemp", value=150.0)

ratio = f_test / f_design
P_test = max(1.25 * P * ratio, 1.43 * P)
st.write(f"**Provtryck P_test ≈** {P_test:.2f} MPa")

# Sammanfattningstabell
data = {
    "Parameter": ["Material", "P (MPa)", "T_design (°C)", "f_design (MPa)", "D_o (mm)", "t_nom (mm)", "e_total (mm)", "Rörstatus §6.1", "Provtryck (MPa)"],
    "Värde": [material, f"{P:.2f}", f"{T_design}", f"{f_design:.1f}", f"{D_o}", f"{t_nom:.2f}", f"{e_total:.3f}", 
              "Godkänt" if e_total <= t_nom else "Under dimensionerad", f"{P_test:.2f}"]
}
df = pd.DataFrame(data)
st.dataframe(df)

# PDF-knapp (med ritning)
def create_diagram():
    fig, ax = plt.subplots(figsize=(5,3))
    ax.add_patch(plt.Rectangle((0,0), D_o, t_nom, fill=None, edgecolor='b', lw=2))
    ax.text(D_o/2, -10, f'OD = {D_o} mm', ha='center')
    ax.text(D_o+10, t_nom/2, f't = {t_nom} mm', va='center')
    ax.axis('equal'); ax.axis('off')
    buf = BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf

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
