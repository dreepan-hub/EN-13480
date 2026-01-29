import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime

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

st.title("EN 13480-3 – Snabbkontroll & Kvalitetsunderlag")

# Grunddata + egen rubrik
with st.expander("Grunddata", expanded=True):
    material = st.selectbox("Material", list(materials.keys()))
    P = st.number_input("Designtryck P (MPa)", value=1.0, step=0.1)
    T_design = st.number_input("Designtemp T (°C)", value=100.0, step=10.0)
    z = st.number_input("Fogfaktor z", value=1.0, min_value=0.4, max_value=1.0, step=0.05)
    c = st.number_input("Korrosionstillägg c (mm)", value=1.0, step=0.1)

    auto_title = f"EN 13480-3 Kontroll – {material} – P {P:.1f} MPa – {datetime.now().strftime('%Y-%m-%d')}"
    use_custom = st.checkbox("Använd egen rapportrubrik?")
    custom_title = ""
    if use_custom:
        custom_title = st.text_input("Egen rubrik", "")
    rapportrubrik = custom_title.strip() if custom_title.strip() else auto_title
    st.markdown(f"**Rapportrubrik:** {rapportrubrik}")

# f_design
if material == "Annan":
    f_design = st.number_input("f vid T_design (MPa)", value=100.0)
else:
    mat = materials[material]
    if T_design < min(mat["temps"]) or T_design > max(mat["temps"]):
        st.warning("T utanför tabell → extrapolation")
    f_design = np.interp(T_design, mat["temps"], mat["f_values"])

st.write(f"**f_design = {f_design:.1f} MPa** vid {T_design}°C")

# Raka rör
with st.expander("Raka rör (§6.1)", expanded=True):
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
    status_rak = "Godkänt" if e_total <= t_nom else "Under dimensionerad"

    st.write(f"**Formel:** {formel_rak}")
    st.write(f"**e_total (inkl. c):** {e_total:.3f} mm")
    if status_rak == "Godkänt":
        st.success(f"**GODKÄNT §6.1** – t_nom ≥ e_total")
    else:
        st.error(f"**UNDER DIMENSIONERAD §6.1** – saknas {e_total - t_nom:.3f} mm")

# Böj
with st.expander("Böj (§6.2.3)"):
    use_boj = st.checkbox("Beräkna böj?")
    if use_boj:
        R = st.number_input("Böjradie R (mm)", value=D_o * 1.5)
        t_boj_nom = st.number_input("Böj t_nom (mm)", value=t_nom)

        r_d = R / D_o
        if r_d <= 0.5:
            e_int = e_ext = e_min
            st.warning("r/D_o ≤ 0.5 – använder raka rör-värde")
        else:
            e_int = e_min * (r_d - 0.25) / (r_d - 0.5)
            e_ext = e_min * (r_d + 0.25) / (r_d + 0.5)

        e_total_int = e_int + c
        e_total_ext = e_ext + c
        e_max_boj = max(e_total_int, e_total_ext)
        status_boj = "Godkänt" if e_max_boj <= t_boj_nom else "Under dimensionerad"

        st.write(f"**r/D_o =** {r_d:.3f}")
        st.write(f"**e_int (6.2.3-1):** {e_int:.3f} mm")
        st.write(f"**e_ext (6.2.3-2):** {e_ext:.3f} mm")
        st.write(f"**Total intrados/ext:** {e_total_int:.3f} / {e_total_ext:.3f} mm")
        if status_boj == "Godkänt":
            st.success(f"**GODKÄNT §6.2.3** – t_nom ≥ {e_max_boj:.3f}")
        else:
            st.error(f"**UNDER DIMENSIONERAD §6.2.3** – saknas {e_max_boj - t_boj_nom:.3f} mm")

# Reducer
with st.expander("Reducer (§6.5)"):
    use_reducer = st.checkbox("Beräkna reducer?")
    if use_reducer:
        D_large = st.number_input("Stor D_o (mm)", value=168.3)
        D_small = st.number_input("Liten d_o (mm)", value=114.3)
        alpha = st.number_input("Konvinkel α (°)", value=15.0, max_value=30.0)

        e_large = (P * D_large) / (2 * f_design * z + P) + c
        e_small = (P * D_small) / (2 * f_design * z + P) + c
        e_min_red = max(e_large, e_small)

        st.write(f"**e_min reducer:** {e_min_red:.3f} mm (max av ändar)")
        if alpha > 20:
            st.warning("α > 20° – extra förstärkning kan krävas §6.5.3")
        st.info("Formel: Max av raka rör-formel på båda ändar")

