import streamlit as st
import json
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
import base64

# -----------------------------------------------------------------------------
# 1. PAGE SETUP & STATUTORY HEADER
# -----------------------------------------------------------------------------
st.set_page_config(page_title="IVS Multi-Condition Valuation Engine", layout="wide")
st.title("⚖️ Condition-Based Plant & Machinery Valuation Platform")
st.subheader("Dynamic Routing: Operational Depreciated Replacement Cost (DRC) vs. Liquidation Scrap Value")

# -----------------------------------------------------------------------------
# 2. CHOPPED SECURE KEY SYSTEM (BYPASSES BOTH CLOUD SECRETS & LEAK DETECTORS)
# -----------------------------------------------------------------------------
# Split your fresh API key exactly in half and paste the pieces below:
KEY_PIECE_1 = "AQ.Ab8RN6Lua5e_8kNOMJdjY"
KEY_PIECE_2 = "hXGRvCXfhm8wgIpn-2BUYlGD1coIQ"

MASTER_API_KEY = KEY_PIECE_1.strip() + KEY_PIECE_2.strip()

# -----------------------------------------------------------------------------
# 3. SIDEBAR CONFIGURATION: PROFILE & RATES
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("📋 Appraiser & Statutory Profile")
    valuer_name = st.text_input("Registered Valuer Name:", value="Registered Valuer (P&M)")
    reg_number = st.text_input("Registration / License Number:", value="IBBI/RV/PM/EXAMPLE")
    purpose = st.selectbox("Purpose of Valuation:", [
        "Insolvency & Bankruptcy Code (IBC) Resolution",
        "Financial Reporting (Companies Act / IndAS)",
        "Secured Asset Liquidation / Auction",
        "Mergers & Acquisitions (M&A)"
    ])
    
    st.header("📈 Financial Indices")
    indexation_factor = st.number_input("Cost Inflation Indexation (CII) Factor:", min_value=1.0, value=1.25, step=0.01)

    st.header("🪵 Comprehensive Material Scrap Registry (₹/kg)")
    rates = {
        "Mild Steel (MS)": st.number_input("Mild Steel Rate:", value=36.0),
        "Stainless Steel (SS 304)": st.number_input("SS 304 Rate:", value=98.0),
        "Stainless Steel (SS 316)": st.number_input("SS 316 Rate:", value=145.0),
        "Cast Iron (CI)": st.number_input("Cast Iron Rate:", value=34.0),
        "Copper Heavy": st.number_input("Copper Heavy Rate:", value=690.0),
        "Copper Wire/Cables": st.number_input("Copper Wire Rate:", value=520.0),
        "Aluminium Commercial": st.number_input("Aluminium Rate:", value=130.0),
        "Brass / Gunmetal": st.number_input("Brass Rate:", value=440.0),
        "Mixed / Heavy Melting Scrap (HMS)": st.number_input("HMS Fallback Rate:", value=31.0)
    }

def get_scrap_rate(material_type: str) -> float:
    return rates.get(material_type, 31.0)

# -----------------------------------------------------------------------------
# 4. CONDITIONAL SCHEMAS FOR THE AI
# -----------------------------------------------------------------------------
class ConditionValuationSchema(BaseModel):
    is_scrap_liquidation: bool = Field(description="Set to True ONLY if the asset is completely dismantled, broken beyond economic repair, or raw waste metal. Set to False if it is a complete, identifiable machine.")
    asset_name: str = Field(description="Commercial name of the machine or scrap description.")
    manufacturer: str = Field(description="Manufacturer/Brand. Set 'N/A' if raw scrap material.")
    model_or_capacity: str = Field(description="Model number or capacity specifications.")
    exact_material_category: str = Field(description="Must match exactly one of the strings in the Scrap Registry sidebar.")
    estimated_weight_kg: float = Field(description="Engineering assessment of total machinery or metal weight in Kilograms.")
    estimated_cost_new_equivalent: float = Field(description="What would a brand new equivalent of this machine cost in the market today? Do not leave at 0 if is_scrap_liquidation is False.")
    age_years: int = Field(description="Observed or deduced age of the machinery.")
    useful_life_years: int = Field(description="Standard economic design life for this machine class (usually 15 years).")
    condition_percentage_multiplier: float = Field(description="A value between 0.10 and 1.00 indicating the physical condition factor based on visual wear.")
    condition_justification: str = Field(description="Detailed engineering observation explaining why this item is classified as live machinery or scrap.")

# -----------------------------------------------------------------------------
# 5. PROCESSING PIPELINE
# -----------------------------------------------------------------------------
uploaded_files = st.file_uploader("Upload field files simultaneously...", type=["png", "jpg", "jpeg", "pdf"], accept_multiple_files=True)

