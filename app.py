import streamlit as st
import json
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# -----------------------------------------------------------------------------
# 1. PAGE SETUP & CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(page_title="AI P&M Valuation Pro", layout="wide")
st.title("🏭 Automated AI Plant & Machinery Valuation Pro")
st.subheader("Upload multiple photos, documents, or material specs to get an advanced target valuation.")

# -----------------------------------------------------------------------------
# 2. SIDEBAR CONFIGURATION & REAL-TIME SCRAP RATES
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("🔑 Configuration")
    api_key = st.text_input("Enter Gemini API Key:", type="password")
    
    st.header("📈 Financial & Scrap Rules")
    indexation_factor = st.number_input("Cost Inflation Index Factor:", min_value=1.0, value=1.2, step=0.1)
    
    st.markdown("### 🪵 Live Scrap Benchmarks (₹/kg)")
    scrap_ms = st.number_input("Mild Steel (MS) Scrap Rate:", value=35.0)
    scrap_ss = st.number_input("Stainless Steel (SS) Scrap Rate:", value=95.0)
    scrap_ci = st.number_input("Cast Iron Scrap Rate:", value=32.0)
    scrap_copper = st.number_input("Copper Scrap Rate:", value=680.0)
    scrap_alu = st.number_input("Aluminium Scrap Rate:", value=120.0)

# Helper function to match scrap types to user sidebar settings
def get_scrap_rate(material_type: str) -> float:
    mat = material_type.lower()
    if "stainless" in mat or "ss" in mat:
        return scrap_ss
    elif "mild steel" in mat or "ms" in mat:
        return scrap_ms
    elif "cast iron" in mat or "iron" in mat:
        return scrap_ci
    elif "copper" in mat or "wire" in mat:
        return scrap_copper
    elif "aluminium" in mat or "aluminum" in mat:
        return scrap_alu
    return 25.0  # Default general mixed metal scrap fallback rate

# -----------------------------------------------------------------------------
# 3. ADVANCED EXTRACTION SCHEMA (MACHINERY VS. SCRAP)
# -----------------------------------------------------------------------------
class AdvancedAssetSchema(BaseModel):
    is_scrap_item: bool = Field(description="True if the uploaded item/photo represents raw scrap material, junk, or non-functional structural metal. False if it is a identifiable machine asset.")
    asset_name: str = Field(description="Name/Category of machine or type of scrap material (e.g., CNC Milling Machine or Mild Steel Heavy Melting Scrap)")
    manufacturer: str = Field(description="Brand or manufacturer. Use 'N/A' if raw scrap material.")
    primary_material: str = Field(description="Predominant material type observed (e.g., Mild Steel, Stainless Steel, Cast Iron, Copper, Aluminium).")
    estimated_weight_kg: float = Field(description="Best engineering estimate of total weight in Kilograms (KG) based on standard equipment weight parameters or visual volume.")
    original_cost: float = Field(description="Historical price/invoice value if found. Default to 0.0 if unknown or scrap.")
    age_years: int = Field(description="Estimated age of the asset. Set to 0 if pure raw scrap material.")
    estimated_useful_life_years: int = Field(description="Standard industrial useful life span for this category of asset.")

# -----------------------------------------------------------------------------
# 4. MULTI-FILE UPLOADER INTERFACE
# -----------------------------------------------------------------------------
uploaded_files = st.file_uploader(
    "Drag & Drop multiple files here (Upload asset photos, nameplates, or records together for absolute context)...", 
    type=["png", "jpg", "jpeg", "pdf"], 
    accept_multiple_files=True
)

