import streamlit as st
import json
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# -----------------------------------------------------------------------------
# 1. PAGE SETUP & CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(page_title="AI P&M Valuation Engine", layout="wide")
st.title("🏭 AI-Powered Plant & Machinery Valuation Engine")
st.subheader("Upload an asset photo, nameplate, or invoice to generate an automated valuation.")

# -----------------------------------------------------------------------------
# 2. API CREDENTIALS MANAGEMENT
# -----------------------------------------------------------------------------
# Enter your Gemini API key in the sidebar of the webpage to activate the AI
with st.sidebar:
    st.header("🔑 Configuration")
    api_key = st.text_input("Enter Gemini API Key:", type="password")
    st.markdown("[Get a free API key here](https://aistudio.google.com/)")
    
    st.header("📉 Valuation Settings")
    indexation_factor = st.number_input("Cost Inflation Index Factor:", min_value=1.0, value=1.2, step=0.1)
    salvage_pct = st.number_input("Salvage Value (%) :", min_value=0.0, max_value=100.0, value=5.0) / 100.0

# -----------------------------------------------------------------------------
# 3. DEFINING THE AI EXPECTATIONS (DATA EXTRACTION SCHEMA)
# -----------------------------------------------------------------------------
class AssetExtractionSchema(BaseModel):
    asset_name: str = Field(description="Name or type of the machine/asset")
    manufacturer: str = Field(description="Manufacturer/Brand name. Use 'Unknown' if missing.")
    model_number: str = Field(description="Model designation or number.")
    serial_number: str = Field(description="Serial or chassis number.")
    estimated_useful_life_years: int = Field(description="Industry standard useful life for this asset category if not specified.")
    original_cost: float = Field(description="Invoice or purchase price. Default to 0.0 if not found.")
    age_years: int = Field(description="Estimated age of the machine based on its manufacture date relative to the current year.")

# -----------------------------------------------------------------------------
# 4. USER INTERFACE: FILE UPLOADER
# -----------------------------------------------------------------------------
uploaded_file = st.file_uploader("Drop an asset photo or invoice PDF here...", type=["png", "jpg", "jpeg", "pdf"])

if uploaded_file is not None:
    # Display the uploaded file if it's an image
    if uploaded_file.type in ["image/png", "image/jpeg", "image/jpg"]:
        st.image(uploaded_file, caption="Uploaded Asset File", width=400)
    else:
        st.success("📄 PDF Document Uploaded Successfully!")

    if not api_key:
        st.warning("⚠️ Please provide your Gemini API Key in the sidebar to run the automated engine.")
    else:
        with st.spinner("AI is analyzing the asset data and calculating value..."):
            try:
                # Initialize the Gemini Engine
                client = genai.Client(api_key=api_key)
                
                # Convert uploaded file to bytes for the AI
                file_bytes = uploaded_file.read()
                
                # Instruct the AI
                prompt = """
                Analyze this asset file (photo or document). Extract the exact parameters.
                If information like age or cost is missing from a photo, use standard industrial engineering 
                baselines to make an intelligent professional estimation.
                """
                
                # Execute AI parsing
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        types.Part.from_bytes(data=file_bytes, mime_type=uploaded_file.type),
                        prompt
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=AssetExtractionSchema,
                        temperature=0.1
                    ),
                )
                
                # Convert the AI's response back into an organized python dictionary
                data = json.loads(response.text)
                
                # -----------------------------------------------------------------------------
                # 5. MATHEMATICAL COMPLIANCE ENGINE (COST APPROACH - SLM)
                # -----------------------------------------------------------------------------
                orig_cost = data.get("original_cost", 0.0)
                useful_life = data.get("estimated_useful_life_years", 15)
                age = data.get("age_years", 0)
                
                # Calculate Gross Current Replacement Cost (GCRC)
                gcrc = orig_cost * indexation_factor
                salvage_value = gcrc * salvage_pct
                depreciable_amount = gcrc - salvage_value
                
                # Apply Straight-Line Depreciation
                if age >= useful_life:
                    fair_value = salvage_value
                else:
                    annual_depreciation = depreciable_amount / useful_life
                    accumulated_depreciation = annual_depreciation * age
                    fair_value = gcrc - accumulated_depreciation

                # -----------------------------------------------------------------------------
                # 6. DISPLAYING RESULTS TO THE USER
                # -----------------------------------------------------------------------------
                st.success("✅ Valuation Complete!")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### 📋 Extracted Asset Specifications")
                    st.write(f"**Asset Name:** {data.get('asset_name')}")
                    st.write(f"**Manufacturer:** {data.get('manufacturer')}")
                    st.write(f"**Model Number:** {data.get('model_number')}")
                    st.write(f"**Serial/Chassis No:** {data.get('serial_number')}")
                    st.write(f"**Assessed Age:** {age} Years")
                    st.write(f"**Estimated Useful Life:** {useful_life} Years")
                
                with col2:
                    st.markdown("### 💰 Automated Valuation Summary (Cost Approach)")
                    st.metric(label="Calculated Fair Value (Current)", value=f"₹ {fair_value:,.2f}")
                    st.metric(label="Gross Current Replacement Cost (GCRC)", value=f"₹ {gcrc:,.2f}")
                    st.write(f"**Original Historical Cost:** ₹ {orig_cost:,.2f}")
                    st.write(f"**Calculated Salvage Floor Value:** ₹ {salvage_value:,.2f}")
                    
            except Exception as e:
                st.error(f"An error occurred during processing: {e}")
