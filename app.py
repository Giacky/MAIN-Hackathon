import streamlit as st
from transformers import pipeline

@st.cache_resource
def load_model():
    return pipeline(
        "zero-shot-classification",
        model="MoritzLaurer/deberta-v3-base-zeroshot-v2.0",
        device="mps",
    )

classifier = load_model()

st.title("Fix Maastricht")

description = st.text_area("Describe the problem")

if st.button("Analyse") and description:
    result = classifier(
        description,
        candidate_labels=[
            "road hazard",
            "waste or litter",
            "broken lighting",
            "accessibility problem",
            "other",
        ],
    )
    st.json(result)