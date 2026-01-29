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

# Allmänna indata
with st.expander("Grunddata (obligatoriskt)", expanded=True):
    material = st.selectbox("Material (EN 13480-2)", list(materials.keys()))
    P = st.number_input("Designtryck P (MPa)", min_value=0.0, value=1.0, step=0.1)
    T_design = st.number_input("Designtemperatur T (°C)", min_value=-50.0, value=100.0, step=10.0)
    z = st.number_input("Fogfaktor z", min_value=0.4, max_value=1.0, value=1.0, step=0.05)
    c = st.number_input("Korrosions-/slitagetillägg c (mm)", min_value=0.0, value=1.0, step=0.1)

# f_design
if material == "Annan":
    f_design = st.number_input("Tillåten spänning f vid T_design (MPa)", value=100.0)
else:
    mat = materials[material]
    if T_design < min(mat["temps"]) or T_design > max(mat["temps"]):
        st.warning("T utanför tabell – konstant extrapolation (kontrollera standarden)")
    f_design = np.interp(T_design, mat["temps"], mat["f_values"])

st.write(f"**Tillåten spänning f vid {T_design}°C:** {f_design:.1f} MPa (EN 13480-2)")

# Raka rör
with st.expander("Raka rör (§6.1)", expanded=True):
    D_o = st.number_input("Yttre diameter D_o (mm)", value=168.3, step=1.0)
    t_nom = st.number_input("Nominell väggtjocklek t_nom (mm)", value=7.1, step=0.1)

    D_i = D_o - 2 * t_nom
    ratio = D_o / D_i if D_i > 0 else 1.0
    st.write(f"**D_o / D_i =** {ratio:.3f}")

    if ratio <= 1.7:
        e_min = (P * D_o) / (2 * f_design * z + P)
        formel_rak = "6.1-1"
    else:
        e_min = (D_o / 2) * (1 - np.sqrt((f_design * z - P) / (f_design * z + P)))
        formel_rak = "6.1-3 (Lamé)"

    e_total = e_min + c
    st.write(f"**Formel:** {formel_rak}")
    st.write(f"**e_min (utan c):** {e_min:.3f} mm")
    st.write(f"**e_total (inkl. c):** {e_total:.3f} mm")

    if e_total <= t_nom:
        st.success(f"**GODKÄNT enligt §6.1** – t_nom ({t_nom:.2f} mm) ≥ e_total ({e_total:.3f} mm)")
    else:
        st.error(f"**UNDER DIMENSIONERAD enligt §6.1** – saknas {e_total - t_nom:.3f} mm")

# Böj
with st.expander("Böj (elbow) enligt §6.2.3"):
    use_boj = st.checkbox("Aktivera beräkning för böj?")
    if use_boj:
        R = st.number_input("Böjradie R (mm)", value=D_o * 1.5, step=10.0)
        t_boj_nom = st.number_input("Böj nominell tjocklek t_nom (mm)", value=t_nom, step=0.1)

        r_d = R / D_o
        if r_d <= 0.5:
            st.warning("r/D_o ≤ 0.5 – använder e från raka rör (kontrollera standarden)")
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
            st.success(f"**GODKÄNT §6.2.3** – t_nom ({t_boj_nom:.2f} mm) ≥ max e ({e_max_boj:.3f} mm)")
        else:
            st.error(f"**UNDER DIMENSIONERAD §6.2.3** – saknas {e_max_boj - t_boj_nom:.3f} mm")

# Avstick
with st.expander("Avstick / Branch (§8.4.3)"):
    use_branch = st.checkbox("Aktivera avstick-beräkning?")
    if use_branch:
        is_oblique = st.checkbox("Vinklad (oblique)?")
        beta_deg = st.number_input("Vinkel φ/β från normalen (°)", 0.0, 45.0, 0.0) if is_oblique else 0.0
        beta_rad = np.deg2rad(beta_deg)

        d_o = st.number_input("Branch yttre diameter d_o (mm)", value=60.3)
        t_b_nom = st.number_input("Branch tjocklek t_b nom (mm)", value=5.0)

        d_i = d_o - 2 * t_b_nom
        d_eff = d_i / np.cos(beta_rad) if is_oblique and np.cos(beta_rad) != 0 else d_i  # (8.4.3-8)

        A_p_req = d_eff * t_nom * (2 - np.sin(np.deg2rad(90 - beta_deg)))  # approx baserat på 8.4.3-3 + vinkel

        ls = 2.5 * np.sqrt(D_o * max(t_nom - e_total, 0))  # approx (8.4.1-2)

        excess_shell = max(0, t_nom - e_total) * min(ls, 2.5 * d_o)
        excess_branch = max(0, t_b_nom - e_total) * min(ls, 2.5 * d_o)

        A_f_pl = 0
        if st.checkbox("Använd reinforcing pad?"):
            l_pl = st.number_input("Pad längd/bredd l_pl (mm)", value=50.0)
            e_pl = st.number_input("Pad tjocklek e_pl (mm)", value=6.0)
            l_pl = min(l_pl, ls)  # (8.4.3-4)
            e_pl = min(e_pl, t_nom)  # (8.4.3-5)
            A_f_pl = l_pl * e_pl

        A_f_total = excess_shell + excess_branch + A_f_pl

        st.write("**Använda formler (approx):")
        st.write("- d_eff enligt (8.4.3-8) vid oblique")
        st.write("- A_p_req ≈ d_eff * t_nom * (2 - sin(90-β)) (baserat på 8.4.3-3)")
        st.write("- ls ≈ 2.5 √(D_o × excess_t) (från 8.4.1-2)")
        st.write("- Pad begränsad enligt (8.4.3-4) & (8.4.3-5)")
        st.write("- Area-check enligt (8.4.3-6)")

        st.write(f"**Required area A_p:** {A_p_req:.1f} mm²")
        st.write(f"**Available area A_f:** {A_f_total:.1f} mm²")

        if A_f_total >= A_p_req:
            st.success("**OK enligt §8.4.3** – reinforcement tillräcklig (8.4.3-6)")
        else:
            st.error(f"**Otillräcklig enligt §8.4.3** – saknas {A_p_req - A_f_total:.1f} mm². Kontrollera (8.4.3-6/7) manuellt")

