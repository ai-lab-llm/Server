from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch

MODEL_PATH = "hajeong67/mistral-7b-merged"

tokenizer = None
model = None
hf_pipeline = None

def load_model():
    """모델이 아직 로드되지 않았다면 다운로드 후 초기화"""
    global tokenizer, model, hf_pipeline
    if hf_pipeline is None:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_PATH,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto"
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
    """리포트 생성 함수 (lazy load)"""
    pipe = load_model()
    outputs = pipe(prompt)
    return outputs[0]["generated_text"]