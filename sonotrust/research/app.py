"""Research visualization demo; does NOT provide medical advice."""
from pathlib import Path
import numpy as np
from PIL import Image
import torch
import streamlit as st
from src.data import prepare_image
from src.model import UNet

st.set_page_config(page_title='SonoTrust Research Demo', layout='wide')
st.title('SonoTrust | Ultrasound segmentation research')
st.warning('Educational research prototype. Not validated for diagnosis, screening or treatment.')
weights=st.text_input('Model checkpoint path','results/raw_first/best_model.pt')
file=st.file_uploader('Choose a de-identified ultrasound image (PNG/JPG)',type=['png','jpg','jpeg'])
if file is not None:
    if not Path(weights).exists():
        st.error('Train a model first; the checkpoint is missing.')
        st.stop()
    ck=torch.load(weights,map_location='cpu',weights_only=True)
    model=UNet(ck['base']).eval();model.load_state_dict(ck['state_dict'])
    im=Image.open(file).convert('RGB')
    gray=prepare_image(im, ck['side'], ck['method'])
    tensor=torch.from_numpy(gray.copy()).float()[None,None]/255.0
    with torch.no_grad():prob=torch.sigmoid(model(tensor))[0,0].numpy()
    threshold=st.slider('Visualization threshold',0.1,0.9,0.5,0.05)
    overlay=np.stack([gray,gray,gray],axis=-1)
    lesion=prob>=threshold
    overlay[lesion]=(overlay[lesion].astype(float)*0.5+np.array([255,0,0])*0.5).astype(np.uint8)
    a,b=st.columns(2)
    a.image(gray,caption='Model input (grayscale)',use_container_width=True)
    b.image(overlay,caption='Predicted area (red, not a diagnosis)',use_container_width=True)
    st.caption('This system estimates a visual region only. It does not assign a diagnosis or clinical certainty.')