# Provtryckning
st.subheader("Provtryckning (EN 13480-5)")
T_test = st.number_input("Testtemperatur (°C)", value=20.0, step=5.0)
f_test = np.interp(T_test, materials[material]["temps"], materials[material]["f_values"]) if material != "Annan" else st.number_input("f_test (MPa)", value=150.0)
P_test = max(1.25 * P * (f_test / f_design), 1.43 * P)
st.write(f"**Provtryck P_test:** {P_test:.2f} MPa (max av 1.25×P×(f_test/f_design) och 1.43×P)")

# Sammanfattning
results = [
    ["Material", material],
    ["Designtryck P", f"{P:.2f} MPa"],
    ["Designtemp T", f"{T_design} °C"],
    ["f_design", f"{f_design:.1f} MPa"],
    ["Raka rör – D_o", f"{D_o} mm"],
    ["Raka rör – t_nom", f"{t_nom:.2f} mm"],
    ["Raka rör – e_total (inkl c)", f"{e_total:.3f} mm"],
    ["Formel raka rör", formel_rak],
    ["Status raka rör §6.1", "Godkänt" if e_total <= t_nom else "Under dimensionerad"]
]

if use_boj:
    results.extend([
        ["Böj – r/D_o", f"{r_d:.3f}"],
        ["Böj – e_int (exkl c)", f"{e_int:.3f} mm"],
        ["Böj – e_ext (exkl c)", f"{e_ext:.3f} mm"],
        ["Böj – t_nom", f"{t_boj_nom:.2f} mm"],
        ["Formler böj", "6.2.3-1 & 6.2.3-2"],
        ["Status böj §6.2.3", "Godkänt" if max(e_total_int, e_total_ext) <= t_boj_nom else "Under dimensionerad"]
    ])

if use_branch:
    results.extend([
        ["Avstick – d_o", f"{d_o} mm"],
        ["Avstick – A_p_req", f"{A_p_req:.1f} mm²"],
        ["Avstick – A_f total", f"{A_f_total:.1f} mm²"],
        ["Formler avstick", "8.4.3-3/4/5/6/8"],
        ["Status avstick §8.4.3", "OK" if A_f_total >= A_p_req else "Otillräcklig"]
    ])

results.extend([
    ["Provtryck P_test", f"{P_test:.2f} MPa"],
    ["Beräknat", datetime.now().strftime("%Y-%m-%d %H:%M")]
])

df_summary = pd.DataFrame(results, columns=["Parameter", "Värde"])
st.subheader("Sammanfattning – Kvalitetsunderlag")
st.dataframe(df_summary.style.applymap(lambda x: 'background-color: #d4edda' if 'Godkänt' in x or 'OK' in x else 'background-color: #f8d7da' if 'Under' in x or 'Otillräcklig' in x else ''))

# PDF – ren text
if st.button("Generera PDF-rapport"):
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=letter)
    w, h = letter
    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, h - 40, "EN 13480-3 Snabbkontroll – Kvalitetsunderlag")
    c.setFont("Helvetica", 10)
    c.drawString(100, h - 60, f"Beräknat: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Material: {material}")

    y = h - 100
    for _, row in df_summary.iterrows():
        c.drawString(100, y, f"{row['Parameter']}: {row['Värde']}")
        y -= 18
        if y < 50:
            c.showPage()
            y = h - 50

    c.save()
    pdf_buffer.seek(0)
    st.download_button(
        label="Ladda ner PDF-rapport",
        data=pdf_buffer,
        file_name=f"en13480_kontroll_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
        mime="application/pdf"
    )
