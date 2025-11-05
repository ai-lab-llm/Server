from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from django.conf import settings
import torch, os

MODEL_PATH = os.path.join(settings.BASE_DIR, "mistral-7b-merged")

# 전역 변수 초기화만 함
tokenizer = None
model = None
hf_pipeline = None

def load_model():
    global tokenizer, model, hf_pipeline
    if hf_pipeline is None:
        print("🚀 Loading model (this may take a while)...")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_PATH,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map={"": "cuda:1"},     
            trust_remote_code=True
        )
        hf_pipeline = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=1024,
            do_sample=True,
            temperature=0.7
        )
    return hf_pipeline

def generate_report(prompt: str) -> str:
    pipe = load_model()
    outputs = pipe(prompt)
    return outputs[0]["generated_text"]