# Tee
with st.expander("Tee (§8.5)"):
    use_tee = st.checkbox("Beräkna tee?")
    if use_tee:
        d_o_tee = st.number_input("Branch d_o (mm)", value=60.3)
        t_tee_nom = st.number_input("Branch t_nom (mm)", value=5.0)

        A_req_tee = 2.5 * t_nom * d_o_tee
        excess_tee = max(0, t_tee_nom - e_min) * 2.5 * d_o_tee
        status_tee = "OK utan extra pad" if excess_tee >= A_req_tee else "Behöver förstärkning"

        st.write(f"**A_req tee approx:** {A_req_tee:.1f} mm²")
        st.write(f"**Excess area:** {excess_tee:.1f} mm²")
        if "OK" in status_tee:
            st.success(status_tee)
        else:
            st.warning(status_tee)

# Avstick
with st.expander("Avstick (§8.4.3)"):
    use_branch = st.checkbox("Beräkna avstick?")
    if use_branch:
        is_oblique = st.checkbox("Vinklad?")
        beta_deg = st.number_input("Vinkel φ/β från normalen (°)", 0.0, 45.0, 0.0) if is_oblique else 0.0
        beta_rad = np.deg2rad(beta_deg)

        d_o = st.number_input("d_o (mm)", value=60.3)
        t_b_nom = st.number_input("Branch t_nom (mm)", value=5.0)

        d_i = d_o - 2 * t_b_nom
        d_eff = d_i / np.cos(beta_rad) if is_oblique and np.cos(beta_rad) != 0 else d_i

        A_p_req = d_eff * t_nom * (2 - np.sin(np.deg2rad(90 - beta_deg)))

        ls = 2.5 * np.sqrt(D_o * max(t_nom - e_total, 0))

        excess_shell = max(0, t_nom - e_total) * min(ls, 2.5 * d_o)
        excess_branch = max(0, t_b_nom - e_total) * min(ls, 2.5 * d_o)

        A_f_pl = 0
        if st.checkbox("Pad?"):
            l_pl = st.number_input("l_pl (mm)", value=50.0)
            e_pl = st.number_input("e_pl (mm)", value=6.0)
            l_pl = min(l_pl, ls)
            e_pl = min(e_pl, t_nom)
            A_f_pl = l_pl * e_pl

        A_f_total = excess_shell + excess_branch + A_f_pl

        st.write("**Formler:** 8.4.3-3/8 (A_p), 8.4.1-2 (ls), 8.4.3-4/5 (pad)")
        st.write(f"A_p_req: {A_p_req:.1f} mm² | A_f total: {A_f_total:.1f} mm²")
        if A_f_total >= A_p_req:
            st.success("**OK §8.4.3**")
        else:
            st.error(f"**Otillräcklig** – saknas {A_p_req - A_f_total:.1f} mm²")

# Provtryckning
st.subheader("Provtryckning")
T_test = st.number_input("Testtemp (°C)", value=20.0, step=5.0)
f_test = np.interp(T_test, materials[material]["temps"], materials[material]["f_values"]) if material != "Annan" else st.number_input("f_test (MPa)", value=150.0)
P_test = max(1.25 * P * (f_test / f_design), 1.43 * P)
st.write(f"**P_test:** {P_test:.2f} MPa vid {T_test}°C")

# Sammanfattning
results = [
    ["Rapportrubrik", rapportrubrik],
    ["Material", material],
    ["P", f"{P:.2f} MPa"],
    ["T_design", f"{T_design} °C"],
    ["f_design", f"{f_design:.1f} MPa"],
    ["Raka rör – e_total", f"{e_total:.3f} mm"],
    ["Raka rör – status §6.1", status_rak],
    ["Provtryck P_test", f"{P_test:.2f} MPa"],
    ["Provtryckningstemp", f"{T_test} °C"],
    ["Beräknat", datetime.now().strftime("%Y-%m-%d %H:%M")]
]

if use_boj:
    results.extend([
        ["Böj – status §6.2.3", status_boj],
        ["Formler böj", "6.2.3-1 & 6.2.3-2"]
    ])

if use_reducer:
    results.append(["Reducer – e_min", f"{e_min_red:.3f} mm"])

if use_tee:
    results.append(["Tee – status §8.5", status_tee])

if use_branch:
    results.append(["Avstick – status §8.4.3", "OK" if A_f_total >= A_p_req else "Otillräcklig"])

df_summary = pd.DataFrame(results, columns=["Parameter", "Värde"])
st.subheader("Sammanfattning")
st.dataframe(df_summary)

# PDF
if st.button("Ladda ner PDF"):
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=letter)
    w, h = letter
    y = h - 40

    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, y, rapportrubrik)
    y -= 30

    c.setFont("Helvetica", 10)
    c.drawString(100, y, f"Beräknat: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    y -= 40

    for i, row in df_summary.iterrows():
        if row['Parameter'] == "Rapportrubrik":
            continue
        c.drawString(100, y, f"{row['Parameter']}: {row['Värde']}")
        y -= 20
        if y < 50:
            c.showPage()
            y = h - 40

    c.save()
    pdf_buffer.seek(0)
    st.download_button("Ladda ner PDF", pdf_buffer, "en13480_rapport.pdf", "application/pdf")