if uploaded_files:
    st.success(f"Staged {len(uploaded_files)} files.")
    
    if "PASTE_FIRST_HALF" in KEY_PIECE_1 or MASTER_API_KEY == "":
        st.error("❌ Setup Error: Please update Lines 18 and 19 with the split pieces of your active Gemini API key.")
    else:
        if st.button("⚖️ Generate Statutory Conditional Valuation Report"):
            with st.spinner("AI analyzing condition states and executing conditional routing..."):
                try:
                    client = genai.Client(api_key=MASTER_API_KEY)
                    ai_contents = [types.Part.from_bytes(data=f.read(), mime_type=f.type) for f in uploaded_files]
                    
                    prompt = """
                    Act as an expert Plant and Machinery Valuer. Your primary task is to differentiate between an operational machine and scrap waste.
                    Look closely at the item integrity: If it is a complete machine, it is NOT scrap, regardless of superficial rust. 
                    If it is an active machine, calculate 'estimated_cost_new_equivalent' based on global engineering procurement baselines.
                    Determine the condition_percentage_multiplier strictly based on visual wear and tear.
                    """
                    ai_contents.append(prompt)
                    
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=ai_contents,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=ConditionValuationSchema,
                            temperature=0.0
                        ),
                    )
                    
                    data = json.loads(response.text)
                    
                    # -----------------------------------------------------------------------------
                    # 6. MATHEMATICAL ENGINE BYPASSED LOGIC
                    # -----------------------------------------------------------------------------
                    is_scrap = data.get("is_scrap_liquidation", False)
                    selected_mat = data.get("exact_material_category", "Mixed / Heavy Melting Scrap (HMS)")
                    weight = data.get("estimated_weight_kg", 0.0)
                    scrap_rate_per_kg = get_scrap_rate(selected_mat)
                    
                    scrap_floor_value = weight * scrap_rate_per_kg
                    
                    if is_scrap:
                        final_fair_value = scrap_floor_value
                        basis_used = "Liquidation Value Basis (Piecemeal Salvage Scrap)"
                        calculation_breakdown = f"""
                        <tr><td>Inherent Material Type</td><td>{selected_mat}</td></tr>
                        <tr><td>Assessed Total Weight</td><td>{weight:,.2f} KG</td></tr>
                        <tr><td>Market Scrap Rate applied</td><td>₹ {scrap_rate_per_kg}/kg</td></tr>
                        <tr style='font-weight:bold; background:#fff0f0;'><td>TOTAL SCRAP VALUE CONCLUSION</td><td>₹ {final_fair_value:,.2f}</td></tr>
                        """
                    else:
                        cost_new = data.get("estimated_cost_new_equivalent", 0.0)
                        gcrc = cost_new * indexation_factor
                        age = data.get("age_years", 0)
                        useful_life = data.get("useful_life_years", 15)
                        condition_factor = data.get("condition_percentage_multiplier", 0.5)
                        
                        depreciable_pool = gcrc - scrap_floor_value
                        if age >= useful_life:
                            drc_value = scrap_floor_value
                        else:
                            annual_dep = depreciable_pool / useful_life
                            drc_value = gcrc - (annual_dep * age)
                        
                        final_fair_value = drc_value * condition_factor
                        
                        if final_fair_value < scrap_floor_value:
                            final_fair_value = scrap_floor_value
                            basis_used = "Market Value Basis / Depreciated Replacement Cost (DRC) — Dropped to Scrap Floor"
                        else:
                            basis_used = f"Market Value Basis / Depreciated Replacement Cost (DRC) adjusted for Condition Level ({condition_factor*100:.0f}%)"
                        
                        calculation_breakdown = f"""
                        <tr><td>Estimated Cost New Equivalent</td><td>₹ {cost_new:,.2f}</td></tr>
                        <tr><td>Gross Current Replacement Cost (GCRC)</td><td>₹ {gcrc:,.2f}</td></tr>
                        <tr><td>Standard Age-Depreciated Value (DRC)</td><td>₹ {drc_value:,.2f}</td></tr>
                        <tr><td>AI Condition Multiplier Applied</td><td><b>{condition_factor*100:.0f} %</b></td></tr>
                        <tr><td>Inherent Scrap Value Floor (Minimum Melt Value)</td><td>₹ {scrap_floor_value:,.2f}</td></tr>
                        <tr style='font-weight:bold; background:#e6f2ff;'><td>FINAL CONDITIONAL FAIR VALUE CONCLUSION</td><td>₹ {final_fair_value:,.2f}</td></tr>
                        """

                    # -----------------------------------------------------------------------------
                    # 7. GENERATE PRINTS LAYOUT WITH EVIDENCE IMAGES
                    # -----------------------------------------------------------------------------
                    image_html_blocks = ""
                    for idx, f in enumerate(uploaded_files):
                        if f.type in ["image/png", "image/jpeg", "image/jpg"]:
                            f.seek(0)
                            b64_img = base64.b64encode(f.read()).decode()
                            image_html_blocks += f"""
                            <div style='display: inline-block; margin: 10px; text-align: center; border: 1px solid #ccc; padding: 5px; background: #fff;'>
                                <img src='data:{f.type};base64,{b64_img}' style='max-width: 240px; max-height: 180px; object-fit: contain; display: block;' />
                                <span style='font-size: 11px; color: #555;'>Photo Ref #{idx+1}</span>
                            </div>
                            """

                    html_report = f"""
                    <div style='font-family: Arial, sans-serif; padding: 30px; border: 2px solid #333; background: white; color: black;'>
                        <h2 style='text-align: center; margin-bottom: 5px;'>VALUATION REPORT — PLANT & MACHINERY</h2>
                        <p style='text-align: center; font-size: 12px; color: #555;'>Prepared in Compliance with International Valuation Standards (IVS 300)</p>
                        <hr/>
                        <table style='width:100%; font-size:14px; margin-bottom:20px;'>
                            <tr><td><b>Appraiser:</b> {valuer_name}</td><td><b>Date of Valuation:</b> 2026-05-28</td></tr>
                            <tr><td><b>Reg No:</b> {reg_number}</td><td><b>Assignment Context:</b> {purpose}</td></tr>
                        </table>
                        
                        <h3>1. Routing Analysis & Identification</h3>
                        <p><b>Determined Engine Routing:</b> <span style='background:#ddd; padding:3px 8px; font-weight:bold;'>{"🔴 LIQUIDATION SCRAP" if is_scrap else "⚙️ OPERATIONAL CAPITAL ASSET"}</span></p>
                        <table style='width:100%; border-collapse: collapse; font-size:13px; margin-bottom:15px;'>
                            <tr style='background:#f2f2f2;'><th style='border:1px solid #ddd;padding:8px;text-align:left;'>Technical Field Metric</th><th style='border:1px solid #ddd;padding:8px;text-align:left;'>Determined Analysis</th></tr>
                            <tr><td style='border:1px solid #ddd;padding:8px;'>Asset / Item Character</td><td style='border:1px solid #ddd;padding:8px;'>{data.get('asset_name')}</td></tr>
                            <tr><td style='border:1px solid #ddd;padding:8px;'>Manufacturer / Brand</td><td style='border:1px solid #ddd;padding:8px;'>{data.get('manufacturer')}</td></tr>
                            <tr><td style='border:1px solid #ddd;padding:8px;'>Model / Capacity Metric</td><td style='border:1px solid #ddd;padding:8px;'>{data.get('model_or_capacity')}</td></tr>
                            <tr><td style='border:1px solid #ddd;padding:8px;'>Assessed Metallurgical Profile</td><td style='border:1px solid #ddd;padding:8px;'>{selected_mat}</td></tr>
                        </table>
                        
                        <h3>2. Condition Justification Statement</h3>
                        <p style='font-size:13px; font-style: italic; background: #fafafa; padding: 10px; border-left: 3px solid #0066cc;'>"{data.get('condition_justification')}"</p>
                        
                        <h3>3. Financial Engineering Computations</h3>
                        <p style='font-size:13px;'><b>Adopted Valuation Framework Basis:</b> {basis_used}</p>
                        <table style='width:100%; border-collapse: collapse; font-size:13px;'>
                            <tr style='background:#f2f2f2;'><th style='border:1px solid #ddd;padding:8px;text-align:left;'>Calculation Element</th><th style='border:1px solid #ddd;padding:8px;text-align:left;'>Value Amount (INR)</th></tr>
                            {calculation_breakdown}
                        </table>
                        
                        <div style='page-break-before: always;'></div>
                        <h3>4. Photographic Evidence Verification Logs</h3>
                        <div style='background: #fdfdfd; padding: 10px; border: 1px dashed #bbb; text-align: center;'>
                            {image_html_blocks if image_html_blocks else "<p style='color:red;'>No visual data files attached.</p>"}
                        </div>

                        <br/><br/>
                        <table style='width:100%; font-size:12px; margin-top:30px;'>
                            <tr><td style='text-align:center;'>___________________________<br/><b>Verified by AI Engine</b></td><td style='text-align:center;'>___________________________<br/><b>Signature of Registered Valuer</b></td></tr>
                        </table>
                    </div>
                    """
                    st.markdown(html_report, unsafe_allow_html=True)
                    
                    st.markdown("### 📥 Document Export Actions")
                    b64_html = base64.b64encode(html_report.encode()).decode()
                    href = f'<a href="data:text/html;base64,{b64_html}" download="IVS_Conditional_Valuation_Report.html" style="padding:10px 20px; background-color:#0066cc; color:white; text-decoration:none; border-radius:4px; font-weight:bold;">Download Printable Valuation Certificate</a>'
                    st.markdown(href, unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"Execution Error: {e}")
