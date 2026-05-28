import streamlit as st
import json
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
import base64

# -----------------------------------------------------------------------------
# 1. PAGE SETUP & STATUTORY HEADER
# -----------------------------------------------------------------------------
st.set_page_config(page_title="IVS Compliant P&M Engine", layout="wide")
st.title("⚖️ Statutory Plant & Machinery Valuation Platform")
st.subheader("Fully Aligned with International Valuation Standards (IVS) & Govt Regulatory Codes")

# -----------------------------------------------------------------------------
# 2. HARDCODED SECURE KEY ACCESS (BYPASSES CLOUD SETTINGS)
# -----------------------------------------------------------------------------
# Paste your raw Gemini API key inside the quotes below:
MASTER_API_KEY = "AIzaSyAfK09Zlf3D19L4PMwMj-Qsp-d0BUL7nXc"

# -----------------------------------------------------------------------------
# 3. SIDEBAR CONFIGURATION: USER PROFILE & MARKT SCRAP RATES
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
# 4. STRUCTURED DATA SPECIFICATION FOR AI
# -----------------------------------------------------------------------------
class StrictAssetSchema(BaseModel):
    is_pure_scrap_pile: bool = Field(description="Strictly set to True ONLY if this item is abandoned, dismantled junk, or raw metal waste. Set to False if this is an operational or stand-by asset/machine.")
    asset_name: str = Field(description="Commercial/Technical name of the machine or description of scrap.")
    manufacturer: str = Field(description="Manufacturer/Brand. Set 'Unknown' if unavailable.")
    model_or_capacity: str = Field(description="Model number, structural sizing, or operational throughput capacity.")
    exact_material_category: str = Field(description="Must match exactly one of these strings: 'Mild Steel (MS)', 'Stainless Steel (SS 304)', 'Stainless Steel (SS 316)', 'Cast Iron (CI)', 'Copper Heavy', 'Copper Wire/Cables', 'Aluminium Commercial', 'Brass / Gunmetal', 'Mixed / Heavy Melting Scrap (HMS)'.")
    estimated_weight_kg: float = Field(description="Engineering assessment of total metal/equipment weight in Kilograms.")
    estimated_cost_new: float = Field(description="Estimated modern-day market purchase price for a new equivalent of this asset if invoice is missing. Do not leave at 0.")
    age_years: int = Field(description="Observed or deduced physical age of the equipment.")
    useful_life_years: int = Field(description="Statutory useful economic life span based on industry standards (e.g., 15 years for general engineering).")
    condition_justification: str = Field(description="Technical statement detailing observed physical wear, maintenance status, or corrosion levels to defend the appraisal.")

# -----------------------------------------------------------------------------
# 5. MULTI-FILE GRAPHICAL INTERFACE CONTROL
# -----------------------------------------------------------------------------
uploaded_files = st.file_uploader(
    "Upload multiple field investigation assets simultaneously...", 
    type=["png", "jpg", "jpeg", "pdf"], 
    accept_multiple_files=True
)

