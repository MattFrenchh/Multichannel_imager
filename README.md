# Multichannel_imager
Create RGB file stack of image +7 channels


# 1. Create a virtual environment
python3 -m venv .venv

# 2. Activate the virtual environment (Linux/macOS)
source .venv/bin/activate

# 2.1. For Windows, use this command instead:
# .\.venv\Scripts\activate

# 3. Install the required dependencies
pip install streamlit tifffile numpy imageio

# 4. Run the Streamlit app
streamlit run app.py