if uploaded_files:
    st.success(f"Successfully staged {len(uploaded_files)} source verification files for processing.")
    
    # Render mini-thumbnails of uploaded images on the screen for the user
    cols = st.columns(min(len(uploaded_files), 5))
    for idx, idx_file in enumerate(uploaded_files[:5]):
        if idx_file.type in ["image/png", "image/jpeg", "image/jpg"]:
            cols[idx].image(idx_file, width=150, caption=f"File {idx+1}")

    if not api_key:
        st.warning("⚠️ Enter your Gemini API Key in the sidebar to activate the analysis engine.")
    else:
        if st.button("🚀 Execute Comprehensive Multi-File Valuation"):
            with st.spinner("AI Engine cross-referencing files and executing mathematical valuation models..."):
                try:
                    client = genai.Client(api_key=api_key)
                    
                    # Package ALL uploaded files into the AI request parts array
                    ai_contents = []
                    for f in uploaded_files:
                        f_bytes = f.read()
                        ai_contents.append(types.Part.from_bytes(data=f_bytes, mime_type=f.type))
                    
                    # Prompt guiding the multi-file reasoning logic
                    prompt = """
                    Analyze all the uploaded files together as a single unified target asset assessment.
                    Cross-examine details between close-ups, nameplates, or context sheets.
                    Determine cleanly if this represents a running asset or end-of-life scrap.
                    Estimate the total metric weight in KG based on known industrial weights for this material volume or size.
                    """
                    ai_contents.append(prompt)
                    
                    # Fire query to Gemini
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=ai_contents,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=AdvancedAssetSchema,
                            temperature=0.1
                        ),
                    )
                    
                    data = json.loads(response.text)
                    
                    # -----------------------------------------------------------------------------
                    # 5. DUAL ENGINE CALCULATION (DETERMINISTIC MATH)
                    # -----------------------------------------------------------------------------
                    is_scrap = data.get("is_scrap_item", False)
                    weight = data.get("estimated_weight_kg", 0.0)
                    material = data.get("primary_material", "Mild Steel")
                    
                    st.markdown("---")
                    st.success("✅ Multi-Source Valuation Model Finished Successfully!")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("### 📋 Unified Asset Attributes")
                        st.write(f"**Identified Classification:** {'🔴 SCRAP / LIQUIDATION MATERIAL' if is_scrap else '⚙️ FUNCTIONAL MACHINERY ASSET'}")
                        st.write(f"**Calculated Category/Name:** {data.get('asset_name')}")
                        st.write(f"**Inferred Primary Material:** {material}")
                        st.write(f"**AI Assessed Weight:** {weight:,.2f} KG")
                        if not is_scrap:
                            st.write(f"**Manufacturer/Brand:** {data.get('manufacturer')}")
                            st.write(f"**Assessed Age:** {data.get('age_years')} Years")
                            st.write(f"**Useful Life Span:** {data.get('estimated_useful_life_years')} Years")

                    with col2:
                        st.markdown("### 💰 Valuation & Math Engine Output")
                        
                        if is_scrap or data.get("original_cost", 0.0) == 0:
                            # --- SCRAP METHOD VALUE ---
                            per_kg_rate = get_scrap_rate(material)
                            final_valuation = weight * per_kg_rate
                            
                            st.metric(label="Calculated Net Scrap Value", value=f"₹ {final_valuation:,.2f}")
                            st.info(f"Basis of Valuation: Applied Scrap Rule for [{material}] @ ₹{per_kg_rate}/kg multiplied by estimated weight of {weight:,.2f} kg.")
                        
                        else:
                            # --- MACHINERY METHOD VALUE (Cost Approach) ---
                            orig_cost = data.get("original_cost", 0.0)
                            useful_life = data.get("estimated_useful_life_years", 15)
                            age = data.get("age_years", 0)
                            
                            gcrc = orig_cost * indexation_factor
                            scrap_rate_floor = get_scrap_rate(material)
                            salvage_floor_value = weight * scrap_rate_floor
                            
                            depreciable_amount = gcrc - salvage_floor_value
                            
                            if age >= useful_life:
                                final_valuation = salvage_floor_value
                            else:
                                annual_dep_rate = depreciable_amount / useful_life
                                final_valuation = gcrc - (annual_dep_rate * age)
                            
                            # Standard safety check: machine valuation shouldn't drop under its raw melt scrap value floor
                            if final_valuation < salvage_floor_value:
                                final_valuation = salvage_floor_value
                                st.warning("⚠️ Asset value depreciated below scrap metal value. Floor scrap pricing applied.")
                                
                            st.metric(label="Calculated Operational Fair Value", value=f"₹ {final_valuation:,.2f}")
                            st.write(f"**Gross Current Replacement Cost (GCRC):** ₹ {gcrc:,.2f}")
                            st.write(f"**Inherent Material Floor Value:** ₹ {salvage_floor_value:,.2f}")
                            st.write(f"**Historical Purchase Cost:** ₹ {orig_cost:,.2f}")
                            
                except Exception as e:
                    st.error(f"Processing error encountered: {e}")
