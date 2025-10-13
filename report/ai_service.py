from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch

MODEL_PATH = "./mistral-7b-merged"

# 앱 실행 시 1번만 로드
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    torch_dtype=torch.float16,
    device_map="auto",
    low_cpu_mem_usage=True
)

hf_pipeline = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    max_new_tokens=1024,
    do_sample=True,
    temperature=0.7
)

def generate_report(prompt: str) -> str:
    outputs = hf_pipeline(prompt)
    return outputs[0]["generated_text"]
