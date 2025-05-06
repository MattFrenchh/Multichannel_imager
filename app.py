import streamlit as st
import tifffile
import numpy as np
import imageio
from io import BytesIO

# --- Normalize channels based on percentile ranges ---
def normalize_channels_with_percentiles(volume, percentiles):
    Z, C, X, Y = volume.shape
    norm_volume = np.zeros_like(volume, dtype=np.float32)
    for c in range(C):
        ch = volume[:, c, :, :]
        lower_p, upper_p = percentiles[c]
        vmin = np.percentile(ch, lower_p)
        vmax = np.percentile(ch, upper_p)
        if vmax > vmin:
            norm_volume[:, c] = np.clip((ch - vmin) / (vmax - vmin), 0, 1)
        else:
            norm_volume[:, c] = 0.0
    return norm_volume

# --- Convert RGB hex to float (0-1) ---
def hex_to_rgb_floats(hex_color):
    return tuple(int(hex_color[i:i+2], 16)/255.0 for i in (1, 3, 5))

# --- Combine normalized channels into RGB ---
def multichannel_to_rgb_stack(volume, channel_colors, visibility):
    Z, C, X, Y = volume.shape
    rgb_stack = np.zeros((Z, X, Y, 3), dtype=np.float32)
    for z in range(Z):
        for c, (r, g, b) in enumerate(channel_colors):
            if visibility[c]:  # Only add visible channels
                gray = volume[z, c]
                rgb_stack[z, :, :, 0] += gray * r
                rgb_stack[z, :, :, 1] += gray * g
                rgb_stack[z, :, :, 2] += gray * b
        rgb_stack[z] = np.clip(rgb_stack[z], 0, 1)
    return rgb_stack

# --- Streamlit UI ---
st.set_page_config(page_title="TIFF Channel Composite", layout="wide")
st.title("🧬 Multichannel TIFF → RGB Z-stack Composite")

uploaded_file = st.file_uploader("📂 Drop a multichannel TIFF (Z × C × X × Y or 1 × Z × C × X × Y)", type=["tif", "tiff"])

if uploaded_file is not None:
    try:
        img = tifffile.imread(uploaded_file)

        # Reshape if 5D (e.g. 1 × Z × C × X × Y)
        if img.ndim == 5:
            if img.shape[0] == 1:
                img = img[0]
            else:
                st.error("Only 4D or 1×Z×C×X×Y TIFFs are supported.")
                st.stop()

        if img.ndim != 4:
            st.error(f"Unsupported TIFF shape: {img.shape}")
            st.stop()

        Z, C, X, Y = img.shape
        st.success(f"Loaded image with shape: Z={Z}, C={C}, X={X}, Y={Y}")

        # --- Two-column layout ---
        col1, col2 = st.columns([2, 3])  # Adjust column widths

        # --- Left Column (Controls) ---
        with col1:
            # Channel color pickers with toggle to show/hide
            st.subheader("🎨 Pick RGB color per channel")
            default_colors = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF", "#FFA500", "#8000FF", "#888888"]
            cols = st.columns(C)
            color_hex = []
            channel_visibility = []

            for c in range(C):
                with cols[c]:
                    # Checkbox for showing/hiding the channel
                    visibility = st.checkbox(f"Show Channel {c+1}", value=True, key=f"toggle_{c}")
                    channel_visibility.append(visibility)

                    # Color picker
                    color = st.color_picker(f"Ch {c+1}", value=default_colors[c % len(default_colors)], label_visibility="visible")
                    color_hex.append(color)

            # Convert hex to RGB floats
            channel_colors = [hex_to_rgb_floats(h) for h in color_hex]

            # --- Channel normalization percentiles ---
            st.subheader("📊 Channel normalization percentiles")
            percentiles = []
            for c in range(C):
                p = st.slider(f"Channel {c+1} percentile range", 0.0, 100.0, (1.0, 99.0), 0.5)
                percentiles.append(p)

        # --- Right Column (Image Viewer) ---
        with col2:
            # Normalize and convert
            with st.spinner("Processing image..."):
                norm_img = normalize_channels_with_percentiles(img, percentiles)
                rgb_stack = multichannel_to_rgb_stack(norm_img, channel_colors, channel_visibility)

            # --- Show Z slice ---
            st.subheader("🪂 View Z slice")
            z = st.slider("Z-slice index", 0, Z-1, 0)
            st.image((rgb_stack[z] * 255).astype(np.uint8), caption=f"Z = {z}", channels="RGB")

            # --- Download section ---
            st.subheader("💾 Download individual slices")
            with st.expander("Download PNGs"):
                for z in range(Z):
                    buf = BytesIO()
                    imageio.imwrite(buf, (rgb_stack[z] * 255).astype(np.uint8), format='png')
                    st.download_button(
                        label=f"Download Z={z}",
                        data=buf.getvalue(),
                        file_name=f"z_{z:03d}.png",
                        mime="image/png"
                    )

    except Exception as e:
        st.error(f"Error processing TIFF: {e}")
