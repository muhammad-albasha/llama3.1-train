from unsloth import FastLanguageModel
import os
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = "lora_model",
    max_seq_length = 2048,
    dtype = None,
    load_in_4bit = True,
)
FastLanguageModel.for_inference(model)

model.push_to_hub_gguf(
    "muhammad-albasha/Llama-3.1-8B-python", # Change this to your username!
    tokenizer,
    quantization_method = ["q4_k_m", "q8_0", "q5_k_m",],
    token = os.getenv("HF_TOKEN"),
)