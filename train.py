from unsloth import FastLanguageModel
import torch
import os
from transformers import TextStreamer
from datasets import load_dataset
from trl import SFTTrainer
from transformers import TrainingArguments
from unsloth import is_bfloat16_supported
import traceback

# 1. Configuration
max_seq_length = 1024
dtype = None
load_in_4bit = True 
alpaca_prompt = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{}

### Input:
{}

### Response:
{}"""

instruction = "Create a function to calculate the sum of a sequence of integers."
input = "[1, 2, 3, 4, 5]"
huggingface_model_name = "muhammad-albasha/Llama-3.1-8B"

# 2. Before Training
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = "unsloth/Meta-Llama-3.1-8B-bnb-4bit",
    max_seq_length = max_seq_length,
    dtype = dtype,
    load_in_4bit = load_in_4bit,
    token = os.getenv("HF_TOKEN")
)

FastLanguageModel.for_inference(model)
inputs = tokenizer(
[
    alpaca_prompt.format(
        instruction,
        input,
        "",
    )
], return_tensors = "pt").to("cuda")

text_streamer = TextStreamer(tokenizer)
_ = model.generate(**inputs, streamer = text_streamer, max_new_tokens = 1000)

# 3. Load data
EOS_TOKEN = tokenizer.eos_token
def formatting_prompts_func(examples):
    instructions = examples["instruction"]
    inputs       = examples["input"]
    outputs      = examples["output"]
    texts = []
    for instruction, input, output in zip(instructions, inputs, outputs):
        text = alpaca_prompt.format(instruction, input, output) + EOS_TOKEN
        texts.append(text)
    return { "text" : texts, }

dataset = load_dataset("iamtarun/python_code_instructions_18k_alpaca", split = "train")
dataset = dataset.map(formatting_prompts_func, batched = True,)

# 4. Training
model = FastLanguageModel.get_peft_model(
    model,
    r = 16,
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
                      "gate_proj", "up_proj", "down_proj",],
    lora_alpha = 16,
    lora_dropout = 0,
    bias = "none",
    use_gradient_checkpointing = "unsloth",
    random_state = 3407,
    use_rslora = False,
    loftq_config = None,
)

trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = dataset,
    dataset_text_field = "text",
    max_seq_length = max_seq_length,
    dataset_num_proc = 2,
    packing = False,
    args = TrainingArguments(
        per_device_train_batch_size = 1,
        gradient_accumulation_steps = 8,
        warmup_steps = 5,
        max_steps = 100,
        learning_rate = 2e-4,
        fp16 = not is_bfloat16_supported(),
        bf16 = is_bfloat16_supported(),
        logging_steps = 1,
        optim = "adamw_8bit",
        weight_decay = 0.01,
        lr_scheduler_type = "linear",
        seed = 3407,
        output_dir = "outputs",
    ),
)

# Show current memory stats
gpu_stats = torch.cuda.get_device_properties(0)
start_gpu_memory = round(torch.cuda.max_memory_reserved() / 1024 / 1024 / 1024, 3)
max_memory = round(gpu_stats.total_memory / 1024 / 1024 / 1024, 3)
print(f"GPU = {gpu_stats.name}. Max memory = {max_memory} GB.")
print(f"{start_gpu_memory} GB of memory reserved.")

trainer_stats = trainer.train()

# Show final memory and time stats
used_memory = round(torch.cuda.max_memory_reserved() / 1024 / 1024 / 1024, 3)
used_memory_for_lora = round(used_memory - start_gpu_memory, 3)
used_percentage = round(used_memory         /max_memory*100, 3)
lora_percentage = round(used_memory_for_lora/max_memory*100, 3)
print(f"{trainer_stats.metrics['train_runtime']} seconds used for training.")
print(f"{round(trainer_stats.metrics['train_runtime']/60, 2)} minutes used for training.")
print(f"Peak reserved memory = {used_memory} GB.")
print(f"Peak reserved memory for training = {used_memory_for_lora} GB.")
print(f"Peak reserved memory % of max memory = {used_percentage} %.")
print(f"Peak reserved memory for training % of max memory = {lora_percentage} %.")

# 5. After Training
FastLanguageModel.for_inference(model)
inputs = tokenizer(
[
    alpaca_prompt.format(
        instruction,
        input,
        "",
    )
], return_tensors = "pt").to("cuda")

text_streamer = TextStreamer(tokenizer)
_ = model.generate(**inputs, streamer = text_streamer, max_new_tokens = 1000)

# 6. Saving and Pushing to Hub

# Local saving
print("Saving model locally...")
model.save_pretrained("lora_model")
tokenizer.save_pretrained("lora_model")

# Try saving merged model locally
print("Attempting to save merged model locally...")
try:
    model.save_pretrained_merged("local_merged_model", tokenizer, save_method="merged_16bit")
    print("Successfully saved merged model locally.")
except Exception as e:
    print(f"Error saving merged model locally: {e}")
    traceback.print_exc()

# Push to Hub
print("Pushing model to Hub...")
try:
    model.push_to_hub(huggingface_model_name, token=os.getenv("HF_TOKEN"))
    tokenizer.push_to_hub(huggingface_model_name, token=os.getenv("HF_TOKEN"))
    print("Successfully pushed model and tokenizer to Hub.")
except Exception as e:
    print(f"Error pushing to Hub: {e}")
    traceback.print_exc()

# Try pushing merged model to Hub
print("Attempting to push merged model to Hub...")
try:
    model.push_to_hub_merged(huggingface_model_name, tokenizer, save_method="merged_16bit", token=os.getenv("HF_TOKEN"))
    print("Successfully pushed merged model to Hub.")
except Exception as e:
    print(f"Error pushing merged model to Hub: {e}")
    traceback.print_exc()

# Optional: Uncomment these sections if you want to try other saving methods

# # Merge to 4bit
# if True:
#     try:
#         model.save_pretrained_merged("model_4bit", tokenizer, save_method="merged_4bit")
#         model.push_to_hub_merged(huggingface_model_name, tokenizer, save_method="merged_4bit", token=os.getenv("HF_TOKEN"))
#         print("Successfully saved and pushed 4-bit merged model.")
#     except Exception as e:
#         print(f"Error with 4-bit merged model: {e}")
#         traceback.print_exc()

# # Just LoRA adapters
# if True:
#     try:
#         model.save_pretrained_merged("model_lora", tokenizer, save_method="lora")
#         model.push_to_hub_merged(huggingface_model_name, tokenizer, save_method="lora", token=os.getenv("HF_TOKEN"))
#         print("Successfully saved and pushed LoRA adapters.")
#     except Exception as e:
#         print(f"Error with LoRA adapters: {e}")
#         traceback.print_exc()

# # Save to 8bit Q8_0 GGUF
# if True:
#     try:
#         model.save_pretrained_gguf("model_gguf_8bit", tokenizer)
#         model.push_to_hub_gguf(huggingface_model_name, tokenizer, token=os.getenv("HF_TOKEN"))
#         print("Successfully saved and pushed 8-bit GGUF model.")
#     except Exception as e:
#         print(f"Error with 8-bit GGUF model: {e}")
#         traceback.print_exc()

print("All operations completed.")