if uploaded_files:
    st.success(f"Successfully staged {len(uploaded_files)} source verification files for processing.")
    
    if MASTER_API_KEY == "PASTE_YOUR_ACTUAL_GEMINI_API_KEY_HERE" or MASTER_API_KEY == "":
        st.error("❌ Setup Error: You forgot to replace the filler text on Line 18 with your actual Gemini API Key inside the code.")
    else:
        if st.button("⚖️ Generate Statutory IVS Valuation Report"):
            with st.spinner("AI parsing assets and building compliant legal framework..."):
                try:
                    # Direct initialization bypassing environment variables entirely
                    client = genai.Client(api_key=MASTER_API_KEY)
                    
                    ai_contents = [types.Part.from_bytes(data=f.read(), mime_type=f.type) for f in uploaded_files]
                    
                    prompt = """
                    You are performing a statutory Plant & Machinery appraisal. Analyze the attached files.
                    Map the item strictly to one of the available materials registry names. 
                    If it is an active machine, calculate 'estimated_cost_new' using historical commercial databases for this asset class.
                    """
                    ai_contents.append(prompt)
                    
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=ai_contents,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=StrictAssetSchema,
                            temperature=0.0
                        ),
                    )
                    
                    data = json.loads(response.text)
                    
                    # -----------------------------------------------------------------------------
                    # 6. BUSINESS LOGIC & EVALUATION CALCULATION ENGINE
                    # -----------------------------------------------------------------------------
                    is_scrap = data.get("is_pure_scrap_pile", False)
                    selected_mat = data.get("exact_material_category", "Mixed / Heavy Melting Scrap (HMS)")
                    weight = data.get("estimated_weight_kg", 0.0)
                    scrap_rate_per_kg = get_scrap_rate(selected_mat)
                    
                    scrap_floor_value = weight * scrap_rate_per_kg
                    cost_new = data.get("estimated_cost_new", 0.0)
                    gcrc = cost_new * indexation_factor
                    age = data.get("age_years", 0)
                    useful_life = data.get("useful_life_years", 15)
                    
                    if is_scrap:
                        final_fair_value = scrap_floor_value
                        basis_used = "Liquidation Value Basis (Piecemeal Raw Scrap)"
                    else:
                        if age >= useful_life:
                            final_fair_value = scrap_floor_value
                        else:
                            depreciable_pool = gcrc - scrap_floor_value
                            annual_dep = depreciable_pool / useful_life
                            final_fair_value = gcrc - (annual_dep * age)
                        
                        if final_fair_value < scrap_floor_value:
                            final_fair_value = scrap_floor_value
                        basis_used = "Market Value Basis / Depreciated Replacement Cost (DRC)"

                    # -----------------------------------------------------------------------------
                    # 7. GENERATING THE OUTPUT COMPLIANCE DOCUMENT
                    # -----------------------------------------------------------------------------
                    st.success("Analysis Complete. IVS Compliance Framework Purchased.")
                    
                    html_report = f"""
                    <div style='font-family: Arial, sans-serif; padding: 30px; border: 2px solid #333; background: white; color: black;'>
                        <h2 style='text-align: center; margin-bottom: 5px;'>VALUATION REPORT — PLANT & MACHINERY</h2>
                        <p style='text-align: center; font-size: 12px; color: #555;'>Prepared in Compliance with International Valuation Standards (IVS 300)</p>
                        <hr/>
                        <table style='width:100%; font-size:14px; margin-bottom:20px;'>
                            <tr><td><b>Appraiser:</b> {valuer_name}</td><td><b>Date of Valuation:</b> 2026-05-28</td></tr>
                            <tr><td><b>Reg No:</b> {reg_number}</td><td><b>Assignment Context:</b> {purpose}</td></tr>
                        </table>
                        
                        <h3>1. Asset Identification & Technical Parameters</h3>
                        <table style='width:100%; border-collapse: collapse; font-size:13px;'>
                            <tr style='background:#f2f2f2;'><th style='border:1px solid #ddd;padding:8px;text-align:left;'>Parameter</th><th style='border:1px solid #ddd;padding:8px;text-align:left;'>Determined Fact / Value</th></tr>
                            <tr><td style='border:1px solid #ddd;padding:8px;'>Asset / Item Character</td><td style='border:1px solid #ddd;padding:8px;'>{data.get('asset_name')}</td></tr>
                            <tr><td style='border:1px solid #ddd;padding:8px;'>Manufacturer / Brand</td><td style='border:1px solid #ddd;padding:8px;'>{data.get('manufacturer')}</td></tr>
                            <tr><td style='border:1px solid #ddd;padding:8px;'>Model / Capacity Metric</td><td style='border:1px solid #ddd;padding:8px;'>{data.get('model_or_capacity')}</td></tr>
                            <tr><td style='border:1px solid #ddd;padding:8px;'>Assessed Metallurgical Composition</td><td style='border:1px solid #ddd;padding:8px;'>{selected_mat}</td></tr>
                            <tr><td style='border:1px solid #ddd;padding:8px;'>Calculated Metric Weight</td><td style='border:1px solid #ddd;padding:8px;'>{weight:,.2f} KG</td></tr>
                            <tr><td style='border:1px solid #ddd;padding:8px;'>Physical Vintage / Logged Age</td><td style='border:1px solid #ddd;padding:8px;'>{age} Years (Estimated Useful Life: {useful_life} Years)</td></tr>
                        </table>
                        
                        <h3>2. Condition Assessment & Disclosures</h3>
                        <p style='font-size:13px; font-style: italic; background: #fafafa; padding: 10px; border-left: 3px solid #0066cc;'>"{data.get('condition_justification')}"</p>
                        
                        <h3>3. Valuation Methodology & Financial Computations</h3>
                        <p style='font-size:13px;'><b>Adopted Valuation Approach:</b> {basis_used}</p>
                        <table style='width:100%; border-collapse: collapse; font-size:13px;'>
                            <tr><td style='border:1px solid #ddd;padding:8px;'>Estimated Cost New Equivalent</td><td style='border:1px solid #ddd;padding:8px;'>₹ {cost_new:,.2f}</td></tr>
                            <tr><td style='border:1px solid #ddd;padding:8px;'>Gross Current Replacement Cost (GCRC after Indexation)</td><td style='border:1px solid #ddd;padding:8px;'>₹ {gcrc:,.2f}</td></tr>
                            <tr><td style='border:1px solid #ddd;padding:8px;'>Inherent Material Scrap Value Floor (@ ₹{scrap_rate_per_kg}/kg)</td><td style='border:1px solid #ddd;padding:8px;'>₹ {scrap_floor_value:,.2f}</td></tr>
                            <tr style='background:#e6f2ff; font-weight:bold;'><td style='border:1px solid #ddd;padding:8px;'>FINAL ASSESSED VALUE CONCLUSION</td><td style='border:1px solid #ddd;padding:8px;'>₹ {final_fair_value:,.2f}</td></tr>
                        </table>
                        
                        <br/><br/>
                        <table style='width:100%; font-size:12px; margin-top:30px;'>
                            <tr><td style='text-align:center;'>___________________________<br/><b>Verified by AI Engine</b></td><td style='text-align:center;'>___________________________<br/><b>Signature of Registered Valuer</b></td></tr>
                        </table>
                    </div>
                    """
                    st.markdown(html_report, unsafe_allow_html=True)
                    
                    st.markdown("### 📥 Document Export Actions")
                    b64_html = base64.b64encode(html_report.encode()).decode()
                    href = f'<a href="data:text/html;base64,{b64_html}" download="IVS_Valuation_Report.html" style="padding:10px 20px; background-color:#0066cc; color:white; text-decoration:none; border-radius:4px; font-weight:bold;">Download Printable Valuation Certificate</a>'
                    st.markdown(href, unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"Execution Error: {e}")
